import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, settings
from app.api import chat as chat_api
from app.api import health as health_api
from app.api import models as models_api
from app.services.embeddings import create_embeddings
from app.services.graph import build_chat_graph
from app.services.llm_factory import create_llm
from app.services.vector_store import load_vector_stores


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时加载模型和向量存储，关闭时清理资源。"""
    config: Settings = app.state.config

    # 如果配置了 DashScope API Key，设置环境变量
    if config.dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = config.dashscope_api_key

    # 加载嵌入模型
    print("正在加载嵌入模型...")
    embeddings = create_embeddings(config)
    app.state.embeddings = embeddings

    # 加载向量存储
    print("正在加载向量存储...")
    vector_stores = load_vector_stores(config, embeddings)
    app.state.vector_stores = vector_stores
    print(f"已加载 {len(vector_stores)} 个民族索引: {list(vector_stores.keys())}")

    # 构建混合检索器
    from app.services.retrievers import build_hybrid_retrievers_for_ethnic_groups
    print("正在构建混合检索器...")
    hybrid_retrievers = build_hybrid_retrievers_for_ethnic_groups(vector_stores)
    app.state.hybrid_retrievers = hybrid_retrievers
    app.state.enable_reranker = config.enable_reranker
    print(f"混合检索器构建完成: {list(hybrid_retrievers.keys())}")

    # 初始化默认 LLM（专业模型）
    print("正在初始化默认模型（专业模型）...")
    try:
        llm_result = create_llm(config, "professional")
        app.state.current_llm = llm_result["llm"]
        app.state.current_model_name = "专业模型"
        print("专业模型初始化完成")
    except Exception as e:
        print(f"专业模型初始化失败: {e}，尝试加载生活模型...")
        try:
            llm_result = create_llm(config, "living")
            app.state.current_llm = llm_result["llm"]
            app.state.current_model_name = "生活模型"
            print("生活模型初始化完成")
        except Exception as e2:
            print(f"生活模型也初始化失败: {e2}，服务将启动但无法生成回答")
            app.state.current_llm = None
            app.state.current_model_name = None

    # 构建 LangGraph 对话图
    chat_graph = build_chat_graph()
    app.state.chat_graph = chat_graph
    print("LangGraph 对话图构建完成")

    print(f"服务启动完成，监听 {config.host}:{config.port}")
    yield

    # 清理
    print("服务关闭，清理资源...")
    if hasattr(app.state, "current_llm") and app.state.current_llm is not None:
        del app.state.current_llm
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(
        title="Ethno Med AI - 民医智问",
        description="少数民族医药问答系统 API",
        version="0.2.0",
        lifespan=lifespan,
    )

    # 存储配置
    app.state.config = settings

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "code": 500},
        )

    # 注册路由
    app.include_router(health_api.router)
    app.include_router(models_api.router)
    app.include_router(chat_api.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
