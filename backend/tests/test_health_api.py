"""健康检查 API 测试。"""
import pytest
from fastapi.testclient import TestClient


class TestHealthAPI:
    def test_health_check(self, mock_app):
        """测试健康检查端点。"""
        client = TestClient(mock_app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "current_model" in data
        assert "llm_provider" in data
        assert "loaded_ethnic_indices" in data

    def test_health_returns_loaded_indices(self, mock_app):
        """测试健康检查返回已加载的民族索引。"""
        client = TestClient(mock_app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # mock_app fixture 中 mock 了藏族和羌族的向量存储
        assert isinstance(data["loaded_ethnic_indices"], list)
