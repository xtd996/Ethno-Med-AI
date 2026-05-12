"""
RAG Index Builder for EthnoMedAI
=================================
Refactored from RAG/知识向量库构建.py

Builds FAISS vector indices from .docx documents organized by ethnicity.
Each ethnicity gets its own index file and metadata file.

Usage:
    python -m rag.build_index --build      # Build indices
    python -m rag.build_index --rebuild    # Delete and rebuild
    python -m rag.build_index --fix-names  # Fix garbled index filenames

Environment:
    DASHSCOPE_API_KEY  — Required. API key for DashScope embedding service.
"""

import argparse
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import faiss
import numpy as np
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_community.embeddings import DashScopeEmbeddings
from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rag.build_index")

# ---------------------------------------------------------------------------
# Garbled filename mapping (UTF-8 bytes misinterpreted as legacy encoding)
# ---------------------------------------------------------------------------
GARBLED_INDEX_MAP: Dict[str, str] = {
    "钘忔棌": "藏族",
    "褰濇棌": "彝族",
    "缇屾棌": "羌族",
}


# ---------------------------------------------------------------------------
# Configuration via pydantic-settings
# ---------------------------------------------------------------------------
class BuildConfig(BaseSettings):
    """Configuration loaded from environment variables (or .env file)."""

    dashscope_api_key: str = ""
    embedding_model: str = "text-embedding-v3"
    chunk_size: int = 300
    chunk_overlap: int = 50
    batch_size: int = 64
    data_root: str = ""
    vector_store_dir: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        base = Path(__file__).parent
        if not self.data_root:
            self.data_root = str(base / "datasets")
        if not self.vector_store_dir:
            self.vector_store_dir = str(base / "vector_store")


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------
def clean_docx_text(text: str) -> str:
    """Remove pagination markers and normalize whitespace."""
    text = re.sub(r'·\d{3,4}·', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()


def semantic_chunking(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    """Split text into semantic chunks using RecursiveCharacterTextSplitter."""
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", "(?<=[。！？])", " ", ""],
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
    )
    doc = Document(page_content=text)
    chunks = text_splitter.split_documents([doc])
    return [chunk.page_content for chunk in chunks]


# ---------------------------------------------------------------------------
# Document processing
# ---------------------------------------------------------------------------
class EthnicDocument(Document):
    """Document with ethnic metadata."""

    def __init__(self, page_content: str, metadata: dict):
        super().__init__(page_content=page_content, metadata=metadata)
        self.metadata["doc_id"] = f"{metadata['ethnic']}_{metadata['chapter']}_{hash(page_content)}"

    @classmethod
    def process_file(cls, file_path: str, ethnic: str, chunk_size: int, chunk_overlap: int) -> List['EthnicDocument']:
        """Process a single .docx file into chunks with metadata."""
        if not file_path.endswith('.docx'):
            raise ValueError("仅支持 .docx 文件")

        loader = UnstructuredWordDocumentLoader(file_path=file_path)
        docs = loader.load()
        text = clean_docx_text(docs[0].page_content)

        file_name = os.path.basename(file_path)
        chapter = file_name.split('_')[1].split('.')[0] if '_' in file_name else file_name
        chunks = semantic_chunking(text, chunk_size, chunk_overlap)

        result = []
        for idx, chunk in enumerate(chunks):
            metadata = {
                "ethnic": ethnic,
                "chapter": chapter,
                "source": file_name,
                "chunk_id": idx,
                "timestamp": datetime.now().isoformat(),
            }
            result.append(cls(chunk, metadata))
        return result


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------
def generate_embeddings(texts: List[str], embedding_model: DashScopeEmbeddings) -> np.ndarray:
    """Generate embeddings for a list of texts."""
    start_time = time.time()
    embeddings = embedding_model.embed_documents(texts)
    embeddings = np.array(embeddings, dtype=np.float32)
    logger.info(f"Embedding generation took {time.time() - start_time:.2f}s for {len(texts)} texts")
    return embeddings


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------
class EthnicIndexer:
    """Builds and manages FAISS indices for ethnic medicine documents."""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.embedding_model = DashScopeEmbeddings(
            model=config.embedding_model,
            dashscope_api_key=config.dashscope_api_key,
        )
        self.indices: Dict[str, faiss.Index] = {}
        self.metadata: Dict[str, List[dict]] = {}

    def build_index(self):
        """Build FAISS indices from all .docx files."""
        os.makedirs(self.config.vector_store_dir, exist_ok=True)

        all_docs = []
        data_root = Path(self.config.data_root)
        if not data_root.exists():
            logger.error(f"Data root does not exist: {data_root}")
            sys.exit(1)

        for ethnic_dir in data_root.iterdir():
            if not ethnic_dir.is_dir():
                continue
            ethnic = ethnic_dir.name
            for file_path in ethnic_dir.glob("*.docx"):
                try:
                    docs = EthnicDocument.process_file(
                        str(file_path), ethnic,
                        self.config.chunk_size, self.config.chunk_overlap,
                    )
                    all_docs.extend(docs)
                    logger.info(f"Processed {file_path.name}: {len(docs)} chunks")
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")

        if not all_docs:
            logger.error("No documents processed")
            sys.exit(1)

        # Group by ethnic
        ethnic_docs: Dict[str, List[EthnicDocument]] = {}
        for doc in all_docs:
            ethnic = doc.metadata['ethnic']
            ethnic_docs.setdefault(ethnic, []).append(doc)

        # Build index per ethnic
        for ethnic, docs in ethnic_docs.items():
            texts = [doc.page_content for doc in docs]
            self.metadata[ethnic] = [{"content": doc.page_content, **doc.metadata} for doc in docs]
            embeddings = generate_embeddings(texts, self.embedding_model)
            dimension = embeddings.shape[1]

            index = faiss.IndexFlatIP(dimension)
            faiss.normalize_L2(embeddings)
            index.add(embeddings)

            self.indices[ethnic] = index
            index_path = os.path.join(self.config.vector_store_dir, f"{ethnic}_index.index")
            metadata_path = os.path.join(self.config.vector_store_dir, f"{ethnic}_metadata.npy")

            faiss.write_index(index, index_path)
            np.save(metadata_path, self.metadata[ethnic])
            logger.info(f"Built index for {ethnic}: {len(docs)} entries -> {index_path}")

    def fix_garbled_filenames(self):
        """Rename garbled index files to correct Chinese names."""
        vs_dir = self.config.vector_store_dir
        for garbled, correct in GARBLED_INDEX_MAP.items():
            garbled_path = os.path.join(vs_dir, f"{garbled}_index.index")
            correct_path = os.path.join(vs_dir, f"{correct}_index.index")
            if os.path.exists(garbled_path) and not os.path.exists(correct_path):
                os.rename(garbled_path, correct_path)
                logger.info(f"Renamed: {garbled}_index.index -> {correct}_index.index")

    def rebuild(self):
        """Delete existing indices and rebuild."""
        vs_dir = self.config.vector_store_dir
        if os.path.exists(vs_dir):
            for f in os.listdir(vs_dir):
                if f.endswith(('.index', '.npy')):
                    os.remove(os.path.join(vs_dir, f))
            logger.info("Deleted existing indices")
        self.build_index()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="EthnoMedAI RAG Index Builder")
    parser.add_argument("--build", action="store_true", help="Build indices")
    parser.add_argument("--rebuild", action="store_true", help="Delete and rebuild indices")
    parser.add_argument("--fix-names", action="store_true", help="Fix garbled index filenames")
    args = parser.parse_args()

    config = BuildConfig()

    if not config.dashscope_api_key:
        logger.error("DASHSCOPE_API_KEY not set. Set it in .env or environment.")
        sys.exit(1)

    indexer = EthnicIndexer(config)

    if args.fix_names:
        indexer.fix_garbled_filenames()
    elif args.rebuild:
        indexer.rebuild()
    elif args.build:
        indexer.build_index()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
