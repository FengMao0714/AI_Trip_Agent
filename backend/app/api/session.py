"""Conversation session API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.models.schemas import ClearSessionResponse, SessionMessage, SessionResponse
from app.services.session import clear_session, get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["session"])


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session_endpoint(session_id: str) -> SessionResponse:
    """Return persisted context for a conversation session."""
    try:
        session_data = await get_session(session_id)
    except Exception as exc:
        logger.warning("Failed to read session_id=%s: %s", session_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Session service is temporarily unavailable.",
        ) from exc

    if session_data is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    return _build_session_response(session_id, session_data)


@router.delete("/session/{session_id}", response_model=ClearSessionResponse)
async def clear_session_endpoint(session_id: str) -> ClearSessionResponse:
    """Clear persisted context for a conversation session."""
    try:
        await clear_session(session_id)
    except Exception as exc:
        logger.warning("Failed to clear session_id=%s: %s", session_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Session service is temporarily unavailable.",
        ) from exc

    return ClearSessionResponse(session_id=session_id, cleared=True)


def _build_session_response(
    session_id: str,
    session_data: dict[str, Any],
) -> SessionResponse:
    """Normalize raw Redis session payload into the public response model."""
    messages = [
        SessionMessage(**message)
        for message in session_data.get("messages", [])
        if _is_session_message(message)
    ]

    return SessionResponse(
        session_id=session_id,
        user_profile=_dict_or_none(session_data.get("user_profile")),
        itinerary=_dict_or_none(session_data.get("itinerary")),
        message_count=_int_value(session_data.get("message_count")),
        messages=messages,
        updated_at=_str_or_none(session_data.get("updated_at")),
    )


def _is_session_message(value: Any) -> bool:
    """Return whether a raw value can be parsed as a session message."""
    if not isinstance(value, dict):
        return False
    content = value.get("content")
    return (
        value.get("role") in {"user", "assistant"}
        and isinstance(content, str)
        and bool(content.strip())
    )


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    """Return value if it is a dictionary."""
    return value if isinstance(value, dict) else None


def _str_or_none(value: Any) -> str | None:
    """Return value if it is a string."""
    return value if isinstance(value, str) else None


def _int_value(value: Any) -> int:
    """Convert a value to int, returning 0 on invalid input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
