from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    token: str


class SwitchModelRequest(BaseModel):
    model_name: str


class ModelInfo(BaseModel):
    name: str
    description: str
    provider: str


class ErrorResponse(BaseModel):
    error: str
    code: int
