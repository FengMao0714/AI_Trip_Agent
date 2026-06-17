"""Tool implementation tests."""

from __future__ import annotations

import importlib
from typing import Any

import httpx
import pytest

poi_module = importlib.import_module("app.tools.poi_search")
route_module = importlib.import_module("app.tools.route_plan")
weather_module = importlib.import_module("app.tools.weather")
rag_module = importlib.import_module("app.tools.rag_search")


@pytest.fixture(autouse=True)
def disable_tool_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tool tests independent from a real Redis instance."""

    async def fake_get_cache(key: str) -> Any | None:
        return None

    async def fake_set_cache(key: str, value: Any, ttl: int) -> None:
        return None

    for module in (poi_module, route_module, weather_module):
        monkeypatch.setattr(module, "get_cache", fake_get_cache)
        monkeypatch.setattr(module, "set_cache", fake_set_cache)


class FakeResponse:
    """Minimal httpx response double."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        """Match httpx response API."""

    def json(self) -> dict[str, Any]:
        """Return fake JSON response data."""
        return self._data


def fake_async_client(response_data: dict[str, Any]):
    """Build a fake AsyncClient class returning static response data."""

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, params: dict[str, Any]) -> FakeResponse:
            self.url = url
            self.params = params
            return FakeResponse(response_data)

    return FakeAsyncClient


def failing_async_client(exc: Exception):
    """Build a fake AsyncClient class that raises during GET."""

    class FailingAsyncClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> FailingAsyncClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, params: dict[str, Any]) -> FakeResponse:
            raise exc

    return FailingAsyncClient


@pytest.mark.asyncio
async def test_poi_search_returns_normalized_pois(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        poi_module.httpx,
        "AsyncClient",
        fake_async_client(
            {
                "status": "1",
                "pois": [
                    {
                        "name": "故宫博物院",
                        "address": "景山前街4号",
                        "location": "116.397,39.918",
                        "type": "风景名胜",
                        "biz_ext": {"rating": "4.8"},
                    }
                ],
            }
        ),
    )

    result = await poi_module.poi_search.ainvoke(
        {"city": "北京", "keyword": "故宫", "top_k": 1}
    )

    assert result == [
        {
            "name": "故宫博物院",
            "address": "景山前街4号",
            "lng": 116.397,
            "lat": 39.918,
            "type": "风景名胜",
            "rating": "4.8",
        }
    ]


@pytest.mark.asyncio
async def test_poi_search_error_returns_error_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(poi_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(
        poi_module.httpx,
        "AsyncClient",
        fake_async_client({"status": "0", "info": "INVALID_USER_KEY"}),
    )

    result = await poi_module.poi_search.ainvoke(
        {"city": "Beijing", "keyword": "museum", "top_k": 1}
    )

    assert len(result) == 1
    assert "error" in result[0]
    assert "POI search unavailable" in result[0]["error"]


@pytest.mark.asyncio
async def test_poi_search_timeout_returns_error_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(poi_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(
        poi_module.httpx,
        "AsyncClient",
        failing_async_client(httpx.TimeoutException("timed out")),
    )

    result = await poi_module.poi_search.ainvoke(
        {"city": "Beijing", "keyword": "museum", "top_k": 1}
    )

    assert result == [{"error": "POI search unavailable: timed out"}]


@pytest.mark.asyncio
async def test_poi_search_cache_hit_skips_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = [{"name": "Cached Museum", "address": "A"}]

    async def fake_get_cache(key: str) -> list[dict[str, Any]]:
        assert key == "poi:Beijing:museum"
        return cached

    monkeypatch.setattr(poi_module, "get_cache", fake_get_cache)
    monkeypatch.setattr(
        poi_module.httpx,
        "AsyncClient",
        failing_async_client(AssertionError("HTTP should not be called")),
    )

    result = await poi_module.poi_search.ainvoke(
        {"city": "Beijing", "keyword": "museum", "top_k": 5}
    )

    assert result == cached


@pytest.mark.asyncio
async def test_poi_search_cache_miss_writes_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[str, Any, int]] = []

    async def fake_set_cache(key: str, value: Any, ttl: int) -> None:
        writes.append((key, value, ttl))

    monkeypatch.setattr(poi_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(poi_module, "set_cache", fake_set_cache)
    monkeypatch.setattr(
        poi_module.httpx,
        "AsyncClient",
        fake_async_client(
            {
                "status": "1",
                "pois": [
                    {
                        "name": "Cached Later",
                        "address": "A",
                        "location": "116.397,39.918",
                        "type": "museum",
                        "biz_ext": {},
                    }
                ],
            }
        ),
    )

    await poi_module.poi_search.ainvoke(
        {"city": "Beijing", "keyword": "museum", "top_k": 1}
    )

    assert writes[0][0] == "poi:Beijing:museum"
    assert writes[0][2] == 24 * 60 * 60


@pytest.mark.asyncio
async def test_route_plan_returns_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        route_module.httpx,
        "AsyncClient",
        fake_async_client(
            {
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "distance": "2500",
                            "duration": "900",
                            "steps": [{"instruction": "沿景山前街向东步行"}],
                        }
                    ]
                },
            }
        ),
    )

    result = await route_module.route_plan.ainvoke(
        {
            "origin": "116.397,39.918",
            "destination": "116.407,39.918",
            "mode": "walking",
        }
    )

    assert result == {
        "distance_km": 2.5,
        "duration_min": 15.0,
        "steps": ["沿景山前街向东步行"],
    }


@pytest.mark.asyncio
async def test_route_plan_unsupported_mode_returns_error() -> None:
    result = await route_module.route_plan.ainvoke(
        {
            "origin": "116.397,39.918",
            "destination": "116.407,39.918",
            "mode": "bicycle",
        }
    )

    assert result == {
        "error": "Route planning unavailable: Unsupported route mode: bicycle"
    }


@pytest.mark.asyncio
async def test_route_plan_transit_uses_requested_city(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_params: list[dict[str, Any]] = []

    class CapturingAsyncClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> CapturingAsyncClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, params: dict[str, Any]) -> FakeResponse:
            captured_params.append(params)
            return FakeResponse(
                {
                    "status": "1",
                    "route": {
                        "transits": [
                            {
                                "distance": "3600",
                                "duration": "1800",
                                "segments": [{"bus": {"buslines": [{"name": "1路"}]}}],
                            }
                        ]
                    },
                }
            )

    monkeypatch.setattr(route_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(route_module.httpx, "AsyncClient", CapturingAsyncClient)

    result = await route_module.route_plan.ainvoke(
        {
            "origin": "104.056,30.673",
            "destination": "104.075,30.681",
            "mode": "transit",
            "city": "成都",
        }
    )

    assert captured_params[0]["city"] == "成都"
    assert result["distance_km"] == 3.6
    assert result["duration_min"] == 30.0


@pytest.mark.asyncio
async def test_route_plan_transit_requires_city() -> None:
    result = await route_module.route_plan.ainvoke(
        {
            "origin": "104.056,30.673",
            "destination": "104.075,30.681",
            "mode": "transit",
        }
    )

    assert result == {
        "error": "Route planning unavailable: city is required for transit route planning"
    }


@pytest.mark.asyncio
async def test_route_plan_timeout_returns_error_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(route_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(
        route_module.httpx,
        "AsyncClient",
        failing_async_client(httpx.TimeoutException("timed out")),
    )

    result = await route_module.route_plan.ainvoke(
        {
            "origin": "116.397,39.918",
            "destination": "116.407,39.918",
            "mode": "walking",
        }
    )

    assert result == {"error": "Route planning unavailable: timed out"}


@pytest.mark.asyncio
async def test_route_plan_cache_hit_skips_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = {"distance_km": 1.2, "duration_min": 8.0, "steps": ["cached"]}

    async def fake_get_cache(key: str) -> dict[str, Any]:
        assert key == "route:116.397,39.918:116.407,39.918:walking"
        return cached

    monkeypatch.setattr(route_module, "get_cache", fake_get_cache)
    monkeypatch.setattr(
        route_module.httpx,
        "AsyncClient",
        failing_async_client(AssertionError("HTTP should not be called")),
    )

    result = await route_module.route_plan.ainvoke(
        {
            "origin": "116.397,39.918",
            "destination": "116.407,39.918",
            "mode": "Walking",
        }
    )

    assert result == cached


@pytest.mark.asyncio
async def test_route_plan_cache_miss_writes_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[str, Any, int]] = []

    async def fake_set_cache(key: str, value: Any, ttl: int) -> None:
        writes.append((key, value, ttl))

    monkeypatch.setattr(route_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(route_module, "set_cache", fake_set_cache)
    monkeypatch.setattr(
        route_module.httpx,
        "AsyncClient",
        fake_async_client(
            {
                "status": "1",
                "route": {
                    "paths": [{"distance": "1200", "duration": "480", "steps": []}]
                },
            }
        ),
    )

    await route_module.route_plan.ainvoke(
        {
            "origin": "116.397,39.918",
            "destination": "116.407,39.918",
            "mode": "walking",
        }
    )

    assert writes[0][0] == "route:116.397,39.918:116.407,39.918:walking"
    assert writes[0][2] == 24 * 60 * 60


@pytest.mark.asyncio
async def test_weather_returns_forecast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        weather_module.httpx,
        "AsyncClient",
        fake_async_client(
            {
                "status": "1",
                "forecasts": [
                    {
                        "reporttime": "2026-05-05 10:00:00",
                        "casts": [
                            {
                                "date": "2026-05-05",
                                "week": "2",
                                "dayweather": "晴",
                                "nightweather": "多云",
                                "daytemp": "25",
                                "nighttemp": "14",
                                "daywind": "北",
                                "nightwind": "北",
                                "daypower": "3",
                                "nightpower": "3",
                            }
                        ],
                    }
                ],
            }
        ),
    )

    result = await weather_module.weather.ainvoke({"city": "北京"})

    assert result[0]["date"] == "2026-05-05"
    assert result[0]["day_weather"] == "晴"
    assert result[0]["reporttime"] == "2026-05-05 10:00:00"


@pytest.mark.asyncio
async def test_weather_api_error_returns_error_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(weather_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(
        weather_module.httpx,
        "AsyncClient",
        fake_async_client({"status": "0", "info": "INVALID_USER_KEY"}),
    )

    result = await weather_module.weather.ainvoke({"city": "Beijing"})

    assert len(result) == 1
    assert "error" in result[0]
    assert "Weather query unavailable" in result[0]["error"]


@pytest.mark.asyncio
async def test_weather_timeout_returns_error_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(weather_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(
        weather_module.httpx,
        "AsyncClient",
        failing_async_client(httpx.TimeoutException("timed out")),
    )

    result = await weather_module.weather.ainvoke({"city": "Beijing"})

    assert result == [{"error": "Weather query unavailable: timed out"}]


@pytest.mark.asyncio
async def test_weather_cache_hit_skips_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = [{"date": "2026-05-07", "day_weather": "sunny"}]

    async def fake_get_cache(key: str) -> list[dict[str, Any]]:
        assert key == "weather:Beijing"
        return cached

    monkeypatch.setattr(weather_module, "get_cache", fake_get_cache)
    monkeypatch.setattr(
        weather_module.httpx,
        "AsyncClient",
        failing_async_client(AssertionError("HTTP should not be called")),
    )

    result = await weather_module.weather.ainvoke({"city": "Beijing"})

    assert result == cached


@pytest.mark.asyncio
async def test_weather_cache_miss_writes_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[str, Any, int]] = []

    async def fake_set_cache(key: str, value: Any, ttl: int) -> None:
        writes.append((key, value, ttl))

    monkeypatch.setattr(weather_module, "_api_key", lambda: "test-key")
    monkeypatch.setattr(weather_module, "set_cache", fake_set_cache)
    monkeypatch.setattr(
        weather_module.httpx,
        "AsyncClient",
        fake_async_client(
            {
                "status": "1",
                "forecasts": [
                    {
                        "reporttime": "2026-05-07 10:00:00",
                        "casts": [{"date": "2026-05-07", "dayweather": "sunny"}],
                    }
                ],
            }
        ),
    )

    await weather_module.weather.ainvoke({"city": "Beijing"})

    assert writes[0][0] == "weather:Beijing"
    assert writes[0][2] == 6 * 60 * 60


@pytest.mark.asyncio
async def test_rag_search_returns_vector_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_vector_search(
        query_embedding: list[float],
        city: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        assert query_embedding == [0.1] * 1024
        assert city == "北京"
        assert top_k == 5
        return [
            {
                "title": "故宫博物院",
                "content": "故宫博物院位于北京市中心。",
                "metadata": {"address": "北京市东城区景山前街4号"},
                "similarity_score": 0.91,
            }
        ]

    monkeypatch.setattr(rag_module, "encode", lambda query: [0.1] * 1024)
    monkeypatch.setattr(rag_module, "vector_search", fake_vector_search)

    result = await rag_module.rag_search.ainvoke(
        {"query": "北京历史文化景点", "city": "北京", "top_k": 5}
    )

    assert result == [
        {
            "title": "故宫博物院",
            "content": "故宫博物院位于北京市中心。",
            "metadata": {"address": "北京市东城区景山前街4号"},
            "similarity_score": 0.91,
        }
    ]


@pytest.mark.asyncio
async def test_rag_search_returns_error_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rag_module,
        "encode",
        lambda query: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = await rag_module.rag_search.ainvoke(
        {"query": "北京历史文化景点", "city": "北京", "top_k": 5}
    )

    assert result == [{"error": "RAG 检索暂不可用: boom"}]
