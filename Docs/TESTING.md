# Testing

## Backend

```powershell
cd backend
uv sync
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app --ignore-missing-imports
uv run pytest tests -q
```

Some tests require PostgreSQL and Redis. Start them first:

```powershell
docker compose up -d postgres redis
```

Compose exposes PostgreSQL on `localhost:15432` and Redis on `localhost:16379` by default. Use those ports for local backend test runs outside Docker.

For tests that should not call real external services, use placeholder keys and demo mode:

```powershell
$env:DEEPSEEK_API_KEY = "sk-test-key"
$env:AMAP_API_KEY = "test-amap-key"
$env:DEMO_MODE = "true"
```

## Frontend

```powershell
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm build
corepack pnpm test:e2e
```

Playwright starts the Next.js dev server on port `3100` according to `playwright.config.ts`.
