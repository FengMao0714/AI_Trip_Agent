"""pgvector-backed semantic search for RAG knowledge chunks."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import Select, select

from app.db import connection
from app.models.db_models import KnowledgeChunk
from app.rag.embeddings import EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
MAX_TOP_K = 20


async def search(
    query_embedding: list[float],
    city: str | None = None,
    category: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Search knowledge chunks by cosine similarity.

    Args:
        query_embedding: Query vector produced by the embedding model.
        city: Optional city filter, for example "北京".
        category: Optional category filter, for example "景点".
        top_k: Maximum number of results.

    Returns:
        Knowledge chunk dictionaries with similarity scores.
    """
    _validate_search_args(query_embedding, top_k)

    start_time = time.perf_counter()
    if connection.async_session_factory is None:
        await connection.init_db()

    if connection.async_session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")

    distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)
    stmt = _build_search_statement(distance, city, category, top_k)

    async with connection.async_session_factory() as session:
        result = await session.execute(stmt)
        rows = result.all()

    documents = [_format_row(row) for row in rows]
    logger.info(
        "RAG vector search completed",
        extra={
            "city": city,
            "category": category,
            "top_k": top_k,
            "result_count": len(documents),
            "duration": round(time.perf_counter() - start_time, 3),
        },
    )
    return documents


def _build_search_statement(
    distance: Any,
    city: str | None,
    category: str | None,
    top_k: int,
) -> Select[tuple[str, str, dict[str, Any], float]]:
    """Build the SQLAlchemy vector search statement."""
    similarity_score = (1 - distance).label("similarity_score")
    stmt = select(
        KnowledgeChunk.title,
        KnowledgeChunk.content,
        KnowledgeChunk.metadata_,
        similarity_score,
    )

    if city:
        stmt = stmt.where(KnowledgeChunk.city == city)
    if category:
        stmt = stmt.where(KnowledgeChunk.category == category)

    return stmt.order_by(distance).limit(top_k)


def _format_row(row: Any) -> dict[str, Any]:
    """Format one SQLAlchemy result row as a plain dictionary."""
    return {
        "title": row.title,
        "content": row.content,
        "metadata": row.metadata_,
        "similarity_score": round(float(row.similarity_score), 4),
    }


def _validate_search_args(query_embedding: list[float], top_k: int) -> None:
    """Validate vector search arguments."""
    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            "query_embedding dimension mismatch: "
            f"expected {EMBEDDING_DIMENSION}, got {len(query_embedding)}"
        )
    if top_k <= 0 or top_k > MAX_TOP_K:
        raise ValueError(f"top_k must be between 1 and {MAX_TOP_K}.")
