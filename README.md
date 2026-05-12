# 民医智问 - Ethno Med AI

少数民族医药智能问答系统，融合藏族、羌族、彝族千年医药智慧，以 AI 技术传承与发扬民族医学。

## 功能特性

- **双模型切换**：专业医药模型（RAG 增强）+ 日常生活模型
- **混合检索**：BM25 + 向量检索 + Cross-Encoder 重排序
- **多民族支持**：藏族、羌族、彝族医药知识库
- **流式对话**：SSE 实时流式输出
- **LangChain/LangGraph**：标准化 RAG 管道和对话工作流

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Next.js 14 + React 18 + Tailwind CSS |
| 后端 | FastAPI + LangChain + LangGraph |
| 向量库 | FAISS + DashScope Embeddings |
| 模型 | 本地 HuggingFace / DashScope / OpenAI 可切换 |
| 部署 | Docker + GitHub Actions CI/CD |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- NVIDIA GPU（本地模型推理需要）

### 1. 克隆项目

```bash
git clone https://github.com/your-username/EthnoMedAI.git
cd EthnoMedAI
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY 等配置
```

### 3. 启动后端

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### Docker 部署

```bash
docker-compose up -d
```

前端: http://localhost:3000
后端 API: http://localhost:8000

## 项目结构

```
EthnoMedAI/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 路由
│   │   ├── services/        # 业务服务（LLM、RAG、Graph）
│   │   ├── schemas/         # Pydantic 模型
│   │   └── utils/           # 工具函数
│   └── tests/               # 后端测试
├── frontend/                # Next.js 前端
│   └── src/
│       ├── app/             # 页面
│       ├── components/      # 组件
│       ├── hooks/           # React Hooks
│       └── lib/             # API 客户端
├── rag/                     # RAG 索引构建
│   ├── datasets/            # 源文档（藏族/羌族/彝族）
│   └── build_index.py       # 索引构建脚本
└── docker-compose.yml
```

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger 文档。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/models` | GET | 列出可用模型 |
| `/models/switch` | POST | 切换模型 |
| `/chat` | POST | 流式聊天（SSE） |

## 开发

### 运行测试

```bash
# 后端测试
cd backend && pytest tests/ -v

# 前端类型检查
cd frontend && npx tsc --noEmit
```

### 代码规范

```bash
ruff check backend/
```

## 许可证

MIT License
