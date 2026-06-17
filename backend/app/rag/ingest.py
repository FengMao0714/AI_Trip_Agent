"""Ingest tourism knowledge JSON files into the pgvector knowledge table."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, TypedDict

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import connection
from app.models.db_models import KnowledgeChunk
from app.rag.embeddings import encode

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
BATCH_SIZE = 50

CITY_FILE_ALIASES = {
    "beijing": "beijing.json",
    "北京": "beijing.json",
    "shanghai": "shanghai.json",
    "上海": "shanghai.json",
    "chengdu": "chengdu.json",
    "成都": "chengdu.json",
    "guiyang": "guiyang.json",
    "贵阳": "guiyang.json",
}

REQUIRED_FIELDS = {"city", "category", "title", "content", "metadata"}
REQUIRED_METADATA_FIELDS = {
    "address",
    "lng",
    "lat",
    "rating",
    "price_range",
    "opening_hours",
    "tags",
}


class KnowledgeRecord(TypedDict):
    """Raw knowledge record loaded from backend/data JSON files."""

    city: str
    category: str
    title: str
    content: str
    metadata: dict[str, Any]


class IngestStats(TypedDict):
    """Ingestion result counters."""

    loaded: int
    skipped: int
    inserted: int
    duration: float


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--city",
        choices=sorted(CITY_FILE_ALIASES),
        help="Only ingest one city, e.g. beijing, shanghai, chengdu, guiyang.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    """Configure console logging for CLI execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def resolve_data_files(city: str | None = None) -> list[Path]:
    """Resolve JSON files to ingest.

    Args:
        city: Optional city alias or Chinese city name.

    Returns:
        Ordered list of data file paths.

    Raises:
        FileNotFoundError: If a required data file does not exist.
    """
    if city:
        filenames = [CITY_FILE_ALIASES[city]]
    else:
        filenames = list(dict.fromkeys(CITY_FILE_ALIASES.values()))

    files = [DATA_DIR / filename for filename in filenames]
    missing_files = [path for path in files if not path.exists()]
    if missing_files:
        missing = ", ".join(str(path) for path in missing_files)
        raise FileNotFoundError(f"RAG data file not found: {missing}")
    return files


def load_records(files: Sequence[Path]) -> list[KnowledgeRecord]:
    """Load and validate knowledge records from JSON files.

    Args:
        files: JSON data files under backend/data.

    Returns:
        Validated raw knowledge records.
    """
    records: list[KnowledgeRecord] = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a JSON array.")

        for index, item in enumerate(data, start=1):
            records.append(_validate_record(path, index, item))

        logger.info(
            "Loaded RAG data file", extra={"file": str(path), "count": len(data)}
        )

    return records


async def ingest(city: str | None = None) -> IngestStats:
    """Ingest RAG data into the knowledge_chunks table.

    Args:
        city: Optional city alias or Chinese city name.

    Returns:
        Ingestion counters and duration.
    """
    start_time = time.perf_counter()
    files = resolve_data_files(city)
    records = load_records(files)

    if connection.async_session_factory is None:
        await connection.init_db()

    if connection.async_session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")

    async with connection.async_session_factory() as session:
        new_records, skipped_count = await filter_existing_records(session, records)
        inserted_count = await insert_records(session, new_records)

    duration = round(time.perf_counter() - start_time, 3)
    stats: IngestStats = {
        "loaded": len(records),
        "skipped": skipped_count,
        "inserted": inserted_count,
        "duration": duration,
    }
    logger.info("RAG ingest completed", extra=stats)
    return stats


