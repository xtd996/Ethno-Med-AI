import asyncio
import os
import threading
from typing import List, AsyncGenerator

import faiss
import numpy as np
import torch
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain.prompts import PromptTemplate
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer

app = FastAPI()

# 设置 DashScope API Key
os.environ["DASHSCOPE_API_KEY"] = "sk-3e5f2c93e985444e8dc9a9fda8e0d872"
embeddings = DashScopeEmbeddings(model="text-embedding-v3")

# 定义民族列表
ethnic_groups = ["藏族", "羌族", "彝族"]

# 加载所有民族的索引（仅用于专业模型）
vector_stores = {}
for ethnic in ethnic_groups:
    try:
        index_path = f"/app/RAG/vector_store/{ethnic}_index.index"
        index = faiss.read_index(index_path)
        metadata_path = f"/app/RAG/vector_store/{ethnic}_metadata.npy"
        metadata = np.load(metadata_path, allow_pickle=True)

        documents = [Document(
            page_content=meta["content"],
            metadata={k: v for k, v in meta.items() if k != "content"}
        ) for meta in metadata]

        if index.ntotal != len(documents):
            raise ValueError(f"索引条目数 ({index.ntotal}) 与元数据条目数 ({len(documents)}) 不一致")

        docstore = InMemoryDocstore({str(i): doc for i, doc in enumerate(documents)})
        index_to_docstore_id = {i: str(i) for i in range(index.ntotal)}

        vector_store = FAISS(
            embedding_function=embeddings,
            index=index,
            docstore=docstore,
            index_to_docstore_id=index_to_docstore_id
        )

        vector_stores[ethnic] = vector_store
        print(f"成功加载 {ethnic} 索引，条目数: {vector_store.index.ntotal}")
    except Exception as e:
        print(f"加载 {ethnic} 索引失败: {str(e)}")

# 模型和提示词配置
MODEL_CONFIG = {
    "专业模型": {
    "path": os.getenv("PROFESSIONAL_MODEL_PATH", "../../model/deepseek-r1-7B"),
    "prompt_template": """
【系统指令】
你是一个专业的医疗问答助手，仅使用中文回答。请严格遵守以下规则：
1. **信息来源**：  
   - 若【检索到的知识】为“无需检索，直接基于模型知识回答”，则基于你的内置医学知识作答，不得引用外部信息。  
   - 若【检索到的知识】包含具体内容，则严格基于这些知识回答，不得添加知识库未提及的信息（如新疗法、未提及的时间节点等）。  
   - 如知识不足，回复：“根据现有信息无法准确判断，请咨询专业医生。”  

2. **回答格式**：  
   - **结构清晰**，适当使用分点、列表或表格提高可读性。  
   - **精准表达**，不进行模糊推测，不得误导用户。  
   - **适当补充** 若适用，可给出相关健康建议（如生活习惯、饮食调整）。  

3. **医学安全性**：  
   - 避免直接给出医疗诊断，强调**应咨询专业医生**。  
   - 遇到紧急情况（如疑似心梗、中风），建议立即就医，而非尝试自我治疗。  

【对话历史】
{history}

【用户问题】
{question}

【检索到的知识】
{context}

请基于以上规则提供专业回答：
"""
}
,
    "生活模型": {
    "path": os.getenv("LIVING_MODEL_PATH", "../../model/qwen-chat-7b"),
    "system_prompt": """
你是一个友好的生活助手，使用中文回答，语气轻松自然。你的目标是帮助用户解答日常问题、提供建议或闲聊，确保对话流畅、自然、有趣。

### **回答原则**
1. **亲切幽默**  
   - 语气轻松自然，例如“这个问题挺有意思的，让我想想~”  
   - 适当使用表情（如“😊”、“😂”）增加互动感  
   - 避免生硬或过于正式的回答  

2. **引导用户**  
   - 如果用户提问模糊，可礼貌询问更多细节，如：“你想找什么样的建议呢？”  
   - 若回答后可以延续话题，主动提问，如：“你最近有尝试过这个方法吗？”  

3. **信息来源**  
   - 不使用外部知识库，仅基于你的内置知识回答。  
   - 如果问题超出你的知识范围，友好地建议用户查找资料，如：  
     “这个问题我不太清楚哦，建议你查查资料或问问专业人士。”  

4. **格式灵活**  
   - 简单问题 → 直接回答  
   - 复杂问题 → 分点或逐步解答  
   - 推荐类问题 → 可附加个人建议（如“如果你喜欢温暖的地方，可以考虑去海南旅游哦！”）  
"""
}

}

# 当前模型和提示词
current_model = None
current_model_name = None
current_prompt = None
tokenizer = None
streamer = None

def load_model(model_name: str):
    global current_model, current_model_name, current_prompt, tokenizer, streamer
    if current_model_name != model_name:
        if current_model is not None:
            del current_model
            torch.cuda.empty_cache()
        model_path = MODEL_CONFIG[model_name]["path"]
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        # 修复 pad_token 和 eos_token
        if tokenizer.pad_token_id is None or tokenizer.pad_token_id == tokenizer.eos_token_id:
            tokenizer.pad_token = "[PAD]"
            tokenizer.pad_token_id = tokenizer.convert_tokens_to_ids("[PAD]")
            if tokenizer.pad_token_id is None:
                tokenizer.add_special_tokens({"pad_token": "[PAD]"})
        current_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            local_files_only=True,
            torch_dtype="auto",  # 自动选择精度
            device_map="auto"    # 自动管理设备
        )
        if tokenizer.pad_token_id is None:
            current_model.resize_token_embeddings(len(tokenizer))
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        current_model_name = model_name
        if model_name == "专业模型":
            current_prompt = PromptTemplate(
                input_variables=["history", "question", "context"],
                template=MODEL_CONFIG[model_name]["prompt_template"]
            )
        else:
            current_prompt = None  # 生活模型使用 apply_chat_template
        print(f"已加载模型: {model_name}")

