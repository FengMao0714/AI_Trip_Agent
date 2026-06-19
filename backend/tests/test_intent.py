"""Travel intent extraction tests."""
# ruff: noqa: RUF001

from __future__ import annotations

from typing import Any

import pytest

from app.agent import intent as intent_module
from app.agent.clarification import ClarificationAgent
from app.agent.intent import (
    IntentExtractionAgent,
    QueryUnderstandingAgent,
    RequirementValidator,
    TravelIntent,
    TravelState,
    build_heuristic_travel_intent,
    update_travel_state,
)


def test_heuristic_intent_extracts_natural_language_constraints() -> None:
    intent = build_heuristic_travel_intent(
        "我想和女朋友毕业后去云南玩几天，别太累，预算一般"
    )

    assert intent.destination == "云南"
    assert intent.people == 2
    assert intent.start_date == "毕业后"
    assert intent.travel_style == "情侣"
    assert "别太累" in intent.constraints
    assert "预算一般" in intent.constraints
    assert intent.days is None
    assert intent.missing_fields == ["days", "budget"]


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "我想去成都玩三天，预算3000，两个人，从广州出发。",
            {
                "destination": "成都",
                "departure_city": "广州",
                "days": 3,
                "people": 2,
                "budget": 3000,
                "missing_fields": [],
            },
        ),
        (
            "我和女朋友毕业后想去云南玩几天，不想太累，预算一般。",
            {
                "destination": "云南",
                "people": 2,
                "travel_style": "情侣",
                "missing_fields": ["days", "budget"],
                "contains_preferences": ["情侣出行"],
                "contains_constraints": ["不想太累", "预算一般"],
            },
        ),
        (
            "帮我安排一个日本旅行。",
            {
                "destination": "日本",
                "missing_fields": ["days", "people", "budget"],
            },
        ),
        (
            "一家三口想暑假去北京，主要想带孩子玩。",
            {
                "destination": "北京",
                "people": 3,
                "travel_style": "亲子",
                "start_date": "暑假",
                "missing_fields": ["days", "budget"],
            },
        ),
        (
            "从上海出发，五一去杭州，别太贵，两天一夜。",
            {
                "destination": "杭州",
                "departure_city": "上海",
                "days": 2,
                "people": 1,
                "start_date": "五一",
                "missing_fields": ["budget"],
                "contains_constraints": ["别太贵"],
            },
        ),
        (
            "我要去西安",
            {
                "destination": "西安",
                "people": 1,
                "missing_fields": ["days", "budget"],
            },
        ),
        (
            "我和父母下周去西安玩三天，喜欢历史文化，预算一万元。",
            {
                "destination": "西安",
                "days": 3,
                "people": 3,
                "budget": 10000,
                "travel_style": "休闲",
                "start_date": "下周",
                "missing_fields": [],
                "contains_preferences": ["历史文化", "老人友好"],
            },
        ),
        (
            "下周要去西安玩三天，三个老人，预算五千元。",
            {
                "destination": "西安",
                "days": 3,
                "people": 3,
                "budget": 5000,
                "travel_style": "休闲",
                "start_date": "下周",
                "missing_fields": [],
                "contains_preferences": ["老人友好"],
                "contains_constraints": ["老人"],
            },
        ),
        (
            "我自己下周想去西安玩5天，喜欢历史文化，预算1.5万。",
            {
                "destination": "西安",
                "days": 5,
                "people": 1,
                "budget": 15000,
                "start_date": "下周",
                "missing_fields": [],
                "contains_preferences": ["历史文化"],
            },
        ),
        (
            "我下周四要去西安游玩5天，喜欢历史文化，预算5000元。",
            {
                "destination": "西安",
                "days": 5,
                "people": 1,
                "budget": 5000,
                "start_date": "下周四",
                "missing_fields": [],
                "contains_preferences": ["历史文化"],
            },
        ),
    ],
)
def test_heuristic_intent_handles_natural_language_examples(
    message: str,
    expected: dict[str, Any],
) -> None:
    intent = build_heuristic_travel_intent(message)

    for field in (
        "destination",
        "departure_city",
        "days",
        "people",
        "budget",
        "travel_style",
        "start_date",
        "missing_fields",
    ):
        if field in expected:
            assert getattr(intent, field) == expected[field]

    for value in expected.get("contains_preferences", []):
        assert value in intent.preferences
    for value in expected.get("contains_constraints", []):
        assert value in intent.constraints


def test_query_understanding_agent_alias_keeps_intent_extractor_contract() -> None:
    assert QueryUnderstandingAgent is IntentExtractionAgent


def test_clarification_agent_asks_natural_followup() -> None:
    state = TravelState(
        intent=build_heuristic_travel_intent(
            "我和女朋友毕业后想去云南玩几天，不想太累，预算一般。"
        )
    )

    question = ClarificationAgent().ask(state)

    assert "情侣出行" in question
    assert "云南" in question
    assert "不太累" in question
    assert "中等预算" in question
    assert "计划玩几天" in question
    assert "总预算大概多少" in question


def test_heuristic_intent_merges_day_answer_with_previous_intent() -> None:
    previous = TravelIntent(destination="云南", people=2, missing_fields=["days"])

    intent = build_heuristic_travel_intent("7天", previous)

    assert intent.destination == "云南"
    assert intent.people == 2
    assert intent.days == 7
    assert intent.missing_fields == ["budget"]


def test_travel_intent_normalizes_llm_style_string_values() -> None:
    intent = TravelIntent(
        destination="西安",
        days="三天",
        people="我和父母",
        budget="一千快",
    )

    validated = RequirementValidator().apply(TravelState(intent=intent))

    assert validated.intent.days == 3
    assert validated.intent.people == 3
    assert validated.intent.budget == 1000
    assert validated.intent.missing_fields == []
    assert validated.intent.invalid_fields == []
    assert validated.stage == "ready_to_plan"


