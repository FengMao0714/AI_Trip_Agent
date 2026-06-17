"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.api.router import api_router
from app.config import get_settings
from app.db.connection import close_db, init_db
from app.rag.embeddings import load_embedding_model
from app.services.cache import close_redis, init_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    logger.info("Starting Trip Planner backend", extra={"app": app.title})
    await init_db()
    await init_redis()
    if get_settings().preload_embedding_model:
        load_embedding_model()
    yield
    await close_redis()
    await close_db()
    logger.info("Stopping Trip Planner backend", extra={"app": app.title})


app = FastAPI(
    title="AI Trip Agent API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return documented 400 responses for invalid API request bodies."""
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors(), "path": str(request.url.path)},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
