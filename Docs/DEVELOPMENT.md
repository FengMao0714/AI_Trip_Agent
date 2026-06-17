# Development Guide

## Prerequisites

- Python 3.11+
- uv
- Node.js 20+
- Corepack and pnpm
- Docker Desktop

## Local Setup

```powershell
Copy-Item .env.example .env
Copy-Item .env.example backend/.env
Copy-Item .env.example frontend/.env.local
```

Start PostgreSQL and Redis:

```powershell
docker compose up -d postgres redis
```

The default host ports are `15432` for PostgreSQL and `16379` for Redis so this project can run beside other local stacks. If you run the backend outside Docker, keep `POSTGRES_PORT=15432` and `REDIS_PORT=16379` in `backend/.env`.

Backend:

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
cd frontend
corepack enable
corepack pnpm install --frozen-lockfile
corepack pnpm dev
```

## Windows Helper

```powershell
.\scripts\start-dev.ps1
```

Use `-DockerOnly` to run the full Docker Compose stack. Use `-UseProxy -ProxyUrl http://127.0.0.1:10808` only when your local network requires a proxy for model or embedding downloads.

By default the helper enables `http://127.0.0.1:10808` for downloads such as Hugging Face model assets and keeps `token-plan-cn.xiaomimimo.com` in `NO_PROXY` so the Token Plan LLM endpoint is reached directly. Use `-NoProxy` only when your network does not need a proxy at all.

## Knowledge Ingestion

```powershell
cd backend
uv run python -m app.rag.ingest
```

Or from Docker:

```powershell
docker compose exec backend uv run python -m app.rag.ingest
```
