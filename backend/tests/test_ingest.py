"""RAG ingestion helper tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.rag import ingest


def make_record(title: str = "故宫博物院") -> ingest.KnowledgeRecord:
    """Build a valid raw knowledge record."""
    return ingest.KnowledgeRecord(
        city="北京",
        category="景点",
        title=title,
        content=f"{title}适合历史文化主题旅行。",
        metadata={
            "address": "北京市东城区景山前街4号",
            "lng": 116.397,
            "lat": 39.918,
            "rating": 4.8,
            "price_range": "60元起",
            "opening_hours": "08:30-17:00",
            "tags": ["历史", "世界遗产"],
        },
    )


def test_resolve_data_files_supports_city_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """City aliases resolve to the expected JSON file."""
    data_file = tmp_path / "beijing.json"
    data_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(ingest, "DATA_DIR", tmp_path)

    assert ingest.resolve_data_files("北京") == [data_file]
    assert ingest.resolve_data_files("beijing") == [data_file]


def test_load_records_validates_json_file(tmp_path: Path) -> None:
    """Valid JSON data is loaded into typed records."""
    path = tmp_path / "beijing.json"
    record = make_record()
    path.write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")

    records = ingest.load_records([path])

    assert records == [record]


def test_load_records_rejects_missing_metadata(tmp_path: Path) -> None:
    """Invalid source records fail before ingestion."""
    path = tmp_path / "bad.json"
    record = make_record()
    del record["metadata"]["tags"]
    path.write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="metadata missing fields"):
        ingest.load_records([path])


def test_iter_batches_splits_records() -> None:
    """Records are grouped by the requested batch size."""
    records = [make_record(str(index)) for index in range(5)]

    batches = list(ingest.iter_batches(records, batch_size=2))

    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_build_embedding_text_uses_title_and_content() -> None:
    """Embedding input contains both title and detailed content."""
    record = make_record("天坛公园")

    assert ingest.build_embedding_text(record) == (
        "天坛公园\n天坛公园适合历史文化主题旅行。"
    )


@pytest.mark.asyncio
async def test_insert_records_embeds_and_commits_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Insertion embeds title/content text and commits each batch."""
    records = [make_record("故宫博物院"), make_record("天坛公园")]
    encoded_texts: list[list[str]] = []

    def fake_encode(texts: list[str]) -> list[list[float]]:
        encoded_texts.append(texts)
        return [[0.1] * 1024 for _ in texts]

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[Any] = []
            self.commit_count = 0

        def add_all(self, chunks: list[Any]) -> None:
            self.added.extend(chunks)

        async def commit(self) -> None:
            self.commit_count += 1

    session = FakeSession()
    monkeypatch.setattr(ingest, "encode", fake_encode)

    inserted = await ingest.insert_records(session, records, batch_size=1)  # type: ignore[arg-type]

    assert inserted == 2
    assert session.commit_count == 2
    assert [chunk.title for chunk in session.added] == ["故宫博物院", "天坛公园"]
    assert session.added[0].metadata_["address"] == "北京市东城区景山前街4号"
    assert encoded_texts == [
        ["故宫博物院\n故宫博物院适合历史文化主题旅行。"],
        ["天坛公园\n天坛公园适合历史文化主题旅行。"],
    ]
