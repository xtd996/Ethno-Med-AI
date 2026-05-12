from langchain_core.embeddings import Embeddings

from app.config import Settings


def create_embeddings(settings: Settings) -> Embeddings:
    """根据配置创建嵌入模型实例。"""
    provider = settings.embedding_provider

    if provider == "dashscope":
        return _create_dashscope_embeddings(settings)
    elif provider == "huggingface":
        return _create_huggingface_embeddings(settings)
    else:
        raise ValueError(f"不支持的嵌入模型提供商: {provider}")


def _create_dashscope_embeddings(settings: Settings) -> Embeddings:
    """创建 DashScope 云端嵌入模型。"""
    from langchain_community.embeddings import DashScopeEmbeddings

    kwargs: dict = {"model": settings.embedding_model}
    if settings.dashscope_api_key:
        kwargs["dashscope_api_key"] = settings.dashscope_api_key
    return DashScopeEmbeddings(**kwargs)


def _create_huggingface_embeddings(settings: Settings) -> Embeddings:
    """创建本地 HuggingFace 嵌入模型（备选方案）。"""
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=settings.huggingface_embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