def test_requirement_validator_marks_invalid_numeric_values() -> None:
    intent = TravelIntent(
        destination="西安",
        days=0,
        people=-2,
        budget=-100,
        missing_fields=[],
        confidence=1.0,
    )

    validated = RequirementValidator().apply(TravelState(intent=intent))
    question = ClarificationAgent().ask(validated)

    assert validated.intent.missing_fields == []
    assert validated.intent.invalid_fields == ["days", "people", "budget"]
    assert validated.stage == "collecting_info"
    assert validated.confirmed is False
    assert "出行天数需要大于 0 天" in question
    assert "出行人数需要大于 0 人" in question
    assert "预算需要大于 0 元" in question


async def test_intent_extraction_agent_accepts_structured_llm(monkeypatch) -> None:
    class FakeStructuredLLM:
        def with_structured_output(
            self, schema: type[TravelIntent]
        ) -> FakeStructuredLLM:
            return self

        async def ainvoke(self, messages: list[Any]) -> TravelIntent:
            return TravelIntent(
                destination="云南",
                days=5,
                people=2,
                preferences=["自然风光"],
                confidence=0.92,
            )

    monkeypatch.setattr(intent_module, "_llm_extraction_enabled", lambda: True)

    result = await IntentExtractionAgent(llm=FakeStructuredLLM()).extract(
        "我想和女朋友毕业后去云南玩几天，喜欢自然风光"
    )

    assert result.destination == "云南"
    assert result.days == 5
    assert result.people == 2
    assert "自然风光" in result.preferences
    assert "情侣出行" in result.preferences
    assert result.missing_fields == ["budget"]
    assert result.confidence == 0.92


async def test_intent_extraction_agent_normalizes_string_values_from_llm(
    monkeypatch,
) -> None:
    class FakeStructuredLLM:
        def with_structured_output(
            self, schema: type[TravelIntent]
        ) -> FakeStructuredLLM:
            return self

        async def ainvoke(self, messages: list[Any]) -> dict[str, Any]:
            return {
                "destination": "西安",
                "days": "三天",
                "people": "我和父母",
                "budget": "一千快",
                "confidence": 0.94,
            }

    monkeypatch.setattr(intent_module, "_llm_extraction_enabled", lambda: True)

    result = await IntentExtractionAgent(llm=FakeStructuredLLM()).extract(
        "给我做一份西安旅行方案"
    )

    assert result.destination == "西安"
    assert result.days == 3
    assert result.people == 3
    assert result.budget == 1000
    assert result.missing_fields == []
    assert result.invalid_fields == []
    assert result.confidence == 0.94


async def test_intent_extraction_agent_falls_back_when_llm_fails(monkeypatch) -> None:
    class FailingLLM:
        def with_structured_output(self, schema: type[TravelIntent]) -> FailingLLM:
            return self

        async def ainvoke(self, messages: list[Any]) -> TravelIntent:
            raise RuntimeError("upstream timeout")

    monkeypatch.setattr(intent_module, "_llm_extraction_enabled", lambda: True)

    result = await IntentExtractionAgent(llm=FailingLLM()).extract(
        "我和父母下周去西安玩三天，预算一万元。"
    )

    assert result.destination == "西安"
    assert result.days == 3
    assert result.people == 3
    assert result.budget == 10000
    assert result.missing_fields == []


def test_travel_state_update_preserves_previous_fields() -> None:
    state = TravelState(
        raw_messages=["我想和女朋友毕业后去云南玩几天，别太累，预算一般"],
        intent=build_heuristic_travel_intent(
            "我想和女朋友毕业后去云南玩几天，别太累，预算一般"
        ),
    )

    updated = update_travel_state(
        state,
        "从西安出发，两个人，预算8000，玩5天",
        build_heuristic_travel_intent("从西安出发，两个人，预算8000，玩5天"),
    )

    assert updated.raw_messages == [
        "我想和女朋友毕业后去云南玩几天，别太累，预算一般",
        "从西安出发，两个人，预算8000，玩5天",
    ]
    assert updated.intent.destination == "云南"
    assert updated.intent.departure_city == "西安"
    assert updated.intent.people == 2
    assert updated.intent.budget == 8000
    assert updated.intent.days == 5
    assert updated.intent.missing_fields == []
    assert updated.stage == "ready_to_plan"
    assert updated.confirmed is True


def test_travel_state_update_resets_trip_scoped_style_for_new_destination() -> None:
    state = TravelState(
        raw_messages=["我和对象从上海出发，下周二去厦门玩4天，没有忌口，预算8000。"],
        intent=build_heuristic_travel_intent(
            "我和对象从上海出发，下周二去厦门玩4天，没有忌口，预算8000。"
        ),
    )

    updated = update_travel_state(
        state,
        "6月1号自己一个人去西安玩3天，预算6000。",
        build_heuristic_travel_intent("6月1号自己一个人去西安玩3天，预算6000。"),
    )

    assert updated.intent.destination == "西安"
    assert updated.intent.departure_city == "上海"
    assert updated.intent.people == 1
    assert updated.intent.travel_style is None
    assert "情侣出行" not in updated.intent.preferences
    assert updated.intent.missing_fields == []


def test_requirement_validator_ignores_llm_ready_claim() -> None:
    intent = TravelIntent(
        destination="云南",
        days=5,
        people=2,
        missing_fields=[],
        confidence=1.0,
    )

    validated = RequirementValidator().apply(TravelState(intent=intent))

    assert validated.intent.missing_fields == ["budget"]
    assert validated.stage == "collecting_info"
    assert validated.confirmed is False
