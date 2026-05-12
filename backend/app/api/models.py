from fastapi import APIRouter, HTTPException, Request

from app.schemas.chat import ModelInfo, SwitchModelRequest
from app.services.llm_factory import create_llm

router = APIRouter(prefix="/models", tags=["models"])

# 可用模型注册表
AVAILABLE_MODELS: dict[str, ModelInfo] = {
    "专业模型": ModelInfo(
        name="专业模型",
        description="经微调的医疗问答模型，使用 RAG 检索少数民族医药知识库",
        provider="deepseek-r1-7B",
    ),
    "生活模型": ModelInfo(
        name="生活模型",
        description="未经微调的通用对话模型，用于日常问题和闲聊",
        provider="qwen-chat-7b",
    ),
}


@router.get("", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    """列出所有可用模型及其描述。"""
    return list(AVAILABLE_MODELS.values())


@router.post("/switch")
async def switch_model(request: Request, body: SwitchModelRequest) -> dict:
    """切换当前使用的模型。"""
    model_name = body.model_name

    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的模型名称: {model_name}，可用模型: {list(AVAILABLE_MODELS.keys())}",
        )

    config = request.app.state.config

    try:
        result = create_llm(config, "professional" if model_name == "专业模型" else "living")
        request.app.state.current_llm = result["llm"]
        request.app.state.current_model_name = model_name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模型加载失败: {e}")

    return {"status": "success", "model": model_name}
