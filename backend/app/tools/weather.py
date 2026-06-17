"""AMap weather forecast LangChain tool with direct HTTP fallback."""

from __future__ import annotations

import logging
import time

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.services.cache import (
    WEATHER_CACHE_TTL_SECONDS,
    get_cache,
    set_cache,
    weather_cache_key,
)

logger = logging.getLogger(__name__)

AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
HTTP_TIMEOUT_SECONDS = 5.0


class ToolCallError(RuntimeError):
    """Raised when an external tool call returns an API-level error."""


def _api_key() -> str:
    key = get_settings().amap_api_key
    if not key:
        raise ToolCallError("AMAP_API_KEY is not configured")
    return key


async def _get_cached_weather(city: str) -> list[dict] | None:
    """Read cached weather data, keeping tool execution resilient."""
    key = weather_cache_key(city)
    try:
        cached = await get_cache(key)
    except Exception as exc:
        logger.warning("Weather cache read failed key=%s: %s", key, exc)
        return None

    if isinstance(cached, list):
        logger.info("Weather cache hit key=%s", key)
        return cached
    return None


async def _set_cached_weather(city: str, value: list[dict]) -> None:
    """Write weather data to cache without failing the tool."""
    key = weather_cache_key(city)
    try:
        await set_cache(key, value, ttl=WEATHER_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Weather cache write failed key=%s: %s", key, exc)


async def _fallback_weather(city: str) -> list[dict]:
    """Call AMap weather forecast directly."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(
            AMAP_WEATHER_URL,
            params={
                "key": _api_key(),
                "city": city,
                "extensions": "all",
                "output": "json",
            },
        )
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "1":
        raise ToolCallError(f"AMap weather API error: {data.get('info', 'unknown')}")

    forecasts = data.get("forecasts", [])
    if not forecasts:
        return []

    city_forecast = forecasts[0]
    reporttime = city_forecast.get("reporttime", "")
    return [
        {
            "date": cast.get("date", ""),
            "week": cast.get("week", ""),
            "day_weather": cast.get("dayweather", ""),
            "night_weather": cast.get("nightweather", ""),
            "day_temp": cast.get("daytemp", ""),
            "night_temp": cast.get("nighttemp", ""),
            "day_wind": cast.get("daywind", ""),
            "night_wind": cast.get("nightwind", ""),
            "day_power": cast.get("daypower", ""),
            "night_power": cast.get("nightpower", ""),
            "reporttime": reporttime,
        }
        for cast in city_forecast.get("casts", [])
        if isinstance(cast, dict)
    ]


@tool
async def weather(city: str) -> list[dict]:
    """Query the weather forecast for a city or adcode.

    Args:
        city: City name or adcode, for example "北京" or "110000".

    Returns:
        A list of daily weather forecast dictionaries.
    """
    start_time = time.perf_counter()
    logger.info("Weather query city=%s", city)
    try:
        cached = await _get_cached_weather(city)
        if cached is not None:
            return cached

        result = await _fallback_weather(city)
        await _set_cached_weather(city, result)
        return result
    except Exception as exc:
        logger.exception(
            "Weather query failed after %.3fs", time.perf_counter() - start_time
        )
        return [{"error": f"Weather query unavailable: {exc}"}]
    finally:
        logger.info(
            "Weather query completed in %.3fs", time.perf_counter() - start_time
        )
