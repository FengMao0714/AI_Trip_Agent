"""Service layer tests."""

from __future__ import annotations

import json

import pytest

from app.agent.prompts import render_system_prompt
from app.services import cache
from app.services.session import (
    SESSION_TTL_SECONDS,
    clear_session,
    get_session,
    save_session,
    session_key,
)


class FakeRedis:
    """In-memory Redis double for async cache tests."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.closed = False

    async def ping(self) -> bool:
        return True

    async def get(self, name: str) -> str | None:
        return self.values.get(name)

    async def incr(self, name: str) -> int:
        value = int(self.values.get(name, "0")) + 1
        self.values[name] = str(value)
        return value

    async def expire(self, name: str, time: int) -> bool:
        self.ttls[name] = time
        return True

    async def setex(self, name: str, time: int, value: str) -> None:
        self.values[name] = value
        self.ttls[name] = time

    async def delete(self, *names: str) -> int:
        deleted = 0
        for name in names:
            if name in self.values:
                deleted += 1
                self.values.pop(name)
                self.ttls.pop(name, None)
        return deleted

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def fake_redis() -> FakeRedis:
    client = FakeRedis()
    cache.set_redis_client(client)
    return client


def test_cache_keys_and_ttls_match_phase6_contract() -> None:
    assert cache.poi_cache_key("北京", "故宫") == "poi:北京:故宫"
    assert (
        cache.route_cache_key("116.397,39.918", "116.407,39.918", "Walking")
        == "route:116.397,39.918:116.407,39.918:walking"
    )
    assert (
        cache.route_cache_key("116.397,39.918", "116.407,39.918", "transit", "成都")
        == "route:116.397,39.918:116.407,39.918:transit:成都"
    )
    assert cache.weather_cache_key("北京") == "weather:北京"
    assert cache.POI_CACHE_TTL_SECONDS == 24 * 60 * 60
    assert cache.ROUTE_CACHE_TTL_SECONDS == 24 * 60 * 60
    assert cache.WEATHER_CACHE_TTL_SECONDS == 6 * 60 * 60


@pytest.mark.asyncio
async def test_cache_roundtrip(fake_redis: FakeRedis) -> None:
    await cache.set_cache("weather:北京", {"temp": 25}, ttl=60)

    assert await cache.get_cache("weather:北京") == {"temp": 25}
    assert fake_redis.ttls["weather:北京"] == 60


@pytest.mark.asyncio
async def test_cache_invalid_json_returns_none(fake_redis: FakeRedis) -> None:
    fake_redis.values["bad"] = "{"

    assert await cache.get_cache("bad") is None


@pytest.mark.asyncio
async def test_session_uses_expected_key_and_ttl(fake_redis: FakeRedis) -> None:
    await save_session("abc", {"message_count": 1})

    assert session_key("abc") == "session:abc"
    assert await get_session("abc") == {"message_count": 1}
    assert fake_redis.ttls["session:abc"] == SESSION_TTL_SECONDS

    await clear_session("abc")
    assert await get_session("abc") is None


def test_render_system_prompt_includes_context() -> None:
    prompt = render_system_prompt(
        user_profile={"destination": "北京"},
        current_itinerary={"days": []},
    )

    assert "专业旅行规划助手" in prompt
    assert (
        json.dumps({"destination": "北京"}, ensure_ascii=False, separators=(",", ":"))
        in prompt
    )
    assert json.dumps({"days": []}, ensure_ascii=False, separators=(",", ":")) in prompt


def test_render_system_prompt_includes_prompt_tuning_constraints() -> None:
    prompt = render_system_prompt()

    assert "tool_result" in prompt
    assert "rag_search" in prompt
    assert "poi_search" in prompt
    assert "route_plan" in prompt
    assert "weather" in prompt
    assert "<itinerary_json>...</itinerary_json>" in prompt
    assert "total_cost" in prompt
    assert "110%" in prompt
    assert "必须原样保留" in prompt
