import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

import faiss
import jieba
import numpy as np
from fastapi import FastAPI, HTTPException
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_community.embeddings import DashScopeEmbeddings
from pydantic import BaseModel


# 配置参数
class Config:
    data_root = "datasets"  # 调整为 .docx 文件路径
    chunk_size = 300  # 适配长段落
    chunk_overlap = 50  # 保留上下文
    batch_size = 64


# 设置 API Key
os.environ["DASHSCOPE_API_KEY"] = 'sk-3e5f2c93e985444e8dc9a9fda8e0d872'  # 替换为你的实际 API Key
api_key = os.environ.get("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("DASHSCOPE_API_KEY 未设置")

# 初始化嵌入模型
embedding_model = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=api_key
)


# 分块函数
def semantic_chunking(text: str, chunk_size=Config.chunk_size, overlap=Config.chunk_overlap) -> List[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", "(?<=[。！？])", " ", ""],
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len
    )
    doc = Document(page_content=text)
    chunks = text_splitter.split_documents([doc])
    return [chunk.page_content for chunk in chunks]


# 清洗函数：去除分页标记等噪声
def clean_docx_text(text: str) -> str:
    # 移除分页标记（如 ·265·）
    text = re.sub(r'·\d{3,4}·', ' ', text)
    # 移除多余空格和换行
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    # 可根据需要添加其他清洗规则（如脚注标记）
    return text.strip()


# 带元数据的文档处理
class EthnicDocument(Document):
    def __init__(self, page_content: str, metadata: dict):
        super().__init__(page_content=page_content, metadata=metadata)
        self.metadata["doc_id"] = f"{metadata['ethnic']}_{metadata['chapter']}_{hash(page_content)}"

    @classmethod
    def process_file(cls, file_path: str, ethnic: str) -> List['EthnicDocument']:
        if file_path.endswith('.docx'):
            loader = UnstructuredWordDocumentLoader(file_path=file_path)
            docs = loader.load()
            text = clean_docx_text(docs[0].page_content)
        else:
            raise ValueError("仅支持 .docx 文件")

        file_name = os.path.basename(file_path)
        chapter = file_name.split('_')[1].split('.')[0]  # 如 "羌医药历史"
        chunks = semantic_chunking(text)
        docs = []
        for idx, chunk in enumerate(chunks):
            metadata = {
                "ethnic": ethnic,
                "chapter": chapter,  # 保存完整章节名
                "source": file_name,
                "chunk_id": idx,
                "timestamp": datetime.now().isoformat()
            }
            docs.append(cls(chunk, metadata))
        return docs


# 嵌入生成
def generate_embeddings(texts: List[str]) -> np.ndarray:
    start_time = time.time()
    embeddings = embedding_model.embed_documents(texts)
    embeddings = np.array(embeddings, dtype=np.float32)
    print(f"Embedding generation took {time.time() - start_time:.2f} seconds")
    return embeddings


# FAISS 索引管理
class EthnicIndexer:
    def __init__(self):
        self.indices = {}
        self.metadata = {}
        self.res = faiss.StandardGpuResources() if 'faiss-gpu' in faiss.__file__ else None

    def build_index(self):
        os.makedirs("vector_store", exist_ok=True)

        all_docs = []
        for ethnic in os.listdir(Config.data_root):
            ethnic_path = os.path.join(Config.data_root, ethnic)
            if not os.path.isdir(ethnic_path):
                continue
            for file_name in os.listdir(ethnic_path):
                if not file_name.endswith('.docx'):
                    continue
                file_path = os.path.join(ethnic_path, file_name)
                docs = EthnicDocument.process_file(file_path, ethnic)
                all_docs.extend(docs)

        ethnic_docs = {}
        for doc in all_docs:
            ethnic = doc.metadata['ethnic']
            if ethnic not in ethnic_docs:
                ethnic_docs[ethnic] = []
            ethnic_docs[ethnic].append(doc)

        for ethnic, docs in ethnic_docs.items():
            texts = [doc.page_content for doc in docs]
            self.metadata[ethnic] = [{"content": doc.page_content, **doc.metadata} for doc in docs]
            embeddings = generate_embeddings(texts)
            dimension = embeddings.shape[1]
            if self.res:
                cpu_index = faiss.IndexFlatIP(dimension)
                self.indices[ethnic] = faiss.index_cpu_to_gpu(self.res, 0, cpu_index)
            else:
                self.indices[ethnic] = faiss.IndexFlatIP(dimension)
            faiss.normalize_L2(embeddings)
            self.indices[ethnic].add(embeddings)
            faiss.write_index(self.indices[ethnic], f"vector_store/{ethnic}_index.index")
            np.save(f"vector_store/{ethnic}_metadata.npy", self.metadata[ethnic])
            print(f"Built index for {ethnic} with {len(docs)} entries")

    def load_index(self, ethnic=None):
        if ethnic:
            self.indices[ethnic] = faiss.read_index(f"vector_store/{ethnic}_index.index")
            if self.res:
                self.indices[ethnic] = faiss.index_cpu_to_gpu(self.res, 0, self.indices[ethnic])
            self.metadata[ethnic] = np.load(f"vector_store/{ethnic}_metadata.npy", allow_pickle=True)
            print(f"Loaded index for {ethnic} with {self.indices[ethnic].ntotal} entries")
        else:
            for ethnic_dir in os.listdir(Config.data_root):
                if os.path.isdir(os.path.join(Config.data_root, ethnic_dir)):
                    self.load_index(ethnic_dir)

    def search(self, query: str, ethnic=None, top_k=3, chapter_filter=None):
        query_embed = generate_embeddings([query])[0]
        faiss.normalize_L2(query_embed.reshape(1, -1))

        if ethnic and ethnic in self.indices:
            if chapter_filter:  # 如果指定章节
                # 过滤该民族下特定章节的向量
                filtered_indices = [
                    i for i, meta in enumerate(self.metadata[ethnic])
                    if chapter_filter.lower() in meta['chapter'].lower()
                ]
                if not filtered_indices:
                    print(f"No matching chapter '{chapter_filter}' in {ethnic}")
                    filtered_indices = range(self.indices[ethnic].ntotal)  # 回退到全搜索
                embeddings = np.array([self.indices[ethnic].reconstruct(i) for i in filtered_indices])
                scores, indices = faiss.IndexFlatIP(embeddings.shape[1]).search(query_embed.reshape(1, -1), top_k)
                indices = [filtered_indices[i] for i in indices[0]]
            else:
                scores, indices = self.indices[ethnic].search(query_embed.reshape(1, -1), top_k)
                indices = indices[0]
            scores = scores[0]
            print(f"Search for {ethnic} - Scores: {scores}, Indices: {indices}")
            return scores, indices, [ethnic] * top_k
        else:
            # 全局搜索逻辑保持不变
            all_results = []
            for ethnic in self.indices:
                scores, indices = self.indices[ethnic].search(query_embed.reshape(1, -1), top_k)
                for i, idx in enumerate(indices[0]):
                    all_results.append((scores[0][i], idx, ethnic))
            all_results.sort(reverse=True)
            top_results = all_results[:top_k]
            scores = np.array([r[0] for r in top_results])
            indices = np.array([r[1] for r in top_results], dtype=int)
            ethnic_list = [r[2] for r in top_results]
            return scores, indices, ethnic_list


