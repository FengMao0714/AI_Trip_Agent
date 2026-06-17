"""Tests for deterministic demo itineraries."""

from __future__ import annotations

import json

from app.services.demo_itinerary import build_demo_itinerary


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def test_beijing_history_demo_itinerary() -> None:
    itinerary = build_demo_itinerary(
        "\u6211\u60f3\u53bb\u5317\u4eac\u73a93\u5929\uff0c"
        "\u9884\u7b973000\u5143\uff0c"
        "\u559c\u6b22\u5386\u53f2\u6587\u5316\uff0c\u4e0d\u5403\u8fa3"
    )

    assert itinerary is not None
    assert itinerary["destination"] == "\u5317\u4eac"
    assert itinerary["budget"] == 3000
    assert len(itinerary["days"]) == 3
    assert "\u6545\u5bab" in _dump(itinerary)


def test_beijing_history_quick_prompt_demo_itinerary() -> None:
    itinerary = build_demo_itinerary("北京3天历史文化路线")

    assert itinerary is not None
    assert itinerary["destination"] == "北京"
    assert itinerary["budget"] == 3000
    assert len(itinerary["days"]) == 3


def test_coffee_adjustment_keeps_existing_itinerary_context() -> None:
    itinerary = build_demo_itinerary(
        "\u6211\u60f3\u53bb\u5317\u4eac\u73a93\u5929\uff0c"
        "\u9884\u7b973000\u5143\uff0c"
        "\u559c\u6b22\u5386\u53f2\u6587\u5316"
    )

    adjusted = build_demo_itinerary(
        "\u628a\u7b2c\u4e8c\u5929\u4e0b\u5348\u6362\u6210\u5496\u5561\u9986",
        itinerary,
    )

    assert adjusted is not None
    text = _dump(adjusted)
    assert "Berry Beans" in text
    assert "Page One" in text
    assert "\u5929\u575b" in text


def test_chengdu_elder_friendly_demo_itinerary() -> None:
    itinerary = build_demo_itinerary(
        "\u5e2670\u5c81\u7237\u7237\u53bb\u6210\u90fd4\u5929\uff0c"
        "\u9884\u7b975000\uff0c\u8d70\u4e0d\u4e86\u8fdc\u8def"
    )

    assert itinerary is not None
    assert itinerary["destination"] == "\u6210\u90fd"
    assert itinerary["budget"] == 5000
    assert len(itinerary["days"]) == 4
    assert any(
        term in _dump(itinerary)
        for term in [
            "\u5348\u4f11",
            "\u6253\u8f66",
            "\u77ed\u8ddd\u79bb",
            "\u8001\u4eba",
        ]
    )


def test_chengdu_elder_friendly_quick_prompt_demo_itinerary() -> None:
    itinerary = build_demo_itinerary("成都4天老人友好行程")

    assert itinerary is not None
    assert itinerary["destination"] == "成都"
    assert itinerary["budget"] == 5000
    assert len(itinerary["days"]) == 4


def test_shanghai_family_quick_prompt_demo_itinerary() -> None:
    itinerary = build_demo_itinerary("上海2天亲子轻松游")

    assert itinerary is not None
    assert itinerary["destination"] == "上海"
    assert itinerary["budget"] == 2500
    assert len(itinerary["days"]) == 2
    assert "上海自然博物馆" in _dump(itinerary)
