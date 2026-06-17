"""LangGraph state graph construction for the travel planning agent."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, cast

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import SecretStr

from app.agent.llm_http import direct_http_clients
from app.agent.nodes import (
    ChatModel,
    generate_response,
    handle_fallback,
    route_decision,
    run_planner,
    run_tools,
)
from app.agent.state import AgentState
from app.config import get_settings
from app.tools import poi_search, rag_search, route_plan, weather
from app.tools.mcp_client import get_mcp_tools

logger = logging.getLogger(__name__)

CORE_TOOLS = [poi_search, route_plan, weather]
RAG_TOOLS = [rag_search]
FALLBACK_TOOLS = [*CORE_TOOLS, *RAG_TOOLS]


def _dedupe_tools_by_name(tools: Sequence[BaseTool]) -> list[BaseTool]:
    """Keep the first tool for each LangChain tool name."""
    seen_names: set[str] = set()
    deduped: list[BaseTool] = []
    for candidate in tools:
        name = getattr(candidate, "name", "")
        if name in seen_names:
            continue
        seen_names.add(name)
        deduped.append(candidate)
    return deduped


def build_llm() -> ChatOpenAI:
    """Build the OpenAI-compatible chat model from environment settings."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        msg = "DEEPSEEK_API_KEY is not configured"
        raise RuntimeError(msg)

    extra_body: dict[str, Any] = {}
    if not settings.llm_thinking_enabled:
        extra_body["thinking"] = {"type": "disabled"}

    return ChatOpenAI(
        api_key=SecretStr(settings.deepseek_api_key),
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        extra_body=extra_body or None,
        streaming=True,
        stream_usage=True,
        **direct_http_clients(),
    )


async def build_graph(
    *,
    llm: Any | None = None,
    tools: Sequence[BaseTool] | None = None,
    load_mcp_tools: bool = True,
    load_rag_tool: bool = True,
) -> CompiledStateGraph:
    """Build and compile the travel planning Agent state graph."""
    if tools is not None:
        all_tools = list(tools)
    else:
        all_tools = [*CORE_TOOLS, *(RAG_TOOLS if load_rag_tool else [])]
        if load_mcp_tools:
            mcp_tools = await get_mcp_tools()
            all_tools = _dedupe_tools_by_name([*all_tools, *mcp_tools])

    base_llm = llm if llm is not None else build_llm()
    llm_with_tools = base_llm.bind_tools(all_tools) if all_tools else base_llm
    planner_llm = cast(ChatModel, llm_with_tools)

    async def planner_node(state: AgentState) -> dict[str, Any]:
        return await run_planner(state, planner_llm)

    graph = StateGraph(AgentState)
    graph.add_node("planner_node", planner_node)
    graph.add_node("tool_node", run_tools(all_tools))
    graph.add_node("response_node", generate_response)
    graph.add_node("fallback_node", handle_fallback)

    graph.set_entry_point("planner_node")
    graph.add_conditional_edges("planner_node", route_decision)
    graph.add_edge("tool_node", "planner_node")
    graph.add_edge("response_node", END)
    graph.add_edge("fallback_node", "response_node")

    compiled_graph = graph.compile()
    logger.info("Compiled Agent graph with %d tools", len(all_tools))
    return compiled_graph
