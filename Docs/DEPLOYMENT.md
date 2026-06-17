# Deployment Notes

The repository is prepared for containerized deployment, but no production hosting target is hard-coded.

## Docker Compose

```powershell
docker compose up --build
```

Services:

- `frontend`: Next.js app exposed on port `3000`.
- `backend`: FastAPI service exposed on port `8000`.
- `postgres`: PostgreSQL with pgvector exposed on host port `15432` by default.
- `redis`: Redis exposed on host port `16379` by default.

Inside the Compose network, services still use `postgres:5432` and `redis:6379`. Override `POSTGRES_HOST_PORT` or `REDIS_HOST_PORT` only if you need different host ports.

## Production Checklist

- Create deployment-specific environment variables instead of committing `.env`.
- Restrict AMap browser keys by domain.
- Rotate any API keys that were previously stored in local `.env` files.
- Use managed PostgreSQL and Redis when deploying beyond local demos.
- Add HTTPS and a reverse proxy or platform routing layer.
- Configure backend CORS for the deployed frontend domain.
- Run RAG ingestion during release or as a controlled admin job.
