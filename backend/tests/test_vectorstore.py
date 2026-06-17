"""Vectorstore search helper tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.rag import vectorstore
from app.rag.embeddings import EMBEDDING_DIMENSION


def test_validate_search_args_rejects_wrong_dimension() -> None:
    """Vector search requires 1024-dimensional embeddings."""
    with pytest.raises(ValueError, match="dimension mismatch"):
        vectorstore._validate_search_args([0.1, 0.2], top_k=5)


def test_validate_search_args_rejects_invalid_top_k() -> None:
    """Search result size is bounded."""
    with pytest.raises(ValueError, match="top_k"):
        vectorstore._validate_search_args([0.1] * EMBEDDING_DIMENSION, top_k=0)

    with pytest.raises(ValueError, match="top_k"):
        vectorstore._validate_search_args(
            [0.1] * EMBEDDING_DIMENSION,
            top_k=vectorstore.MAX_TOP_K + 1,
        )


def test_format_row_returns_document_dict() -> None:
    """Database rows are normalized for RAG tool output."""
    row = SimpleNamespace(
        title="故宫博物院",
        content="故宫博物院位于北京市中心。",
        metadata_={"address": "北京市东城区景山前街4号"},
        similarity_score=0.87654,
    )

    assert vectorstore._format_row(row) == {
        "title": "故宫博物院",
        "content": "故宫博物院位于北京市中心。",
        "metadata": {"address": "北京市东城区景山前街4号"},
        "similarity_score": 0.8765,
    }
