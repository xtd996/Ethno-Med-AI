"""
混合检索器 — BM25 + 向量检索

为每个民族构建 EnsembleRetriever，将 FAISS 向量检索与 BM25 关键词检索
通过加权融合合并，提升对少数民族医药术语的召回率。
"""

from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.config import settings


def build_hybrid_retriever(
    vector_store: FAISS,
    docs: list[Document],
    vector_weight: float | None = None,
    bm25_weight: float | None = None,
    search_k: int | None = None,
) -> BaseRetriever:
    """构建混合检索器（BM25 + 向量检索）。

    Args:
        vector_store: FAISS 向量存储
        docs: 用于构建 BM25 索引的文档列表
        vector_weight: 向量检索权重（默认取 config 配置）
        bm25_weight: BM25 检索权重（默认取 config 配置）
        search_k: 返回的文档数量（默认取 config 配置）

    Returns:
        EnsembleRetriever 混合检索器
    """
    vector_weight = vector_weight if vector_weight is not None else settings.hybrid_vector_weight
    bm25_weight = bm25_weight if bm25_weight is not None else settings.hybrid_bm25_weight
    search_k = search_k if search_k is not None else settings.hybrid_search_k

    # BM25 检索器
    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = search_k

    # 向量检索器
    vector_retriever = vector_store.as_retriever(search_kwargs={"k": search_k})

    # 混合检索器
    ensemble_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[vector_weight, bm25_weight],
    )

    return ensemble_retriever


def build_hybrid_retrievers_for_ethnic_groups(
    vector_stores: dict[str, FAISS],
    vector_weight: float | None = None,
    bm25_weight: float | None = None,
    search_k: int | None = None,
) -> dict[str, BaseRetriever]:
    """为每个民族构建混合检索器。

    从 FAISS docstore 中提取文档列表，构建 BM25 索引，
    再与向量检索器组合为 EnsembleRetriever。

    Args:
        vector_stores: 民族名 -> FAISS 向量存储 的字典
        vector_weight: 向量检索权重（默认取 config 配置）
        bm25_weight: BM25 检索权重（默认取 config 配置）
        search_k: 返回的文档数量（默认取 config 配置）

    Returns:
        民族名 -> 混合检索器 的字典
    """
    hybrid_retrievers: dict[str, BaseRetriever] = {}

    for ethnic, store in vector_stores.items():
        # 从 FAISS docstore 中提取文档
        docs: list[Document] = []
        for doc in store.docstore._dict.values():
            if isinstance(doc, Document):
                docs.append(doc)

        if docs:
            hybrid_retrievers[ethnic] = build_hybrid_retriever(
                store, docs, vector_weight, bm25_weight, search_k
            )
        else:
            # 无文档可构建 BM25 索引时，回退到纯向量检索
            k = search_k if search_k is not None else settings.hybrid_search_k
            hybrid_retrievers[ethnic] = store.as_retriever(
                search_kwargs={"k": k}
            )

    return hybrid_retrievers