# 初始化默认模型
load_model("专业模型")

# 判断是否需要检索的关键词（仅专业模型使用）
ethnic_medicine_keywords = ["藏族医学", "藏医", "藏药", "彝族医学", "彝医", "彝药", "羌族医学", "羌医", "羌药"]
symptom_keywords = ["症状", "痛", "干", "咳嗽", "不适", "热", "肿", "痒", "晕"]

def needs_retrieval(query: str) -> bool:
    return current_model_name == "专业模型" and any(keyword in query for keyword in ethnic_medicine_keywords)

def is_symptom_related(query: str) -> bool:
    return any(keyword in query for keyword in symptom_keywords)

def infer_ethnic(query: str) -> str:
    ethnic_keywords = {
        "藏族": ["藏族", "藏医", "藏药"],
        "羌族": ["羌族", "羌医", "羌药"],
        "彝族": ["彝族", "彝医", "彝药"]
    }
    for ethnic, keywords in ethnic_keywords.items():
        if any(kw in query for kw in keywords):
            return ethnic
    return "藏族"

async def stream_response(query: str, history: str) -> AsyncGenerator[str, None]:
    print(f"\n=== 接收到的原始查询: {query} ===")

    history_lines = history.split("\n")
    past_questions = [line.split(": ")[1] for line in history_lines if line.startswith("user: ")]

    if query.startswith("我的第") and "问题" in query:
        try:
            question_num = int(query[3]) - 1
            if 0 <= question_num < len(past_questions):
                yield past_questions[question_num]
            else:
                yield "对话历史中没有对应的问题。"
            return
        except ValueError:
            yield "问题格式错误，请明确指定第几个问题。"
            return

    if current_model_name == "专业模型":
        if needs_retrieval(query):
            symptom_query = None
            for q in reversed(past_questions):
                if is_symptom_related(q):
                    symptom_query = q
                    break
            retrieval_query = symptom_query if symptom_query else query
            print(f"触发检索，检索内容: {retrieval_query}")

            ethnic = infer_ethnic(query)
            retriever = vector_stores[ethnic].as_retriever(search_kwargs={"k": 3})
            docs = retriever.invoke(retrieval_query)
            context = "\n".join(
                [f"来源: {doc.metadata['source']} (章节: {doc.metadata['chapter']})\n内容: {doc.page_content}" for doc in docs])
        else:
            context = "无需检索，直接基于模型知识回答。"
        full_prompt = current_prompt.format(history=history, question=query, context=context)
    else:  # 生活模型
        # 构造聊天模板
        messages = [{"role": "system", "content": MODEL_CONFIG["生活模型"]["system_prompt"]}]
        if history:
            history_pairs = history.split("\n")
            for i in range(0, len(history_pairs), 2):
                user_msg = history_pairs[i].replace("user: ", "")
                assistant_msg = history_pairs[i+1].replace("assistant: ", "") if i+1 < len(history_pairs) else ""
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": assistant_msg})
        messages.append({"role": "user", "content": query})
        full_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

    print(f"=== 用户提问: {query} ===")
    print(f"最终输入模型的模板:\n{full_prompt}")
    print("=== 生成开始 ===")

    inputs = tokenizer(full_prompt, return_tensors="pt", padding=True, truncation=True, max_length=512).to(current_model.device)
    generation_kwargs = {
        "input_ids": inputs["input_ids"],
        "attention_mask": inputs["attention_mask"],
        "max_new_tokens": 2048 if current_model_name == "生活模型" else 1024, # 增加生成长度
        "max_length": 4096,      # 增加最大长度
        "repetition_penalty": 1.1,
        "temperature": 0.7,
        "top_p": 0.9,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }

    thread = threading.Thread(target=current_model.generate, kwargs={**generation_kwargs, "streamer": streamer})
    thread.start()

    for new_text in streamer:
        cleaned_text = new_text.replace("</think>", "").strip()
        if cleaned_text:
            yield cleaned_text
            await asyncio.sleep(0.01)

    thread.join()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class SwitchModelRequest(BaseModel):
    model_name: str

@app.post("/chat")
async def chat(request: ChatRequest):
    print(f"接收到的请求体: {request.model_dump()}")
    history = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages[:-1]])
    query = request.messages[-1].content
    return StreamingResponse(
        stream_response(query, history),
        media_type="text/plain; charset=utf-8",
        headers={"X-Accel-Buffering": "no"}
    )

@app.post("/switch_model")
async def switch_model(request: SwitchModelRequest):
    model_name = request.model_name
    if model_name in MODEL_CONFIG:
        load_model(model_name)
        return {"status": "success", "model": model_name}
    return {"status": "error", "message": "Invalid model name"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)