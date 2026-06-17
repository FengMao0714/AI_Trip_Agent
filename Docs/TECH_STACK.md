# Technical Stack

## Backend

| Area | Choice |
| --- | --- |
| Runtime | Python 3.12 |
| Web framework | FastAPI, Uvicorn |
| Agent orchestration | LangGraph, LangChain Core |
| LLM adapter | `langchain-openai` with an OpenAI-compatible DeepSeek endpoint |
| Data validation | Pydantic v2, pydantic-settings |
| Database | PostgreSQL 16 with pgvector |
| Cache/session store | Redis 7 |
| Vector/RAG utilities | sentence-transformers, pgvector, pandas, pyarrow |
| Package manager | uv |
| Quality tools | pytest, pytest-asyncio, ruff, mypy |

## Frontend

| Area | Choice |
| --- | --- |
| Runtime | Node.js with pnpm |
| Framework | Next.js 15 App Router |
| UI runtime | React 19 |
| Styling | Tailwind CSS, class-variance-authority, tailwind-merge |
| Components | Radix UI primitives, local UI components |
| Icons | lucide-react |
| State | Zustand and component-level React state |
| Map integration | AMap JS API loader |
| Quality tools | ESLint 9, TypeScript, Playwright |

## Infrastructure

| Area | Choice |
| --- | --- |
| Local orchestration | Docker Compose |
| Backend image | Python slim image with uv-managed dependencies |
| Frontend image | Next.js standalone production build |
| CI | GitHub Actions for backend and frontend checks |
| Pre-commit | ruff, ruff-format, mypy, frontend lint/typecheck, basic hygiene hooks |

## Integration Points

- `DEEPSEEK_API_KEY` enables live LLM planning.
- `AMAP_API_KEY` enables backend AMap REST tools.
- `NEXT_PUBLIC_AMAP_KEY` and `NEXT_PUBLIC_AMAP_SECRET` enable frontend map rendering.
- PostgreSQL stores relational and vector data.
- Redis stores session and cache data.

## Version Source Of Truth

- Backend dependencies: `backend/pyproject.toml` and `backend/uv.lock`.
- Frontend dependencies: `frontend/package.json` and `frontend/pnpm-lock.yaml`.
- Docker runtime: `docker-compose.yml`, `backend/Dockerfile`, and `frontend/Dockerfile`.

