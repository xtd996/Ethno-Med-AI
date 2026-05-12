from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request) -> dict:
    """返回服务状态和已加载的模型信息。"""
    current_model: str = getattr(request.app.state, "current_model_name", "未加载")
    vector_stores: dict = getattr(request.app.state, "vector_stores", {})
    provider: str = getattr(request.app.state.config, "llm_provider", "未知") if hasattr(request.app.state, "config") else "未知"

    return {
        "status": "ok",
        "current_model": current_model,
        "llm_provider": provider,
        "loaded_ethnic_indices": list(vector_stores.keys()),
    }
