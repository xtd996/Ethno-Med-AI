from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- LLM 提供商: "local" | "dashscope" | "openai" ---
    # "local" 指向 vLLM/SGLang/TGI 等推理框架暴露的 OpenAI 兼容 API
    llm_provider: str = "local"

    # --- 本地模型推理服务（vLLM / SGLang / TGI）---
    local_model_base_url: str = "http://localhost:8001/v1"
    local_model_api_key: str = "not-needed"
    professional_model_name: str = "deepseek-r1-7b"
    living_model_name: str = "qwen-chat-7b"

    # --- DashScope (通义千问) ---
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"

    # --- OpenAI 兼容 API ---
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # --- RAG ---
    rag_data_root: str = "RAG/datasets"
    rag_vector_store_path: str = "RAG/vector_store"
    rag_chunk_size: int = 300
    rag_chunk_overlap: int = 50

    # --- 嵌入模型 ---
    embedding_provider: str = "dashscope"  # "dashscope" | "huggingface"
    embedding_model: str = "text-embedding-v3"
    huggingface_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Reranker ---
    reranker_model: str = "BAAI/bge-reranker-base"
    reranker_top_n: int = 3
    enable_reranker: bool = True

    # --- 混合检索 ---
    hybrid_vector_weight: float = 0.6
    hybrid_bm25_weight: float = 0.4
    hybrid_search_k: int = 5

    # --- 服务 ---
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
