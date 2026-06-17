"""AMap route planning LangChain tool with direct HTTP fallback."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.services.cache import (
    ROUTE_CACHE_TTL_SECONDS,
    get_cache,
    route_cache_key,
    set_cache,
)

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 5.0
ROUTE_ENDPOINTS = {
    "driving": "https://restapi.amap.com/v3/direction/driving",
    "walking": "https://restapi.amap.com/v3/direction/walking",
    "transit": "https://restapi.amap.com/v3/direction/transit/integrated",
}


class ToolCallError(RuntimeError):
    """Raised when an external tool call returns an API-level error."""


def _api_key() -> str:
    key = get_settings().amap_api_key
    if not key:
        raise ToolCallError("AMAP_API_KEY is not configured")
    return key


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _step_text(step: dict[str, Any]) -> str:
    instruction = step.get("instruction")
    if isinstance(instruction, str) and instruction:
        return instruction

    buslines = step.get("bus", {}).get("buslines", [])
    if buslines:
        names = [line.get("name", "") for line in buslines if isinstance(line, dict)]
        return " -> ".join(name for name in names if name)

    return ""


def _parse_standard_route(data: dict[str, Any]) -> dict[str, Any]:
    paths = data.get("route", {}).get("paths", [])
    path = paths[0] if paths else {}
    steps = path.get("steps", [])
    return {
        "distance_km": round(_as_float(path.get("distance")) / 1000, 2),
        "duration_min": round(_as_float(path.get("duration")) / 60, 1),
        "steps": [_step_text(step) for step in steps if isinstance(step, dict)],
    }


def _parse_transit_route(data: dict[str, Any]) -> dict[str, Any]:
    transits = data.get("route", {}).get("transits", [])
    transit = transits[0] if transits else {}
    segments = transit.get("segments", [])
    return {
        "distance_km": round(_as_float(transit.get("distance")) / 1000, 2),
        "duration_min": round(_as_float(transit.get("duration")) / 60, 1),
        "steps": [
            _step_text(segment) for segment in segments if isinstance(segment, dict)
        ],
    }


async def _get_cached_route(
    origin: str,
    destination: str,
    mode: str,
    city: str = "",
) -> dict[str, Any] | None:
    """Read cached route data, keeping tool execution resilient."""
    key = route_cache_key(origin, destination, mode, city)
    try:
        cached = await get_cache(key)
    except Exception as exc:
        logger.warning("Route cache read failed key=%s: %s", key, exc)
        return None

    if isinstance(cached, dict):
        logger.info("Route cache hit key=%s", key)
        return cached
    return None


async def _set_cached_route(
    origin: str,
    destination: str,
    mode: str,
    value: dict[str, Any],
    city: str = "",
) -> None:
    """Write route data to cache without failing the tool."""
    key = route_cache_key(origin, destination, mode, city)
    try:
        await set_cache(key, value, ttl=ROUTE_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Route cache write failed key=%s: %s", key, exc)


async def _fallback_route_plan(
    origin: str,
    destination: str,
    mode: str = "driving",
    city: str = "",
) -> dict[str, Any]:
    """Call AMap route planning directly."""
    normalized_mode = mode.lower()
    if normalized_mode not in ROUTE_ENDPOINTS:
        raise ToolCallError(f"Unsupported route mode: {mode}")

    params = {
        "key": _api_key(),
        "origin": origin,
        "destination": destination,
        "extensions": "all",
        "output": "json",
    }
    if normalized_mode == "transit":
        if not city.strip():
            raise ToolCallError("city is required for transit route planning")
        params["city"] = city.strip()

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(ROUTE_ENDPOINTS[normalized_mode], params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "1":
        raise ToolCallError(f"AMap route API error: {data.get('info', 'unknown')}")

    if normalized_mode == "transit":
        return _parse_transit_route(data)
    return _parse_standard_route(data)


@tool
async def route_plan(
    origin: str,
    destination: str,
    mode: str = "driving",
    city: str = "",
) -> dict[str, Any]:
    """Plan a route between two longitude-latitude coordinates.

    Args:
        origin: Start coordinate in "lng,lat" format.
        destination: Destination coordinate in "lng,lat" format.
        mode: Travel mode, one of "driving", "transit", or "walking".
        city: City name or adcode required for transit, for example "成都".

    Returns:
        A route summary with distance_km, duration_min, and textual steps.
    """
    start_time = time.perf_counter()
    logger.info(
        "Route plan origin=%s destination=%s mode=%s city=%s",
        origin,
        destination,
        mode,
        city,
    )
    try:
        cached = await _get_cached_route(origin, destination, mode, city)
        if cached is not None:
            return cached

        result = await _fallback_route_plan(origin, destination, mode, city)
        await _set_cached_route(origin, destination, mode, result, city)
        return result
    except Exception as exc:
        logger.exception(
            "Route plan failed after %.3fs", time.perf_counter() - start_time
        )
        return {"error": f"Route planning unavailable: {exc}"}
    finally:
        logger.info("Route plan completed in %.3fs", time.perf_counter() - start_time)
