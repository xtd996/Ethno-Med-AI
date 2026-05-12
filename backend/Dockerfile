FROM python:3.11-slim AS base

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖（无 torch/transformers，模型推理由 vLLM 独立服务承担）
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    pip install --no-cache-dir \
    fastapi uvicorn pydantic-settings \
    langchain langchain-core langchain-community langchain-openai langgraph \
    dashscope faiss-cpu jieba numpy python-dotenv sse-starlette

# 复制应用代码
COPY backend/app ./app
COPY rag ./rag

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
