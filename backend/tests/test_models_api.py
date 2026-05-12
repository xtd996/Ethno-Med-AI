"""模型管理 API 测试。"""
import pytest
from fastapi.testclient import TestClient


class TestModelsAPI:
    def test_list_models(self, mock_app):
        """测试列出所有可用模型。"""
        client = TestClient(mock_app)
        response = client.get("/models")
        assert response.status_code == 200
        models = response.json()
        assert len(models) == 2
        model_names = [m["name"] for m in models]
        assert "专业模型" in model_names
        assert "生活模型" in model_names

    def test_list_models_structure(self, mock_app):
        """测试模型列表返回结构。"""
        client = TestClient(mock_app)
        response = client.get("/models")
        models = response.json()
        for model in models:
            assert "name" in model
            assert "description" in model
            assert "provider" in model

    def test_switch_model_invalid(self, mock_app):
        """测试切换到无效模型。"""
        client = TestClient(mock_app)
        response = client.post("/models/switch", json={"model_name": "不存在的模型"})
        assert response.status_code == 400
        data = response.json()
        assert "无效的模型名称" in data["detail"]
