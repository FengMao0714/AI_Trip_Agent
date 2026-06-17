# ruff: noqa: RUF001
"""Chat API tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.intent import build_heuristic_travel_intent
from app.api import chat
from app.api import health as health_module
from app.api import session as session_module
from app.api.router import api_router
from app.main import app as main_app


class FakeGraph:
    """Fake compiled graph for SSE tests."""

    async def astream(self, state: dict[str, Any], config: dict[str, Any]):
        """Yield a minimal planner update."""
        assert "用户画像" in state["messages"][0].content
        assert "北京" in state["messages"][1].content
        assert "3天" in state["messages"][1].content
        assert state["user_profile"]["destination"] == "北京"
        assert state["user_profile"]["intent"]["days"] == 3
        assert config["metadata"]["session_id"] == "session-1"
        yield {
            "planner_node": {
                "messages": [AIMessage(content="北京3天行程建议。")],
                "iteration_count": 1,
            }
        }
        yield {"response_node": {"should_end": True}}


class HistoryGraph:
    """Fake graph that verifies persisted history is injected."""

    async def astream(self, state: dict[str, Any], config: dict[str, Any]):
        """Assert history order before returning a response."""
        assert state["messages"][1].content == "上一轮用户问题"
        assert state["messages"][2].content == "上一轮助手回答"
        assert state["messages"][3].content == "继续帮我调整"
        yield {
            "planner_node": {
                "messages": [AIMessage(content="已结合上一轮上下文继续调整。")],
                "iteration_count": 1,
            }
        }


class NoItineraryGraph:
    """Fake graph that completes without returning a structured itinerary."""

    async def astream(self, state: dict[str, Any], config: dict[str, Any]):
        """Yield a planner failure message without an itinerary event."""
        yield {
            "planner_node": {
                "messages": [
                    AIMessage(content="抱歉, 规划过程中遇到了问题, 请稍后重试。")
                ],
                "iteration_count": 1,
            }
        }


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(chat.router)
    return TestClient(app)


def _api_client() -> TestClient:
    app = FastAPI()
    app.include_router(api_router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _use_heuristic_intent_extraction(monkeypatch) -> None:
    async def fake_extract_travel_intent(message: str, previous_intent=None):
        return build_heuristic_travel_intent(message, previous_intent)

    monkeypatch.setattr(chat, "extract_travel_intent", fake_extract_travel_intent)


def test_health_endpoint_returns_service_status(monkeypatch) -> None:
    async def fake_database_status(settings: object) -> str:
        return "connected"

    async def fake_redis_status() -> str:
        return "connected"

    monkeypatch.setattr(health_module, "_database_status", fake_database_status)
    monkeypatch.setattr(health_module, "_redis_status", fake_redis_status)

    response = _api_client().get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["services"]["database"] == "connected"
    assert response.json()["services"]["redis"] == "connected"
    assert set(response.json()["services"]) == {"database", "redis", "llm"}


def test_get_session_endpoint_returns_context(monkeypatch) -> None:
    async def fake_get_session(session_id: str) -> dict[str, Any]:
        assert session_id == "session-1"
        return {
            "user_profile": {"destination": "北京"},
            "itinerary": {"days": []},
            "message_count": 2,
            "messages": [
                {
                    "role": "user",
                    "content": "上一轮用户问题",
                    "created_at": "2026-05-09T00:00:00+00:00",
                },
                {
                    "role": "assistant",
                    "content": "上一轮助手回答",
                    "created_at": "2026-05-09T00:00:01+00:00",
                },
            ],
            "updated_at": "2026-05-09T00:00:02+00:00",
        }

    monkeypatch.setattr(session_module, "get_session", fake_get_session)

    response = _api_client().get("/api/v1/session/session-1")

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-1"
    assert response.json()["user_profile"] == {"destination": "北京"}
    assert response.json()["itinerary"] == {"days": []}
    assert response.json()["message_count"] == 2
    assert response.json()["messages"][0]["role"] == "user"


def test_get_session_endpoint_returns_404(monkeypatch) -> None:
    async def fake_get_session(session_id: str) -> None:
        return None

    monkeypatch.setattr(session_module, "get_session", fake_get_session)

    response = _api_client().get("/api/v1/session/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found."


def test_clear_session_endpoint_deletes_context(monkeypatch) -> None:
    cleared: list[str] = []

    async def fake_clear_session(session_id: str) -> None:
        cleared.append(session_id)

    monkeypatch.setattr(session_module, "clear_session", fake_clear_session)

    response = _api_client().delete("/api/v1/session/session-1")

    assert response.status_code == 200
    assert response.json() == {"session_id": "session-1", "cleared": True}
    assert cleared == ["session-1"]


def test_format_graph_event_maps_tool_events() -> None:
    events = chat.format_graph_event(
        {
            "planner_node": {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "poi_search",
                                "args": {"city": "北京", "keyword": "故宫"},
                                "id": "call-1",
                            }
                        ],
                    )
                ]
            },
            "tool_node": {
                "messages": [
                    ToolMessage(
                        content='{"name": "故宫博物院"}',
                        name="poi_search",
                        tool_call_id="call-1",
                    )
                ]
            },
        }
    )

    assert ("thinking", {"step": "正在分析您的需求..."}) in events
    assert (
        "tool_call",
        {"tool": "poi_search", "args": {"city": "北京", "keyword": "故宫"}},
    ) in events
    assert (
        "tool_result",
        {"tool": "poi_search", "result": '{"name": "故宫博物院"}'},
    ) in events


def test_split_content_strips_invalid_itinerary_tag() -> None:
    content, itinerary = chat._split_content_and_itinerary(
        "规划说明\n<itinerary_json>{bad json}</itinerary_json>"
    )

    assert content == "规划说明"
    assert itinerary is None


def test_split_content_downgrades_uncovered_rag_source() -> None:
    content, itinerary = chat._split_content_and_itinerary(
        """
        规划说明
        <itinerary_json>{
          "destination": "陕西",
          "days": [{
            "day": 1,
            "date": "第 1 天",
            "activities": [{
              "time_slot": "18:30-19:30",
              "place_name": "袁家村民宿/酒店",
              "place_type": "住宿",
              "lng": 108.4,
              "lat": 34.6,
              "description": "住在村内。",
              "cost": 300,
              "source": "RAG推荐",
              "source_refs": ["rag_search:陕西特色美食推荐"]
            }]
          }],
          "total_cost": 300
        }</itinerary_json>
        """
    )

    assert content == "规划说明"
    assert itinerary is not None
    activity = itinerary["days"][0]["activities"][0]
    assert activity["source"] == "来源待确认"
    assert activity["is_verified"] is False
    assert "知识库未覆盖" in activity["warnings"]


def test_inline_itinerary_downgrades_uncovered_rag_source() -> None:
    content, itinerary = chat._split_content_and_itinerary(
        """
        下面是行程:
        {
          "destination": "陕西",
          "days": [{
            "day": 1,
            "activities": [{
              "time_slot": "09:00-10:00",
              "place_name": "袁家村",
              "source": "rag_search",
              "source_refs": ["rag_search:陕西特色古镇"]
            }]
          }]
        }
        """
    )

    assert "下面是行程" in content
    assert itinerary is not None
    activity = itinerary["days"][0]["activities"][0]
    assert activity["source"] == "来源待确认"
    assert activity["is_verified"] is False
    assert "知识库未覆盖" in activity["warnings"]


def test_sanitize_keeps_local_knowledge_refs_for_covered_destination() -> None:
    itinerary = {
        "destination": "贵阳",
        "days": [
            {
                "day": 1,
                "activities": [
                    {
                        "place_name": "老凯俚酸汤鱼",
                        "source": "来源待确认",
                        "source_refs": ["本地知识库检索: 老凯俚酸汤鱼"],
                        "warnings": ["营业时间待确认", "知识库未覆盖"],
                    },
                    {
                        "place_name": "二七路小吃街",
                        "source": "来源待确认",
                        "source_refs": ["二七路小吃街"],
                        "warnings": ["人均30-80元", "知识库未覆盖"],
                    },
                ],
            }
        ],
    }

    sanitized = chat._sanitize_itinerary_confidence(itinerary)

    assert sanitized is itinerary
    activity = sanitized["days"][0]["activities"][0]
    assert activity["source"] == "来源待确认"
    assert activity["warnings"] == ["营业时间待确认"]
    plain_ref_activity = sanitized["days"][0]["activities"][1]
    assert plain_ref_activity["warnings"] == ["人均30-80元"]


def test_chat_endpoint_streams_content(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []

    async def fake_build_graph(**kwargs: Any) -> FakeGraph:
        assert kwargs == {"load_mcp_tools": False, "load_rag_tool": True}
        return FakeGraph()

    async def fake_get_session(session_id: str) -> dict[str, Any]:
        assert session_id == "session-1"
        return {
            "user_profile": {"destination": "北京"},
            "itinerary": {"days": []},
            "message_count": 2,
        }

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    async def fake_rate_limit(session_id: str) -> None:
        return None

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", fake_get_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", fake_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "我从上海出发, 两个人去北京玩3天, 预算5000",
            "session_id": "session-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert "event: thinking" in response.text
    assert "event: source" in response.text
    assert '"kind": "agent_graph"' in response.text
    assert 'data: {"text": "北京3天行程建议。"}' in response.text
    assert response.text.rstrip().endswith("event: done\ndata: {}")
    assert saved_sessions[0][0] == "session-1"
    assert saved_sessions[0][1]["message_count"] == 3
    assert saved_sessions[0][1]["itinerary"]["generation_source"]["kind"] == (
        "agent_graph"
    )
    assert (
        saved_sessions[0][1]["messages"][-2]["content"]
        == "我从上海出发, 两个人去北京玩3天, 预算5000"
    )
    assert saved_sessions[0][1]["messages"][-1]["content"] == "北京3天行程建议。"


def test_chat_endpoint_complete_natural_language_enters_planning(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []
    captured_state: dict[str, Any] | None = None

    class CapturingGraph:
        async def astream(self, state: dict[str, Any], config: dict[str, Any]):
            nonlocal captured_state
            captured_state = state
            yield {
                "planner_node": {
                    "messages": [AIMessage(content="成都三天行程建议。")],
                    "iteration_count": 1,
                }
            }

    async def fake_build_graph(**kwargs: Any) -> CapturingGraph:
        assert kwargs == {"load_mcp_tools": False, "load_rag_tool": True}
        return CapturingGraph()

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_demo_fallback_enabled", lambda: False)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "我想去成都玩三天, 预算3000, 两个人, 从广州出发。",
            "session_id": "session-complete-natural",
        },
    )

    assert response.status_code == 200
    assert '"kind": "agent_graph"' in response.text
    assert "成都三天行程建议" in response.text
    assert captured_state is not None
    profile = captured_state["user_profile"]
    assert profile["travel_state"]["stage"] == "planning"
    assert profile["travel_state"]["intent"]["destination"] == "成都"
    assert profile["travel_state"]["intent"]["departure_city"] == "广州"
    assert profile["travel_state"]["intent"]["days"] == 3
    assert profile["travel_state"]["intent"]["people"] == 2
    assert profile["travel_state"]["intent"]["budget"] == 3000
    assert saved_sessions[0][1]["user_profile"]["travel_state"]["stage"] == (
        "ready_to_plan"
    )


def test_chat_endpoint_injects_persisted_history(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []

    async def fake_build_graph(**kwargs: Any) -> HistoryGraph:
        assert kwargs == {"load_mcp_tools": False, "load_rag_tool": False}
        return HistoryGraph()

    async def fake_get_session(session_id: str) -> dict[str, Any]:
        assert session_id == "session-1"
        return {
            "user_profile": {
                "travel_state": {
                    "raw_messages": ["我从上海出发, 两个人去广州玩3天, 预算5000"],
                    "intent": {
                        "destination": "广州",
                        "departure_city": "上海",
                        "days": 3,
                        "people": 2,
                        "budget": 5000,
                        "missing_fields": [],
                    },
                    "confirmed": True,
                    "stage": "ready_to_plan",
                }
            },
            "message_count": 1,
            "messages": [
                {"role": "user", "content": "上一轮用户问题"},
                {"role": "assistant", "content": "上一轮助手回答"},
            ],
        }

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", fake_get_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_demo_fallback_enabled", lambda: False)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={"message": "继续帮我调整", "session_id": "session-1"},
    )

    assert response.status_code == 200
    assert "已结合上一轮上下文继续调整。" in response.text
    assert [message["content"] for message in saved_sessions[0][1]["messages"]] == [
        "上一轮用户问题",
        "上一轮助手回答",
        "继续帮我调整",
        "已结合上一轮上下文继续调整。",
    ]


def test_chat_endpoint_clarifies_missing_days_before_agent(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []

    async def fail_build_graph(**kwargs: Any) -> FakeGraph:
        raise AssertionError("Agent graph should not run before days are provided")

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fail_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "帮我规划我和对象国庆去贵州的行程, 喜欢山水。预算10000, 没有忌口, 从西安出发。",
            "session_id": "session-clarify",
        },
    )

    assert response.status_code == 200
    assert "贵州" in response.text
    assert "计划玩几天" in response.text
    assert "event: itinerary" not in response.text
    assert saved_sessions[0][1]["message_count"] == 1
    assert "计划玩几天" in saved_sessions[0][1]["messages"][-1]["content"]


def test_chat_endpoint_persists_travel_state_for_requirement_collection(
    monkeypatch,
) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []

    async def fail_build_graph(**kwargs: Any) -> FakeGraph:
        raise AssertionError("Agent graph should wait for validated requirements")

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fail_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "我想和女朋友毕业后去云南玩几天, 别太累, 预算一般",
            "session_id": "session-travel-state",
        },
    )

    assert response.status_code == 200
    assert "计划玩几天" in response.text
    assert "总预算大概多少" in response.text
    assert "情侣出行" in response.text
    user_profile = saved_sessions[0][1]["user_profile"]
    travel_state = user_profile["travel_state"]
    assert travel_state["raw_messages"] == [
        "我想和女朋友毕业后去云南玩几天, 别太累, 预算一般"
    ]
    assert travel_state["stage"] == "collecting_info"
    assert travel_state["confirmed"] is False
    assert travel_state["intent"]["destination"] == "云南"
    assert travel_state["intent"]["people"] == 2
    assert travel_state["intent"]["missing_fields"] == [
        "days",
        "budget",
    ]


def test_one_week_trip_duration_is_complete() -> None:
    message = (
        "我和对象打算下周去广州玩一个周, 从西安出发, "
        "最后回到西安, 没有忌口, 喜欢自然风光, 预算10000。"
    )

    assert chat._build_clarification_message(message, None) is None


def test_knowledge_base_strategy_uses_destination_not_departure() -> None:
    assert (
        chat._request_knowledge_base_covered(
            "我从西安出发去贵州玩5天, 喜欢自然风光", None, None
        )
        is True
    )
    assert (
        chat._request_knowledge_base_covered(
            "我从西安出发去广州玩5天, 喜欢自然风光", None, None
        )
        is False
    )
    assert chat._request_knowledge_base_covered("7天", {"destination": "成都"}, None)
    assert (
        chat._request_knowledge_base_covered("7天", {"destination": "广州"}, None)
        is False
    )
    assert (
        chat._request_knowledge_base_covered(
            "改成广州5天自然风光路线",
            {"destination": "成都"},
            {"destination": "北京", "days": []},
        )
        is False
    )
    assert (
        chat._request_knowledge_base_covered(
            "改成贵州5天自然风光路线",
            {"destination": "广州"},
            {"destination": "广州", "days": []},
        )
        is True
    )


def test_chat_endpoint_resumes_day_clarification_with_previous_request(
    monkeypatch,
) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []
    captured_state: dict[str, Any] | None = None

    class CapturingNoItineraryGraph:
        async def astream(self, state: dict[str, Any], config: dict[str, Any]):
            nonlocal captured_state
            captured_state = state
            yield {
                "planner_node": {
                    "messages": [
                        AIMessage(
                            content=(
                                "好的, 现在我已经获取了足够的信息。"
                                "下面为你规划一个7天的广州之旅。"
                            )
                        )
                    ],
                    "iteration_count": 1,
                }
            }

    async def fake_build_graph(**kwargs: Any) -> CapturingNoItineraryGraph:
        assert kwargs == {"load_mcp_tools": False, "load_rag_tool": False}
        return CapturingNoItineraryGraph()

    async def fake_get_session(session_id: str) -> dict[str, Any]:
        return {
            "message_count": 1,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "我和对象打算下周去广州玩一个周, 从西安出发, "
                        "最后回到西安, 没有忌口, 喜欢自然风光, 预算10000。"
                    ),
                },
                {
                    "role": "assistant",
                    "content": "我已经看到你的目的地、预算和偏好。还差一个关键信息: 这次准备玩几天?",
                },
            ],
        }

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", fake_get_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_demo_fallback_enabled", lambda: True)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={"message": "7天", "session_id": "session-resume-days"},
    )

    assert response.status_code == 200
    assert "event: itinerary" in response.text
    assert saved_sessions[0][1]["itinerary"]["destination"] == "广州"
    assert len(saved_sessions[0][1]["itinerary"]["days"]) == 7
    assert saved_sessions[0][1]["messages"][-2]["content"] == "7天"
    assert captured_state is not None
    last_human = captured_state["messages"][-1]
    assert isinstance(last_human, HumanMessage)
    assert "广州" in last_human.content
    assert "7天" in last_human.content


def test_regional_destination_with_month_and_days_is_complete() -> None:
    message = "7月份川西5天旅游行程, 我们两个人是情侣, 预算8000, 没有忌口。"

    assert chat._build_clarification_message(message, None) is None


def test_trip_start_date_prefers_current_request_over_stale_intent_year() -> None:
    itinerary = {"destination": "西安", "days": []}
    intent = build_heuristic_travel_intent("6月1号自己一个人去西安玩3天，预算6000。")
    intent.start_date = "2024-06-01"

    prepared = chat._prepare_itinerary_for_output(
        itinerary,
        {"kind": "agent_graph", "label": "测试", "detail": ""},
        intent,
        "6月1号自己一个人去西安玩3天，预算6000。",
    )

    assert prepared is not None
    assert prepared["start_date"] == "2026-06-01"


def test_chat_endpoint_replaces_existing_itinerary_for_new_trip(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []
    captured_state: dict[str, Any] | None = None
    existing_itinerary = {
        "destination": "西安",
        "summary": "西安2天历史文化路线。",
        "days": [{"day": 1, "date": "第 1 天", "activities": []}],
    }

    class NewTripGraph:
        async def astream(self, state: dict[str, Any], config: dict[str, Any]):
            nonlocal captured_state
            captured_state = state
            yield {
                "planner_node": {
                    "messages": [
                        AIMessage(
                            content=(
                                "已生成宁波2日游。\n"
                                '<itinerary_json>{"destination":"宁波",'
                                '"budget":null,"total_cost":1200,'
                                '"summary":"宁波2日游。",'
                                '"days":[{"day":1,"date":"第 1 天",'
                                '"activities":[]}]}</itinerary_json>'
                            )
                        )
                    ],
                    "iteration_count": 1,
                }
            }

    async def fake_build_graph(**kwargs: Any) -> NewTripGraph:
        assert kwargs == {"load_mcp_tools": False, "load_rag_tool": False}
        return NewTripGraph()

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    async def fake_get_session(session_id: str) -> dict[str, Any]:
        return {
            "user_profile": {
                "travel_state": {
                    "raw_messages": ["从上海出发, 两个人去西安玩2天, 预算4000"],
                    "intent": {
                        "destination": "西安",
                        "departure_city": "上海",
                        "days": 2,
                        "people": 2,
                        "budget": 4000,
                        "missing_fields": [],
                    },
                    "confirmed": True,
                    "stage": "completed",
                }
            },
            "message_count": 1,
            "messages": [
                {"role": "user", "content": "从上海出发, 两个人去西安玩2天, 预算4000"},
                {
                    "role": "assistant",
                    "content": "外部生成链路没有返回可解析的行程卡片, 先保留西安骨架。",
                },
            ],
        }

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", fake_get_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_demo_fallback_enabled", lambda: False)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "我不去西安了，给我换成宁波的2日游。",
            "session_id": "session-replan",
            "current_itinerary": existing_itinerary,
        },
    )

    assert response.status_code == 200
    assert "event: itinerary" in response.text
    assert captured_state is not None
    assert captured_state["itinerary"] is None
    assert len(captured_state["messages"]) == 2
    assert "后端已确认的本轮结构化需求" in captured_state["messages"][-1].content
    assert "上一趟行程" in captured_state["messages"][-1].content
    assert "西安骨架" not in captured_state["messages"][-1].content
    assert "出发城市: 上海" in captured_state["messages"][-1].content
    assert saved_sessions[0][1]["itinerary"]["destination"] == "宁波"


def test_chat_endpoint_handles_no_self_drive_followup_locally(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []
    existing_itinerary = {
        "destination": "贵州",
        "summary": "贵州4天山水行程。",
        "days": [
            {
                "day": 1,
                "date": "第 1 天",
                "activities": [
                    {
                        "time_slot": "09:00-11:00",
                        "place_name": "天河潭",
                        "place_type": "景点",
                        "lng": 106.5,
                        "lat": 26.5,
                        "description": "游览山水。",
                        "cost": 80,
                    },
                    {
                        "time_slot": "20:00-次日",
                        "place_name": "贵阳市区酒店",
                        "place_type": "住宿",
                        "lng": 106.7,
                        "lat": 26.6,
                        "description": "返回市区住宿。",
                        "cost": 400,
                        "transport": {
                            "mode": "自驾",
                            "distance_km": 35,
                            "duration_min": 50,
                            "description": "租车自驾返回。",
                        },
                    },
                ],
            }
        ],
        "total_cost": 480,
    }

    async def fail_build_graph(**kwargs: Any) -> FakeGraph:
        raise AssertionError("Local preference follow-up should not run Agent graph")

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fail_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "我们不会开车, 最好是当天在哪里玩就附近住。",
            "session_id": "session-followup",
            "current_itinerary": existing_itinerary,
        },
    )

    assert response.status_code == 200
    assert "不自驾版本" in response.text
    assert "event: itinerary" in response.text
    lodging = saved_sessions[0][1]["itinerary"]["days"][0]["activities"][1]
    assert lodging["place_name"] == "天河潭附近住宿"
    assert lodging["transport"]["mode"] == "打车"


def test_chat_endpoint_handles_quick_adjust_locally(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []
    existing_itinerary = {
        "destination": "北京",
        "summary": "北京3天行程。",
        "days": [
            {
                "day": 1,
                "date": "第 1 天",
                "activities": [
                    {
                        "time_slot": "09:00-11:00",
                        "place_name": "故宫博物院",
                        "place_type": "景点",
                        "lng": 116.397,
                        "lat": 39.918,
                        "description": "游览故宫。",
                        "cost": 60,
                    }
                ],
            }
        ],
        "total_cost": 60,
    }

    async def fail_build_graph(**kwargs: Any) -> FakeGraph:
        raise AssertionError("Anchored quick adjust should not run Agent graph")

    async def fail_extract_travel_intent(message: str, previous_intent=None):
        raise AssertionError("Anchored quick adjust should not run intent extraction")

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "extract_travel_intent", fail_extract_travel_intent)
    monkeypatch.setattr(chat, "build_graph", fail_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": (
                "请在第 1 天 09:00-11:00 的 故宫博物院前后增加适当休息时间, "
                "其余日期和未提到的活动保持不变。"
            ),
            "session_id": "session-quick-adjust",
            "current_itinerary": existing_itinerary,
        },
    )

    assert response.status_code == 200
    assert "正在理解局部修改" in response.text
    assert "event: itinerary" in response.text
    activities = saved_sessions[0][1]["itinerary"]["days"][0]["activities"]
    assert [activity["place_name"] for activity in activities] == [
        "故宫博物院",
        "故宫博物院附近休息",
    ]


def test_chat_endpoint_replaces_anchored_activity_locally(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []
    poi_calls: list[dict[str, Any]] = []
    existing_itinerary = {
        "destination": "成都",
        "summary": "成都5天行程。",
        "days": [
            {
                "day": 4,
                "date": "第 4 天",
                "activities": [
                    {
                        "time_slot": "18:00-19:30",
                        "place_name": "乔一乔怪味餐厅(东升店)",
                        "place_type": "餐厅",
                        "lng": 104.08,
                        "lat": 30.66,
                        "description": "特色川菜餐厅。",
                        "cost": 250,
                        "address": "东升街道金河路四段76号",
                        "rating": 4.8,
                        "source": "高德 POI 验证",
                        "is_verified": True,
                    }
                ],
            }
        ],
        "total_cost": 250,
    }

    async def fail_build_graph(**kwargs: Any) -> FakeGraph:
        raise AssertionError("Anchored replacement should not run Agent graph")

    async def fail_extract_travel_intent(message: str, previous_intent=None):
        raise AssertionError("Anchored replacement should not run intent extraction")

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    class FakePOISearch:
        async def ainvoke(self, args: dict[str, Any]) -> list[dict[str, Any]]:
            poi_calls.append(args)
            return [
                {
                    "name": "锦江露台餐厅",
                    "address": "成都市锦江区滨江路1号",
                    "lng": 104.082,
                    "lat": 30.654,
                    "type": "餐饮服务;中餐厅",
                    "rating": "4.6",
                }
            ]

    monkeypatch.setattr(chat, "extract_travel_intent", fail_extract_travel_intent)
    monkeypatch.setattr(chat, "build_graph", fail_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "poi_search", FakePOISearch())
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": (
                "请针对第 4 天 18:00-19:30 的「乔一乔怪味餐厅(东升店)」"
                "进行局部微调：换一个可以坐着看风景吃饭的地方。"
                "其余日期和未提到的活动保持不变，请返回完整行程 JSON。"
            ),
            "session_id": "session-replace-adjust",
            "current_itinerary": existing_itinerary,
        },
    )

    assert response.status_code == 200
    assert "正在理解局部修改" in response.text
    assert "锦江露台餐厅" in response.text
    assert poi_calls == [{"city": "成都", "keyword": "观景餐厅", "top_k": 8}]
    activity = saved_sessions[0][1]["itinerary"]["days"][0]["activities"][0]
    assert activity["place_name"] == "锦江露台餐厅"
    assert activity["address"] == "成都市锦江区滨江路1号"
    assert activity["is_verified"] is True
    assert activity["lng"] == 104.082
    assert activity["lat"] == 30.654
    assert activity["rating"] == 4.6
    assert activity["source"] == "高德 POI 查询"
    assert activity["source_refs"] == ["POI: 锦江露台餐厅", "搜索关键词: 观景餐厅"]
    assert activity["warnings"] == ["到达路线待确认"]


def test_chat_endpoint_falls_back_when_replacement_poi_unavailable(
    monkeypatch,
) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []
    existing_itinerary = {
        "destination": "成都",
        "summary": "成都5天行程。",
        "days": [
            {
                "day": 4,
                "date": "第 4 天",
                "activities": [
                    {
                        "time_slot": "18:00-19:30",
                        "place_name": "乔一乔怪味餐厅(东升店)",
                        "place_type": "餐厅",
                        "lng": 104.08,
                        "lat": 30.66,
                        "description": "特色川菜餐厅。",
                        "cost": 250,
                    }
                ],
            }
        ],
        "total_cost": 250,
    }

    async def fail_build_graph(**kwargs: Any) -> FakeGraph:
        raise AssertionError("Anchored replacement should not run Agent graph")

    async def fail_extract_travel_intent(message: str, previous_intent=None):
        raise AssertionError("Anchored replacement should not run intent extraction")

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    class FakePOISearch:
        async def ainvoke(self, args: dict[str, Any]) -> list[dict[str, Any]]:
            return [{"error": "POI search unavailable: AMap POI API error"}]

    monkeypatch.setattr(chat, "extract_travel_intent", fail_extract_travel_intent)
    monkeypatch.setattr(chat, "build_graph", fail_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "poi_search", FakePOISearch())
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": (
                "请针对第 4 天 18:00-19:30 的「乔一乔怪味餐厅(东升店)」"
                "进行局部微调：换一个可以坐着看风景吃饭的地方。"
            ),
            "session_id": "session-replace-adjust-fallback",
            "current_itinerary": existing_itinerary,
        },
    )

    assert response.status_code == 200
    assert "没有拿到可用真实地点" in response.text
    activity = saved_sessions[0][1]["itinerary"]["days"][0]["activities"][0]
    assert activity["place_name"] == "成都观景休闲餐厅备选(待确认)"
    assert activity["is_verified"] is False
    assert "POI 查询失败: POI search unavailable" in "；".join(activity["warnings"])


def test_chat_endpoint_streams_error(monkeypatch) -> None:
    async def fake_build_graph(**kwargs: Any) -> FakeGraph:
        assert kwargs == {"load_mcp_tools": False, "load_rag_tool": True}
        raise RuntimeError("boom")

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", _ignore_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "我从上海出发, 两个人去北京玩3天, 预算5000",
            "session_id": "session-1",
        },
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "对话服务暂时不可用" in response.text
    assert "event: itinerary" not in response.text
    assert "本地兜底行程" not in response.text
    assert response.text.rstrip().endswith("event: done\ndata: {}")


def test_chat_endpoint_surfaces_llm_auth_error_without_fallback(monkeypatch) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []

    class AuthenticationLikeError(Exception):
        status_code = 401

    async def fake_build_graph(**kwargs: Any) -> FakeGraph:
        raise AuthenticationLikeError("Error code: 401 - api key invalid")

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_demo_fallback_enabled", lambda: True)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "我从上海出发, 两个人去北京玩3天, 预算5000",
            "session_id": "session-auth",
        },
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "DEEPSEEK_API_KEY 无效或已过期" in response.text
    assert "event: itinerary" not in response.text
    assert "保守兜底行程" not in response.text
    assert saved_sessions[0][1]["itinerary"] is None


def test_chat_endpoint_does_not_use_demo_fallback_when_disabled(
    monkeypatch,
) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []

    async def fake_build_graph(**kwargs: Any) -> NoItineraryGraph:
        assert kwargs == {"load_mcp_tools": False, "load_rag_tool": True}
        return NoItineraryGraph()

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_demo_fallback_enabled", lambda: False)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={"message": "北京3天历史文化路线", "session_id": "session-fallback"},
    )

    assert response.status_code == 200
    assert "event: itinerary" not in response.text
    assert saved_sessions[0][1]["itinerary"] is None


def test_chat_endpoint_short_circuits_known_quick_prompt_with_demo_fallback(
    monkeypatch,
) -> None:
    saved_sessions: list[tuple[str, dict[str, Any]]] = []

    async def fail_build_graph(**kwargs: Any) -> NoItineraryGraph:
        raise AssertionError("Known quick prompt should use demo fallback first")

    async def fake_save_session(session_id: str, data: dict[str, Any]) -> None:
        saved_sessions.append((session_id, data))

    monkeypatch.setattr(chat, "build_graph", fail_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", fake_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_demo_fallback_enabled", lambda: True)
    monkeypatch.setattr(chat, "_enforce_chat_rate_limit", _ignore_rate_limit)

    response = _client().post(
        "/api/v1/chat",
        json={
            "message": "我从西安出发, 两个人, 预算5000, 成都4天老人友好行程",
            "session_id": "session-quick",
        },
    )

    assert response.status_code == 200
    assert "event: source" in response.text
    assert '"kind": "demo_fallback"' in response.text
    assert "已生成一版可执行行程" in response.text
    assert "event: itinerary" in response.text
    assert saved_sessions[0][1]["itinerary"]["destination"] == "成都"
    assert saved_sessions[0][1]["itinerary"]["generation_source"]["kind"] == (
        "demo_fallback"
    )
    assert len(saved_sessions[0][1]["itinerary"]["days"]) == 4


async def test_sse_generator_yields_thinking_before_session_load(monkeypatch) -> None:
    session_loaded = False

    async def fake_get_session(session_id: str) -> dict[str, Any]:
        nonlocal session_loaded
        session_loaded = True
        return {}

    monkeypatch.setattr(chat, "get_session", fake_get_session)

    generator = chat.sse_generator("session-1", "hello")
    try:
        first_event = await anext(generator)
    finally:
        await generator.aclose()

    assert first_event.startswith("event: thinking")
    assert session_loaded is False


@pytest.mark.parametrize(
    "message",
    [
        "",
        "   ",
        "\n\t  ",
    ],
)
def test_chat_endpoint_returns_400_for_invalid_body(message: str) -> None:
    response = TestClient(main_app).post(
        "/api/v1/chat",
        json={"message": message, "session_id": "session-1"},
    )

    assert response.status_code == 400
    assert response.json()["path"] == "/api/v1/chat"


def test_chat_endpoint_returns_429_when_rate_limited(monkeypatch) -> None:
    chat._RATE_LIMIT_BUCKET.clear()
    monkeypatch.setattr(chat, "CHAT_RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(chat, "CHAT_RATE_LIMIT_WINDOW_SECONDS", 60.0)

    class RateLimitedGraph:
        async def astream(self, state: dict[str, Any], config: dict[str, Any]):
            yield {"planner_node": {"messages": [AIMessage(content="ok")]}}

    async def fake_build_graph(**kwargs: Any) -> RateLimitedGraph:
        assert kwargs == {"load_mcp_tools": False, "load_rag_tool": False}
        return RateLimitedGraph()

    monkeypatch.setattr(chat, "build_graph", fake_build_graph)
    monkeypatch.setattr(chat, "get_session", _empty_session)
    monkeypatch.setattr(chat, "save_session", _ignore_save_session)
    monkeypatch.setattr(chat, "_demo_mode_enabled", lambda: False)
    monkeypatch.setattr(chat, "_enforce_redis_chat_rate_limit", _fail_rate_limit)

    try:
        first_response = _client().post(
            "/api/v1/chat",
            json={"message": "hello", "session_id": "limited-session"},
        )
        second_response = _client().post(
            "/api/v1/chat",
            json={"message": "hello again", "session_id": "limited-session"},
        )
    finally:
        chat._RATE_LIMIT_BUCKET.clear()

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"] == (
        "Too many chat requests. Please try again shortly."
    )


@pytest.mark.asyncio
async def test_redis_chat_rate_limit_raises_after_threshold(monkeypatch) -> None:
    class FakeRateLimitRedis:
        def __init__(self) -> None:
            self.counts: dict[str, int] = {}
            self.expirations: dict[str, int] = {}

        async def incr(self, name: str) -> int:
            self.counts[name] = self.counts.get(name, 0) + 1
            return self.counts[name]

        async def expire(self, name: str, time: int) -> None:
            self.expirations[name] = time

    fake_redis = FakeRateLimitRedis()
    monkeypatch.setattr(chat, "CHAT_RATE_LIMIT_MAX_REQUESTS", 2)
    monkeypatch.setattr(chat, "CHAT_RATE_LIMIT_WINDOW_SECONDS", 60.0)
    monkeypatch.setattr(chat, "get_redis_client", lambda: fake_redis)

    await chat._enforce_redis_chat_rate_limit("session-redis")
    await chat._enforce_redis_chat_rate_limit("session-redis")

    try:
        await chat._enforce_redis_chat_rate_limit("session-redis")
    except HTTPException as exc:
        assert exc.status_code == 429
    else:
        raise AssertionError("Expected HTTPException")

    assert fake_redis.expirations["rate_limit:chat:session-redis"] == 60


async def _empty_session(session_id: str) -> dict[str, Any]:
    return {}


async def _ignore_save_session(session_id: str, data: dict[str, Any]) -> None:
    return None


async def _ignore_rate_limit(session_id: str) -> None:
    return None


async def _fail_rate_limit(session_id: str) -> None:
    raise RuntimeError("redis unavailable")