async def filter_existing_records(
    session: AsyncSession,
    records: Sequence[KnowledgeRecord],
) -> tuple[list[KnowledgeRecord], int]:
    """Remove records that already exist in the database.

    Duplicate identity is city + category + title, matching one JSON chunk per
    place or rule.
    """
    keys = {(record["city"], record["category"], record["title"]) for record in records}
    if not keys:
        return [], 0

    result = await session.execute(
        select(
            KnowledgeChunk.city, KnowledgeChunk.category, KnowledgeChunk.title
        ).where(
            tuple_(
                KnowledgeChunk.city,
                KnowledgeChunk.category,
                KnowledgeChunk.title,
            ).in_(keys)
        )
    )
    existing_keys = set(result.all())
    seen_source_keys: set[tuple[str, str, str]] = set()
    new_records: list[KnowledgeRecord] = []

    for record in records:
        key = (record["city"], record["category"], record["title"])
        if key in existing_keys or key in seen_source_keys:
            continue

        seen_source_keys.add(key)
        new_records.append(record)

    return new_records, len(records) - len(new_records)


async def insert_records(
    session: AsyncSession,
    records: Sequence[KnowledgeRecord],
    batch_size: int = BATCH_SIZE,
) -> int:
    """Embed and insert records in batches.

    Args:
        session: Active async database session.
        records: Records not yet present in the database.
        batch_size: Insert batch size.

    Returns:
        Number of inserted records.
    """
    inserted_count = 0
    total = len(records)

    for batch_index, batch in enumerate(iter_batches(records, batch_size), start=1):
        texts = [build_embedding_text(record) for record in batch]
        embeddings = encode(texts)
        chunks = [
            KnowledgeChunk(
                city=record["city"],
                category=record["category"],
                title=record["title"],
                content=record["content"],
                embedding=embedding,
                metadata_=record["metadata"],
            )
            for record, embedding in zip(batch, embeddings, strict=True)
        ]
        session.add_all(chunks)
        await session.commit()

        inserted_count += len(chunks)
        logger.info(
            "Inserted RAG batch",
            extra={
                "batch": batch_index,
                "batch_size": len(chunks),
                "inserted": inserted_count,
                "total": total,
            },
        )

    return inserted_count


def build_embedding_text(record: KnowledgeRecord) -> str:
    """Build the text sent to the embedding model."""
    return f"{record['title']}\n{record['content']}"


def iter_batches(
    records: Sequence[KnowledgeRecord],
    batch_size: int,
) -> Iterable[list[KnowledgeRecord]]:
    """Yield records in fixed-size batches."""
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0.")

    for start in range(0, len(records), batch_size):
        yield list(records[start : start + batch_size])


def _validate_record(path: Path, index: int, item: Any) -> KnowledgeRecord:
    """Validate one JSON record."""
    if not isinstance(item, dict):
        raise ValueError(f"{path}:{index} must be an object.")

    missing_fields = REQUIRED_FIELDS - item.keys()
    if missing_fields:
        raise ValueError(f"{path}:{index} missing fields: {sorted(missing_fields)}")

    metadata = item["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}:{index} metadata must be an object.")

    missing_metadata = REQUIRED_METADATA_FIELDS - metadata.keys()
    if missing_metadata:
        raise ValueError(
            f"{path}:{index} metadata missing fields: {sorted(missing_metadata)}"
        )

    for field in ("city", "category", "title", "content"):
        if not isinstance(item[field], str) or not item[field].strip():
            raise ValueError(
                f"{path}:{index} field {field} must be a non-empty string."
            )

    if not isinstance(metadata["tags"], list) or not metadata["tags"]:
        raise ValueError(f"{path}:{index} metadata.tags must be a non-empty list.")

    for field in ("lng", "lat", "rating"):
        if not isinstance(metadata[field], int | float):
            raise ValueError(f"{path}:{index} metadata.{field} must be numeric.")

    return KnowledgeRecord(
        city=item["city"],
        category=item["category"],
        title=item["title"],
        content=item["content"],
        metadata=metadata,
    )


async def async_main() -> None:
    """Run ingest from the command line."""
    configure_logging()
    args = parse_args()

    try:
        stats = await ingest(args.city)
        logger.info(
            "RAG ingest summary: loaded=%d skipped=%d inserted=%d duration=%.3fs",
            stats["loaded"],
            stats["skipped"],
            stats["inserted"],
            stats["duration"],
        )
    finally:
        await connection.close_db()


def main() -> None:
    """CLI entrypoint."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
