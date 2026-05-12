import json

from fastapi import APIRouter, Request
from langchain_core.messages import AIMessageChunk
from sse_starlette.sse import EventSourceResponse

from app.schemas.chat import ChatRequest

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    """流式聊天端点，返回 SSE 事件流。"""
    # 解析请求
    messages = body.messages
    if not messages:
        async def empty_error():
            yield {"event": "error", "data": json.dumps({"error": "消息列表为空"}, ensure_ascii=False)}
        return EventSourceResponse(empty_error())

    query = messages[-1].content
    history = "\n".join(f"{msg.role}: {msg.content}" for msg in messages[:-1])

    # 获取当前 LLM 和 graph
    llm = request.app.state.current_llm
    graph = request.app.state.chat_graph
    vector_stores = request.app.state.vector_stores
    model_name = request.app.state.current_model_name

    initial_state = {
        "query": query,
        "history": history,
        "model_name": model_name,
        "ethnic_group": "",
        "needs_retrieval": False,
        "context": "",
        "response": "",
    }

    runtime_config = {
        "configurable": {
            "llm": llm,
            "vector_stores": vector_stores,
            "hybrid_retrievers": getattr(request.app.state, "hybrid_retrievers", {}),
            "enable_reranker": getattr(request.app.state, "enable_reranker", False),
        }
    }

    async def event_generator():
        try:
            # 使用 graph.astream stream_mode="messages" 获取 LLM token 流
            # 检测与检索节点会同步完成，generate 节点的 LLM 调用会被流式捕获
            full_response = ""
            async for event in graph.astream(
                initial_state,
                config=runtime_config,
                stream_mode="messages",
            ):
                # event 是 (message_chunk, metadata) 元组
                chunk, metadata = event
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    token_text = chunk.content
                    full_response += token_text
                    yield {
                        "event": "message",
                        "data": json.dumps({"token": token_text}, ensure_ascii=False),
                    }

            # 发送完成信号
            yield {"event": "done", "data": "[DONE]"}

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())
