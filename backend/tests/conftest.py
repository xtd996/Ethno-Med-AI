"""测试配置和 fixtures。"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.config import Settings


@pytest.fixture
def mock_settings():
    """创建测试用配置。"""
    return Settings(
        llm_provider="dashscope",
        dashscope_api_key="test-key",
        dashscope_model="qwen-plus",
        professional_model_path="/tmp/test-model",
        living_model_path="/tmp/test-model",
        rag_vector_store_path="/tmp/test-vectors",
        embedding_provider="dashscope",
        embedding_model="text-embedding-v3",
        enable_reranker=False,
    )


@pytest.fixture
def mock_app(mock_settings):
    """创建测试用 FastAPI 应用（不加载真实模型）。"""
    from unittest.mock import patch
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    # Mock 所有外部依赖
    with patch("app.main.create_embeddings") as mock_emb, \
         patch("app.main.load_vector_stores") as mock_vs, \
         patch("app.main.create_llm") as mock_llm, \
         patch("app.main.build_chat_graph") as mock_graph, \
         patch("app.services.retrievers.build_hybrid_retrievers_for_ethnic_groups") as mock_hybrid:

        mock_emb.return_value = MagicMock()
        mock_vs.return_value = {"藏族": MagicMock(), "羌族": MagicMock()}
        mock_llm.return_value = {"llm": MagicMock(), "tokenizer": None}
        mock_graph.return_value = MagicMock()
        mock_hybrid.return_value = {}

        from app.main import create_app
        app = create_app()
        yield app
