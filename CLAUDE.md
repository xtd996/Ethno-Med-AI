# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ethno Med AI (民医智问) is a Chinese ethnic minority medicine Q&A system with a RAG (Retrieval-Augmented Generation) pipeline. It provides two modes: a **professional medical model** (uses RAG retrieval from ethnic medicine knowledge base) and a **daily life model** (general chat, no retrieval).

## Architecture

```
backend/app/               — FastAPI backend (modular)
  ├── main.py              — App entry point with lifespan management
  ├── config.py            — pydantic-settings configuration
  ├── api/                 — API routes (chat, models, health)
  ├── services/            — Business logic (LLM, RAG, Graph, Retrievers)
  ├── schemas/             — Pydantic models
  └── utils/               — Utility functions (ethnic detection)
frontend/src/              — Next.js 14 frontend
  ├── app/                 — Pages (home, chat, settings)
  ├── components/          — React components (ChatMessage, ChatInput, Sidebar)
  ├── hooks/               — useChat hook (SSE streaming)
  └── lib/                 — API client
rag/                       — RAG index building
  ├── build_index.py       — FAISS index builder (refactored)
  ├── datasets/            — Source .docx documents (藏族/羌族/彝族)
  └── vector_store/        — Pre-built FAISS indices
```

**Data flow**: User → Next.js frontend → SSE stream → FastAPI → LangGraph (detect_intent → retrieve → generate) → response

**Key technologies**:
- **Backend**: FastAPI + LangChain + LangGraph
- **Frontend**: Next.js 14 + React 18 + Tailwind CSS
- **RAG**: FAISS + BM25 hybrid retrieval + Cross-Encoder reranking
- **Models**: Local HuggingFace / DashScope / OpenAI (switchable)

## Commands

### Backend
```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### RAG index building
```bash
cd rag
python -m rag.build_index --build
```

### Tests
```bash
cd backend && pytest tests/ -v
```

### Docker (full stack)
```bash
cp .env.example .env  # Configure DASHSCOPE_API_KEY etc.
docker-compose up
```

## Configuration

All configuration via `.env` file (see `.env.example`):
- `LLM_PROVIDER` — "local" | "dashscope" | "openai"
- `DASHSCOPE_API_KEY` — Required for DashScope embeddings and LLM
- `PROFESSIONAL_MODEL_PATH` / `LIVING_MODEL_PATH` — Local model paths
- `ENABLE_RERANKER` — Enable Cross-Encoder reranking
- `HYBRID_VECTOR_WEIGHT` / `HYBRID_BM25_WEIGHT` — Hybrid retrieval weights

## Environment

- **Python**: 3.11+
- **Node.js**: 20+
- **Package manager**: Poetry (backend), npm (frontend)
- **GPU**: NVIDIA GPU required for local model inference
