"""Redis-backed conversation session management."""

from __future__ import annotations

from typing import Any

from app.services.cache import delete_cache, get_cache, set_cache

SESSION_TTL_SECONDS = 7 * 24 * 60 * 60


def session_key(session_id: str) -> str:
    """Build the Redis key for a conversation session."""
    return f"session:{session_id}"


async def get_session(session_id: str) -> dict[str, Any] | None:
    """Read session data from Redis."""
    value = await get_cache(session_key(session_id))
    return value if isinstance(value, dict) else None


async def save_session(session_id: str, data: dict[str, Any]) -> None:
    """Save session data to Redis with the standard 7 day TTL."""
    await set_cache(session_key(session_id), data, SESSION_TTL_SECONDS)


async def clear_session(session_id: str) -> None:
    """Delete session data from Redis."""
    await delete_cache(session_key(session_id))
