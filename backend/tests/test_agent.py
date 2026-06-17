"""Agent graph skeleton tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent import graph as graph_module
from app.agent.graph import build_graph
from app.agent.nodes import (
    MAX_ITERATIONS,
    _extract_days,
    _extract_destination,
    generate_response,
    handle_fallback,
    route_decision,
    run_planner,
)
from app.agent.state import AgentState


class FakeChatModel:
    """Minimal async chat model for graph tests."""

    def __init__(self) -> None:
        self.bound_tools: list[Any] = []

    def bind_tools(self, tools: list[Any]) -> FakeChatModel:
        """Return self to mimic LangChain chat model tool binding."""
        self.bound_tools = list(tools)
        return self

    async def ainvoke(self, messages: Any) -> AIMessage:
        """Return a deterministic planner response."""
        return AIMessage(content="北京3天行程可以从故宫、长城、颐和园开始规划。")


def _state(iteration_count: int = 0) -> AgentState:
    return {
        "messages": [HumanMessage(content="我想去北京玩3天")],
        "user_profile": None,
        "itinerary": None,
        "iteration_count": iteration_count,
        "should_end": False,
    }


@pytest.mark.asyncio
async def test_build_graph_runs_planner_to_response() -> None:
    graph = await build_graph(
        llm=FakeChatModel(),
        tools=[],
        load_mcp_tools=False,
    )

    events: list[dict[str, Any]] = []
    async for event in graph.astream(_state()):
        events.append(event)

    assert "planner_node" in events[0]
    assert events[0]["planner_node"]["iteration_count"] == 1
    assert "response_node" in events[1]
    assert events[1]["response_node"]["should_end"] is True


@pytest.mark.asyncio
async def test_build_graph_routes_iteration_limit_to_fallback() -> None:
    graph = await build_graph(
        llm=FakeChatModel(),
        tools=[],
        load_mcp_tools=False,
    )

    events: list[dict[str, Any]] = []
    async for event in graph.astream(_state(MAX_ITERATIONS)):
        events.append(event)

    assert "planner_node" in events[0]
    assert "fallback_node" in events[1]
    assert events[1]["fallback_node"]["should_end"] is True
    assert "response_node" in events[2]


def test_route_decision_sends_iteration_limit_to_fallback() -> None:
    assert route_decision(_state(MAX_ITERATIONS)) == "fallback_node"


def test_route_decision_sends_tool_calls_to_tool_node() -> None:
    state = _state()
    state["messages"] = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "poi_search",
                    "args": {"city": "Beijing", "keyword": "museum"},
                    "id": "call-1",
                }
            ],
        )
    ]

    assert route_decision(state) == "tool_node"


def test_route_decision_sends_regular_messages_to_response_node() -> None:
    state = _state()
    state["messages"] = [AIMessage(content="ready")]

    assert route_decision(state) == "response_node"


def test_route_decision_sends_empty_messages_to_response_node() -> None:
    state = _state()
    state["messages"] = []

    assert route_decision(state) == "response_node"


def test_extract_destination_ignores_leading_intent_words() -> None:
    assert _extract_destination("我想去北京玩3天") == "北京"
    assert _extract_destination("我和对象周末去贵阳玩2天, 从西安出发") == "贵阳"
    assert _extract_destination("我和对象打算下周去广州玩一个周") == "广州"


def test_extract_days_treats_one_week_as_seven_days() -> None:
    assert _extract_days("下周去广州玩一个周") == 7


def test_build_llm_disables_thinking_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALL_PROXY", raising=False)
    monkeypatch.delenv("all_proxy", raising=False)
    monkeypatch.setattr(
        graph_module,
        "get_settings",
        lambda: SimpleNamespace(
            deepseek_api_key="test-key",
            deepseek_base_url="https://example.test/v1",
            deepseek_model="mimo-v2.5-pro",
            llm_thinking_enabled=False,
        ),
    )

    llm = graph_module.build_llm()

    assert llm.extra_body == {"thinking": {"type": "disabled"}}


@pytest.mark.asyncio
async def test_build_graph_uses_fallback_tools_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_mcp_tools() -> list[Any]:
        return []

    monkeypatch.setattr(graph_module, "get_mcp_tools", fake_get_mcp_tools)

    llm = FakeChatModel()
    graph = await build_graph(llm=llm)

    assert graph is not None
    assert {tool.name for tool in llm.bound_tools} >= {
        "poi_search",
        "route_plan",
        "weather",
        "rag_search",
    }


@pytest.mark.asyncio
async def test_build_graph_can_disable_rag_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_mcp_tools() -> list[Any]:
        return []

    monkeypatch.setattr(graph_module, "get_mcp_tools", fake_get_mcp_tools)

    llm = FakeChatModel()
    graph = await build_graph(llm=llm, load_rag_tool=False)

    assert graph is not None
    assert {tool.name for tool in llm.bound_tools} >= {
        "poi_search",
        "route_plan",
        "weather",
    }
    assert "rag_search" not in {tool.name for tool in llm.bound_tools}


@pytest.mark.asyncio
async def test_run_planner_error_returns_fallback_patch() -> None:
    class FailingChatModel:
        async def ainvoke(self, messages: Any) -> AIMessage:
            raise RuntimeError("boom")

    result = await run_planner(_state(), FailingChatModel())

    assert result["should_end"] is True
    assert isinstance(result["messages"][0], AIMessage)


@pytest.mark.asyncio
async def test_run_planner_reraises_llm_service_error() -> None:
    class AuthenticationLikeError(Exception):
        status_code = 401

    class FailingChatModel:
        async def ainvoke(self, messages: Any) -> AIMessage:
            raise AuthenticationLikeError("Error code: 401 - api key invalid")

    with pytest.raises(AuthenticationLikeError):
        await run_planner(_state(), FailingChatModel())


@pytest.mark.asyncio
async def test_generate_response_empty_messages_returns_error_message() -> None:
    state = _state()
    state["messages"] = []

    result = await generate_response(state)

    assert result["should_end"] is True
    assert isinstance(result["messages"][0], AIMessage)


@pytest.mark.asyncio
async def test_handle_fallback_marks_state_done() -> None:
    result = await handle_fallback(_state(MAX_ITERATIONS))

    assert result["should_end"] is True
    assert isinstance(result["messages"][0], AIMessage)
    assert "当前规划步骤较多" not in result["messages"][0].content
    assert "<itinerary_json>" not in result["messages"][0].content
    assert "北京" in result["messages"][0].content


@pytest.mark.asyncio
async def test_handle_fallback_builds_stage_result_from_user_constraints() -> None:
    state = _state(MAX_ITERATIONS)
    state["messages"] = [
        HumanMessage(content="贵州情侣国庆行程, 预算10000, 西安出发。")
    ]

    result = await handle_fallback(state)
    content = result["messages"][0].content

    assert "贵州" in content
    assert "<itinerary_json>" not in content
    assert "没有拿到足够可靠" in content


@pytest.mark.asyncio
async def test_handle_fallback_preserves_regional_destination_and_days() -> None:
    state = _state(MAX_ITERATIONS)
    state["messages"] = [
        HumanMessage(
            content="7月份川西5天旅游行程, 我们两个人是情侣, 预算8000, 没有忌口。"
        )
    ]

    result = await handle_fallback(state)
    content = result["messages"][0].content

    assert "川西" in content
    assert "<itinerary_json>" not in content
    assert "新都桥" not in content
