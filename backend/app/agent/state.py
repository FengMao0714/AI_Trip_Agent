"""Agent state definitions for LangGraph workflows."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state carried through the travel planning agent graph."""

    messages: Annotated[list, add_messages]
    user_profile: dict | None
    itinerary: dict | None
    iteration_count: int
    should_end: bool
