"""Embedding model loading and encoding helpers for RAG."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from typing import Any, cast, overload

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "BAAI/bge-large-zh-v1.5"
EMBEDDING_DIMENSION = 1024

_embedding_model: Any | None = None


def load_embedding_model() -> Any:
    """Load and cache the local BGE embedding model.

    Returns:
        Cached sentence-transformers model instance.

    Raises:
        RuntimeError: If the loaded model does not expose the expected dimension.
    """
    global _embedding_model

    if _embedding_model is not None:
        return _embedding_model

    start_time = time.perf_counter()
    logger.info(
        "Loading embedding model",
        extra={"model": EMBEDDING_MODEL_NAME, "device": "cpu"},
    )

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
    dimension = _get_model_dimension(model)
    if dimension != EMBEDDING_DIMENSION:
        raise RuntimeError(
            "Embedding model dimension mismatch: "
            f"expected {EMBEDDING_DIMENSION}, got {dimension}"
        )

    _embedding_model = model
    logger.info(
        "Embedding model loaded",
        extra={
            "model": EMBEDDING_MODEL_NAME,
            "dimension": EMBEDDING_DIMENSION,
            "duration": round(time.perf_counter() - start_time, 3),
        },
    )
    return _embedding_model


def get_embedding_model() -> Any:
    """Return the cached embedding model, loading it on first use.

    Returns:
        Cached sentence-transformers model instance.
    """
    return load_embedding_model()


@overload
def encode(text: str) -> list[float]: ...


@overload
def encode(text: list[str]) -> list[list[float]]: ...


def encode(text: str | Sequence[str]) -> list[float] | list[list[float]]:
    """Encode text into BGE vectors.

    Args:
        text: One text string or a non-empty sequence of text strings.

    Returns:
        A 1024-dimensional vector for a single string, or a list of vectors for
        batch input.

    Raises:
        ValueError: If the input is empty or the output dimension is invalid.
    """
    is_single = isinstance(text, str)
    texts = [text] if is_single else list(text)

    if not texts or any(not item for item in texts):
        raise ValueError("Embedding input text must be non-empty.")

    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    vectors = cast(list[list[float]], embeddings.tolist())
    _validate_vectors(vectors)

    if is_single:
        return vectors[0]
    return vectors


def _validate_vectors(vectors: list[list[float]]) -> None:
    """Validate encoded vector dimensions."""
    for vector in vectors:
        if len(vector) != EMBEDDING_DIMENSION:
            raise ValueError(
                "Embedding vector dimension mismatch: "
                f"expected {EMBEDDING_DIMENSION}, got {len(vector)}"
            )


def _get_model_dimension(model: Any) -> int:
    """Return the embedding dimension across sentence-transformers versions."""
    if hasattr(model, "get_embedding_dimension"):
        return int(model.get_embedding_dimension())
    return int(model.get_sentence_embedding_dimension())