# REST API 服务
indexer = EthnicIndexer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        indexer.load_index()
        print("Startup: 所有民族索引加载成功")
    except FileNotFoundError:
        print("Startup: 索引文件未找到，正在构建索引...")
        indexer.build_index()
        print("Startup: 索引构建完成")
    except Exception as e:
        print(f"Startup: 索引加载失败: {str(e)}")
        raise
    yield
    print("Shutdown: 服务关闭")


app = FastAPI(lifespan=lifespan)


class QueryRequest(BaseModel):
    question: str
    ethnic_group: str = None
    top_k: int = 3


class QueryResult(BaseModel):
    content: str
    chapter: str
    similarity: float
    source: str


@app.post("/query", response_model=List[QueryResult])
async def handle_query(request: QueryRequest):
    try:
        ethnic_keywords = {
            '藏族': ['藏族', '藏医'],
            '羌族': ['羌族', '羌医'],
            '汉族': ['汉族', '中医'],
            '彝族': ['彝族', '彝医']
        }
        inferred_ethnic = request.ethnic_group
        chapter_filter = None
        if not inferred_ethnic:
            question_words = set(jieba.cut(request.question))
            for ethnic, keywords in ethnic_keywords.items():
                if any(kw in question_words for kw in keywords):
                    inferred_ethnic = ethnic
                    break
            # 从问题中提取可能的章节关键词
            chapter_keywords = {'历史', '发展', '药材', '分类'}  # 可扩展
            for kw in chapter_keywords:
                if kw in request.question:
                    chapter_filter = kw
                    break

        top_k_multiplier = 2
        if inferred_ethnic:
            print(f"Searching index for {inferred_ethnic}, chapter filter: {chapter_filter}")
            scores, indices, ethnic_list = indexer.search(
                request.question, inferred_ethnic, request.top_k * top_k_multiplier, chapter_filter
            )
        else:
            print("No ethnic group inferred, searching all indices")
            scores, indices, ethnic_list = indexer.search(
                request.question, top_k=request.top_k * top_k_multiplier
            )

        question_keywords = set(jieba.cut(request.question)) - set(ethnic_keywords.keys()) - {'的', '是', '有哪些',
                                                                                              '介绍', '一下'}
        results = []
        seen = set()
        for score, idx, ethnic in zip(scores, indices, ethnic_list):
            meta = indexer.metadata[ethnic][idx]
            if meta['doc_id'] in seen:
                continue
            seen.add(meta['doc_id'])
            content = meta['content']
            content_words = set(jieba.cut(content))
            keyword_score = sum(1 for kw in question_keywords if kw in content_words)
            adjusted_score = float(score) + 0.1 * keyword_score
            results.append({
                "content": content,
                "chapter": meta['chapter'],
                "similarity": adjusted_score,
                "source": meta['source']
            })
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return [QueryResult(**res) for res in results[:request.top_k]]
    except Exception as e:
        print(f"Error in handle_query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 主程序
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="重建索引")
    args = parser.parse_args()

    if args.build:
        print("正在构建索引...")
        indexer.build_index()
        print("索引构建完成")
    else:
        print("加载现有索引或启动API服务：")
        try:
            indexer.load_index()
            print("启动API服务：uvicorn app:app --reload")  # 注意文件名需与实际一致
        except FileNotFoundError:
            print("索引文件未找到，请先使用 --build 参数构建索引")
