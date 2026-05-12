from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from app.services.rag_chain import (
    LIVING_SYSTEM_PROMPT,
    get_professional_prompt,
)
from app.services.reranker import rerank_documents
from app.utils.ethnic_detector import infer_ethnic, is_symptom_related, needs_retrieval


# ============================================================
#  Graph State
# ============================================================
class ChatState(TypedDict):
    query: str
    history: str
    model_name: str
    ethnic_group: str
    needs_retrieval: bool
    context: str
    response: Annotated[str, "最终生成的回答"]


# ============================================================
#  节点函数
# ============================================================
def detect_intent(state: ChatState) -> dict[str, Any]:
    """分析用户查询，推断民族与是否需要检索。"""
    query = state["query"]
    model_name = state.get("model_name", "专业模型")

    ethnic_group = infer_ethnic(query)
    should_retrieve = needs_retrieval(query, model_name)

    return {
        "ethnic_group": ethnic_group,
        "needs_retrieval": should_retrieve,
    }


def retrieve(state: ChatState, *, config: dict[str, Any]) -> dict[str, str]:
    """从混合检索器或纯向量检索获取相关文档。"""
    ethnic = state["ethnic_group"]
    query = state["query"]

    # 在历史对话中查找症状相关问题作为检索 query
    history = state.get("history", "")
    retrieval_query = query
    if history:
        history_lines = history.split("\n")
        past_questions = [
            line.split(": ", 1)[1]
            for line in history_lines
            if line.startswith("user: ")
        ]
        for q in reversed(past_questions):
            if is_symptom_related(q):
                retrieval_query = q
                break

    # 优先使用混合检索器
    hybrid_retrievers = config["configurable"].get("hybrid_retrievers", {})
    vector_stores = config["configurable"].get("vector_stores", {})

    if ethnic in hybrid_retrievers:
        docs = hybrid_retrievers[ethnic].invoke(retrieval_query)
    elif ethnic in vector_stores:
        retriever = vector_stores[ethnic].as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(retrieval_query)
    else:
        return {"context": "未找到该民族的向量索引，直接基于模型知识回答。"}

    # 重排序（如果启用）
    enable_reranker = config["configurable"].get("enable_reranker", False)
    if enable_reranker and docs:
        docs = rerank_documents(retrieval_query, docs)

    from app.services.rag_chain import format_docs
    context = format_docs(docs)
    return {"context": context}


async def generate(state: ChatState, *, config: dict[str, Any]) -> dict[str, str]:
    """使用 LLM 生成回答。使用 astream 以支持 stream_mode="messages" 流式捕获。"""
    llm: Runnable = config["configurable"]["llm"]
    tokenizer = config["configurable"].get("tokenizer")
    model_name = state.get("model_name", "专业模型")
    query = state["query"]
    history = state.get("history", "")
    context = state.get("context", "无需检索，直接基于模型知识回答。")

    async def _collect_stream(stream_iter) -> str:
        """从 LLM 流中收集完整响应文本。"""
        collected = ""
        async for chunk in stream_iter:
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            collected += content
        return collected

    if model_name == "专业模型":
        prompt = get_professional_prompt().format(
            history=history,
            question=query,
            context=context,
        )
        response = await _collect_stream(llm.astream(prompt))
    else:
        # 生活模型：优先使用 tokenizer.apply_chat_template，回退到 LangChain ChatPromptTemplate
        if tokenizer is not None:
            messages = [{"role": "system", "content": LIVING_SYSTEM_PROMPT}]
            if history:
                for line in history.split("\n"):
                    if line.startswith("user: "):
                        messages.append({"role": "user", "content": line[6:]})
                    elif line.startswith("assistant: "):
                        messages.append({"role": "assistant", "content": line[11:]})
            messages.append({"role": "user", "content": query})
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            response = await _collect_stream(llm.astream(prompt))
        else:
            from langchain_core.messages import AIMessage, HumanMessage
            from langchain_core.prompts import ChatPromptTemplate

            chat_prompt = ChatPromptTemplate.from_messages([
                ("system", LIVING_SYSTEM_PROMPT),
                ("placeholder", "{history_messages}"),
                ("human", "{question}"),
            ])
            history_messages: list[BaseMessage] = []
            if history:
                for line in history.split("\n"):
                    if line.startswith("user: "):
                        history_messages.append(HumanMessage(content=line[6:]))
                    elif line.startswith("assistant: "):
                        history_messages.append(AIMessage(content=line[11:]))

            chain = chat_prompt | llm
            response = await _collect_stream(chain.astream({
                "history_messages": history_messages,
                "question": query,
            }))

    return {"response": response}


# ============================================================
#  条件路由
# ============================================================
def _route_after_intent(state: ChatState) -> str:
    if state.get("needs_retrieval", False):
        return "retrieve"
    return "generate"


# ============================================================
#  构建 Graph
# ============================================================
def build_chat_graph() -> Any:
    """构建 LangGraph 对话工作流。

    流程:
        START -> detect_intent
            -> (needs_retrieval) -> retrieve -> generate -> END
            -> (!needs_retrieval) -> generate -> END
    """
    graph = StateGraph(ChatState)

    graph.add_node("detect_intent", detect_intent)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)

    graph.add_edge(START, "detect_intent")
    graph.add_conditional_edges(
        "detect_intent",
        _route_after_intent,
        {"retrieve": "retrieve", "generate": "generate"},
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()
