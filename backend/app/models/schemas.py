"""Pydantic request and response models."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Overall service status.")
    services: dict[str, str] = Field(description="Per-service health states.")


class ChatRequest(BaseModel):
    """Chat request body."""

    message: NonBlankString = Field(
        ...,
        description="User message to send to the travel planning agent.",
    )
    session_id: NonBlankString = Field(
        ...,
        description="Conversation session identifier.",
    )
    current_itinerary: dict[str, Any] | None = Field(
        default=None,
        description="Current frontend itinerary used for follow-up edits.",
    )


class SessionMessage(BaseModel):
    """One persisted conversation message."""

    role: Literal["user", "assistant"] = Field(
        description="Conversation role for the persisted message.",
    )
    content: str = Field(
        min_length=1,
        description="Plain text message content.",
    )
    created_at: str | None = Field(
        default=None,
        description="ISO timestamp when the message was recorded.",
    )


class SessionResponse(BaseModel):
    """Conversation session context response."""

    session_id: str = Field(description="Conversation session identifier.")
    user_profile: dict[str, Any] | None = Field(
        default=None,
        description="Extracted user profile for this session.",
    )
    itinerary: dict[str, Any] | None = Field(
        default=None,
        description="Latest itinerary stored for this session.",
    )
    message_count: int = Field(
        default=0,
        ge=0,
        description="Number of user turns handled in this session.",
    )
    messages: list[SessionMessage] = Field(
        default_factory=list,
        description="Recent conversation messages retained for context.",
    )
    updated_at: str | None = Field(
        default=None,
        description="ISO timestamp for the last session update.",
    )


class ClearSessionResponse(BaseModel):
    """Response returned after clearing a session."""

    session_id: str = Field(description="Conversation session identifier.")
    cleared: bool = Field(description="Whether the clear operation completed.")
