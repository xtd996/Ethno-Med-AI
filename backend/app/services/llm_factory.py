from typing import Any

from app.config import Settings


def create_llm(settings: Settings, model_type: str = "professional") -> dict[str, Any]:
    """根据配置创建 LLM 实例。

    Args:
        settings: 应用配置
        model_type: "professional" 或 "living"

    Returns:
        包含 "llm" 和可选 "tokenizer" 键的字典。
        对于本地模型，tokenizer 用于 chat template 格式化。
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
    """创建本地 HuggingFace 模型。"""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline as hf_pipeline

    model_path = (
        settings.professional_model_path
        if model_type == "professional"
        else settings.living_model_path
    )

    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)

    # 修复 pad_token（与原 backend.py 逻辑一致）
    if tokenizer.pad_token_id is None or tokenizer.pad_token_id == tokenizer.eos_token_id:
        tokenizer.pad_token = "[PAD]"
        tokenizer.pad_token_id = tokenizer.convert_tokens_to_ids("[PAD]")
        if tokenizer.pad_token_id is None:
            tokenizer.add_special_tokens({"pad_token": "[PAD]"})

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
    )

    if tokenizer.pad_token_id is None:
        model.resize_token_embeddings(len(tokenizer))

    pipe = hf_pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=1024,
        repetition_penalty=1.1,
        temperature=0.7,
        top_p=0.9,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )

    from langchain_huggingface import HuggingFacePipeline

    llm = HuggingFacePipeline(pipeline=pipe)
    return {"llm": llm, "tokenizer": tokenizer}


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
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key or None,
        base_url=settings.openai_base_url,
        streaming=True,
    )
    return {"llm": llm}
