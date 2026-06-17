"""Embedding helper tests."""

from __future__ import annotations

import pytest

from app.rag import embeddings


class FakeArray:
    """Small stand-in for a numpy array returned by sentence-transformers."""

    def __init__(self, values: list[list[float]]) -> None:
        self.values = values

    def tolist(self) -> list[list[float]]:
        """Return plain Python vectors."""
        return self.values


class FakeEmbeddingModel:
    """Fake embedding model with deterministic vectors."""

    def __init__(self, dimension: int = embeddings.EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension
        self.calls: list[list[str]] = []

    def encode(
        self,
        texts: list[str],
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> FakeArray:
        """Match the sentence-transformers encode API used by the app."""
        assert convert_to_numpy is True
        assert normalize_embeddings is True
        assert show_progress_bar is False
        self.calls.append(texts)
        return FakeArray([[0.1] * self.dimension for _ in texts])


def test_encode_single_text_returns_1024_dimension_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single text input returns one vector."""
    model = FakeEmbeddingModel()
    monkeypatch.setattr(embeddings, "_embedding_model", model)

    vector = embeddings.encode("北京故宫")

    assert len(vector) == embeddings.EMBEDDING_DIMENSION
    assert model.calls == [["北京故宫"]]


def test_encode_batch_returns_vector_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Batch input returns one vector per text."""
    model = FakeEmbeddingModel()
    monkeypatch.setattr(embeddings, "_embedding_model", model)

    vectors = embeddings.encode(["北京故宫", "上海外滩"])

    assert len(vectors) == 2
    assert all(len(vector) == embeddings.EMBEDDING_DIMENSION for vector in vectors)
    assert model.calls == [["北京故宫", "上海外滩"]]


def test_encode_rejects_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty text input is rejected before model execution."""
    model = FakeEmbeddingModel()
    monkeypatch.setattr(embeddings, "_embedding_model", model)

    with pytest.raises(ValueError, match="non-empty"):
        embeddings.encode("")

    assert model.calls == []


def test_encode_rejects_wrong_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected model output dimensions fail fast."""
    model = FakeEmbeddingModel(dimension=3)
    monkeypatch.setattr(embeddings, "_embedding_model", model)

    with pytest.raises(ValueError, match="dimension mismatch"):
        embeddings.encode("北京故宫")
