"""RAG search LangChain tool backed by pgvector."""

from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.tools import tool

from app.rag.embeddings import encode
from app.rag.vectorstore import search as vector_search

logger = logging.getLogger(__name__)


@tool
async def rag_search(query: str, city: str, top_k: int = 5) -> list[dict]:
    """Search the travel knowledge base for relevant local information.

    Args:
        query: Search query, for example "北京有哪些历史文化景点".
        city: City scope for retrieval.
        top_k: Maximum number of knowledge chunks to return, default is 5.

    Returns:
        A list of knowledge chunk dictionaries containing title, content,
        metadata and similarity_score.
    """
    start_time = time.perf_counter()
    logger.info("RAG search query=%s city=%s top_k=%d", query, city, top_k)

    try:
        query_embedding = encode(query)
        results = await vector_search(query_embedding, city=city, top_k=top_k)
        logger.info(
            "RAG search completed",
            extra={
                "city": city,
                "top_k": top_k,
                "result_count": len(results),
                "duration": round(time.perf_counter() - start_time, 3),
            },
        )
        return results
    except Exception as exc:
        logger.exception("RAG search failed: %s", exc)
        return [_format_error(exc)]


def _format_error(exc: Exception) -> dict[str, Any]:
    """Format tool errors as data instead of raising into the Agent loop."""
    return {"error": f"RAG 检索暂不可用: {exc}"}
