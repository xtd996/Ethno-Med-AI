# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ethno Med AI (民医智问) is a Chinese ethnic minority medicine Q&A system with a RAG (Retrieval-Augmented Generation) pipeline. It provides two modes: a **professional medical model** (fine-tuned, uses RAG retrieval from ethnic medicine knowledge base) and a **daily life model** (general chat, no retrieval).

## Architecture

```
web/backend/backend.py   — FastAPI server: loads LLM models, serves /chat (streaming) and /switch_model endpoints
web/frontend/frontend.py — Streamlit UI: chat interface, session management, model switching
RAG/知识向量库构建.py       — Builds FAISS vector indices from .docx documents in RAG/datasets/
RAG/datasets/            — Source documents organized by ethnicity (藏族/羌族/彝族)
RAG/vector_store/        — Pre-built FAISS indices and metadata (.index + .npy files per ethnicity)
model/                   — Local LLM model weights (deepseek-r1-7B, qwen-chat-7b)
```

**Data flow**: User query → Streamlit frontend → FastAPI backend → (if professional model + ethnic medicine keywords) FAISS retrieval → LLM generates streamed response → displayed in frontend.

**Key design decisions**:
- Ethnic group is inferred from keywords in the query using jieba tokenization (藏族/羌族/彝族)
- Retrieval is triggered only when the professional model is active AND ethnic medicine keywords are present
- The backend uses HuggingFace `transformers` with `TextIteratorStreamer` for streaming generation
- Embeddings use DashScope API (text-embedding-v3) — requires `DASHSCOPE_API_KEY`

## Commands

### RAG index building
```bash
cd RAG
python 知识向量库构建.py --build
```

### Run backend (local, without Docker)
```bash
cd web/backend
uvicorn backend:app --host 0.0.0.0 --port 8000
```

### Run frontend
```bash
cd web/frontend
streamlit run frontend.py
```

### Docker (full stack)
```bash
# Set model paths first
export PROFESSIONAL_MODEL_DIR=path/to/deepseek-r1-7B
export LIVING_MODEL_DIR=path/to/qwen-chat-7b
docker-compose up
```
Backend at :8000, frontend at :8501. Requires NVIDIA GPU with CUDA 11.8.

## Environment

- **Python**: 3.11.9 (Poetry) or 3.10.16 (Conda/Docker)
- **Package manager**: Poetry 1.8.5 (local dev), Conda environment.yml (Docker)
- **Key dependencies**: FastAPI, Streamlit, LangChain, FAISS, HuggingFace Transformers, DashScope embeddings, jieba
- **GPU**: NVIDIA CUDA 11.8 required for model inference

## Important Notes

- The `DASHSCOPE_API_KEY` is currently hardcoded in both `backend.py` and `知识向量库构建.py` — this should be moved to environment variables
- Model paths in `backend.py` default to relative paths (`../../model/...`) which differ between local and Docker execution; use env vars `PROFESSIONAL_MODEL_PATH` and `LIVING_MODEL_PATH` to override
- The Streamlit frontend calls backend at `localhost:8000` — in Docker, this is handled via the `ethno-med-ai-network` bridge network
- FAISS index files in `RAG/vector_store/` have encoded filenames (UTF-8 encoding artifacts) — the actual ethnicity names are 藏族/羌族/彝族
