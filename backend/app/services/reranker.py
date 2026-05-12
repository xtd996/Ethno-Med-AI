"""
检索结果重排序器 -- Cross-Encoder Reranker

使用 sentence-transformers CrossEncoder 对 FAISS 检索到的文档进行
相关性重排序，提升送入 LLM 的上下文质量。

模型采用延迟加载策略，首次调用 rerank() 时才下载并初始化。
"""

from __future__ import annotations

from typing import Optional

from langchain_core.documents import Document

from app.config import settings


class Reranker:
    """Cross-Encoder 重排序器。

    Parameters
    ----------
    model_name : str
        HuggingFace 上的 CrossEncoder 模型名称，默认 ``BAAI/bge-reranker-base``。
    top_n : int
        重排序后保留的文档数量。
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        top_n: int = 3,
    ) -> None:
        self.model_name = model_name
        self.top_n = top_n
        self._model = None

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """延迟加载 CrossEncoder 模型（首次调用时加载）。"""
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def rerank(self, query: str, documents: list[Document]) -> list[Document]:
        """对检索结果重排序。

        Parameters
        ----------
        query : str
            用户查询。
        documents : list[Document]
            检索到的文档列表。

        Returns
        -------
        list[Document]
            按相关性降序排列后的前 *top_n* 个文档。如果输入为空则返回空列表。
        """
        if not documents:
            return []

        self._load_model()

        # 构建 query-document 对
        pairs = [(query, doc.page_content) for doc in documents]

        # 计算相关性分数
        scores = self._model.predict(pairs)

        # 按分数降序排序
        scored_docs = list(zip(scores, documents))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        # 返回 top_n
        return [doc for _, doc in scored_docs[: self.top_n]]


# ======================================================================
# 全局单例 & 便捷函数
# ======================================================================

_reranker: Optional[Reranker] = None


def get_reranker(
    model_name: str | None = None,
    top_n: int | None = None,
) -> Reranker:
    """获取全局 Reranker 单例。

    首次调用时使用 *model_name* 和 *top_n* 创建实例，后续调用忽略参数直接返回缓存。
    """
    global _reranker
    if _reranker is None:
        _reranker = Reranker(
            model_name=model_name or settings.reranker_model,
            top_n=top_n if top_n is not None else settings.reranker_top_n,
        )
    return _reranker


def rerank_documents(
    query: str,
    documents: list[Document],
    top_n: int | None = None,
) -> list[Document]:
    """便捷函数：对文档重排序并返回 *top_n* 个结果。"""
    reranker = get_reranker(top_n=top_n)
    return reranker.rerank(query, documents)
