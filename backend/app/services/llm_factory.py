from typing import Any

from langchain_openai import ChatOpenAI

from app.config import Settings


def create_llm(settings: Settings, model_type: str = "professional") -> dict[str, Any]:
    """根据配置创建 LLM 实例。

    三种 provider 统一使用 OpenAI 兼容 API：
    - local:     指向 vLLM/SGLang/TGI 等本地推理框架
    - dashscope: 阿里云 DashScope（也兼容 OpenAI 接口）
    - openai:    OpenAI 或任何兼容 API

    Args:
        settings: 应用配置
        model_type: "professional" 或 "living"

    Returns:
        {"llm": ChatOpenAI} 字典
    """
    provider = settings.llm_provider

    if provider == "local":
        return _create_local_llm(settings, model_type)
    elif provider == "dashscope":
        return _create_dashscope_llm(settings)
    elif provider == "openai":
        return _create_openai_llm(settings)
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")


def _create_local_llm(settings: Settings, model_type: str) -> dict[str, Any]:
    """调用本地 vLLM/SGLang/TGI 推理服务（OpenAI 兼容 API）。

    前提：已通过 vLLM 等框架独立部署模型服务，例如：
        vllm serve deepseek-r1-7B --port 8001
    """
    model_name = (
        settings.professional_model_name
        if model_type == "professional"
        else settings.living_model_name
    )

    llm = ChatOpenAI(
        model=model_name,
        api_key=settings.local_model_api_key,
        base_url=settings.local_model_base_url,
        streaming=True,
    )
    return {"llm": llm}


def _create_dashscope_llm(settings: Settings) -> dict[str, Any]:
    """创建 DashScope (通义千问) LLM。"""
    from langchain_community.chat_models.tongyi import ChatTongyi

    kwargs: dict[str, Any] = {"model": settings.dashscope_model}
    if settings.dashscope_api_key:
        kwargs["dashscope_api_key"] = settings.dashscope_api_key

    llm = ChatTongyi(**kwargs, streaming=True)
    return {"llm": llm}


def _create_openai_llm(settings: Settings) -> dict[str, Any]:
    """创建 OpenAI 兼容 API LLM。"""
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key or None,
        base_url=settings.openai_base_url,
        streaming=True,
    )
    return {"llm": llm}
