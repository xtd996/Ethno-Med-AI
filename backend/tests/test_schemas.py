"""Pydantic 模型测试。"""
import pytest
from pydantic import ValidationError
from app.schemas.chat import ChatMessage, ChatRequest, SwitchModelRequest, ModelInfo, ErrorResponse


class TestChatMessage:
    def test_valid_message(self):
        msg = ChatMessage(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"

    def test_missing_role(self):
        with pytest.raises(ValidationError):
            ChatMessage(content="你好")

    def test_missing_content(self):
        with pytest.raises(ValidationError):
            ChatMessage(role="user")


class TestChatRequest:
    def test_valid_request(self):
        req = ChatRequest(messages=[
            ChatMessage(role="user", content="你好"),
            ChatMessage(role="assistant", content="你好！"),
            ChatMessage(role="user", content="藏医有什么疗法？"),
        ])
        assert len(req.messages) == 3

    def test_empty_messages(self):
        req = ChatRequest(messages=[])
        assert len(req.messages) == 0


class TestSwitchModelRequest:
    def test_valid(self):
        req = SwitchModelRequest(model_name="专业模型")
        assert req.model_name == "专业模型"


class TestModelInfo:
    def test_valid(self):
        info = ModelInfo(name="专业模型", description="民族医药问答", provider="local")
        assert info.name == "专业模型"


class TestErrorResponse:
    def test_valid(self):
        err = ErrorResponse(error="出错了", code=500)
        assert err.code == 500
