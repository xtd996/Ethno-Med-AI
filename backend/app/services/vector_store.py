import os

import faiss
import numpy as np
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.config import Settings


def _read_index_safe(path: str) -> faiss.Index:
    """读取 FAISS 索引，兼容 Windows 中文路径。

    faiss C++ 的 FileIOReader 不支持非 ASCII 路径，
    先复制到临时文件再读取。
    """
    import shutil
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".index", delete=False)
    try:
        tmp.close()
        shutil.copy2(path, tmp.name)
        return faiss.read_index(tmp.name)
    finally:
        os.unlink(tmp.name)

# 支持的民族列表
ETHNIC_GROUPS: list[str] = ["藏族", "羌族", "彝族"]


def _find_index_path(vector_store_path: str, ethnic: str) -> str:
    """查找指定民族的 FAISS 索引文件路径。

    优先尝试精确文件名匹配；若失败则扫描目录，
    通过将 metadata 文件与 index 文件按排序顺序配对来处理文件名乱码问题。
    """
    exact = os.path.join(vector_store_path, f"{ethnic}_index.index")
    if os.path.exists(exact):
        return exact

    # 回退：扫描目录，按排序顺序将 metadata 与 index 配对
    metadata_files = sorted(
        f for f in os.listdir(vector_store_path) if f.endswith("_metadata.npy")
    )
    index_files = sorted(
        f for f in os.listdir(vector_store_path) if f.endswith("_index.index")
    )

    ethnic_names = [f.replace("_metadata.npy", "") for f in metadata_files]

    if len(ethnic_names) != len(index_files):
        raise ValueError(
            f"metadata 文件数 ({len(ethnic_names)}) 与 index 文件数 ({len(index_files)}) 不一致"
        )

    mapping = dict(zip(ethnic_names, index_files))

    if ethnic in mapping:
        return os.path.join(vector_store_path, mapping[ethnic])

    raise FileNotFoundError(f"未找到 {ethnic} 对应的索引文件")


def _load_single_store(
    vector_store_path: str,
    ethnic: str,
    embeddings: Embeddings,
) -> FAISS:
    """加载单个民族的 FAISS 向量存储。"""
    index_path = _find_index_path(vector_store_path, ethnic)
    metadata_path = os.path.join(vector_store_path, f"{ethnic}_metadata.npy")

    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"元数据文件不存在: {metadata_path}")

    index = _read_index_safe(index_path)
    metadata = np.load(metadata_path, allow_pickle=True)

    documents = [
        Document(
            page_content=meta["content"],
            metadata={k: v for k, v in meta.items() if k != "content"},
        )
        for meta in metadata
    ]

    if index.ntotal != len(documents):
        raise ValueError(
            f"{ethnic}: 索引条目数 ({index.ntotal}) 与元数据条目数 ({len(documents)}) 不一致"
        )

    docstore = InMemoryDocstore({str(i): doc for i, doc in enumerate(documents)})
    index_to_docstore_id = {i: str(i) for i in range(index.ntotal)}

    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id,
    )

    print(f"成功加载 {ethnic} 索引，条目数: {vector_store.index.ntotal}")
    return vector_store


def load_vector_stores(
    settings: Settings,
    embeddings: Embeddings,
) -> dict[str, FAISS]:
    """加载所有民族的 FAISS 向量存储。

    返回以民族名为键、FAISS 向量存储为值的字典。
    """
    vector_stores: dict[str, FAISS] = {}
    for ethnic in ETHNIC_GROUPS:
        try:
            store = _load_single_store(settings.rag_vector_store_path, ethnic, embeddings)
            vector_stores[ethnic] = store
        except Exception as e:
            print(f"加载 {ethnic} 索引失败: {e}")
    return vector_stores
