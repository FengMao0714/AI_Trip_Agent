"""AMap POI search LangChain tool with direct HTTP fallback."""

from __future__ import annotations

import logging
import time

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.services.cache import (
    POI_CACHE_TTL_SECONDS,
    get_cache,
    poi_cache_key,
    set_cache,
)

logger = logging.getLogger(__name__)

AMAP_PLACE_TEXT_URL = "https://restapi.amap.com/v3/place/text"
HTTP_TIMEOUT_SECONDS = 5.0


class ToolCallError(RuntimeError):
    """Raised when an external tool call returns an API-level error."""


def _api_key() -> str:
    key = get_settings().amap_api_key
    if not key:
        raise ToolCallError("AMAP_API_KEY is not configured")
    return key


def _split_location(location: str) -> tuple[float | None, float | None]:
    if not location:
        return None, None

    parts = location.split(",", maxsplit=1)
    if len(parts) != 2:
        return None, None

    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


async def _get_cached_poi(city: str, keyword: str) -> list[dict] | None:
    """Read cached POI data, keeping tool execution resilient."""
    key = poi_cache_key(city, keyword)
    try:
        cached = await get_cache(key)
    except Exception as exc:
        logger.warning("POI cache read failed key=%s: %s", key, exc)
        return None

    if isinstance(cached, list):
        logger.info("POI cache hit key=%s", key)
        return cached
    return None


async def _set_cached_poi(city: str, keyword: str, value: list[dict]) -> None:
    """Write POI data to cache without failing the tool."""
    key = poi_cache_key(city, keyword)
    try:
        await set_cache(key, value, ttl=POI_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("POI cache write failed key=%s: %s", key, exc)


async def _fallback_poi_search(city: str, keyword: str, top_k: int = 5) -> list[dict]:
    """Call AMap place text search directly."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(
            AMAP_PLACE_TEXT_URL,
            params={
                "key": _api_key(),
                "keywords": keyword,
                "city": city,
                "citylimit": "true",
                "offset": min(max(top_k, 1), 25),
                "page": 1,
                "extensions": "all",
                "output": "json",
            },
        )
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "1":
        raise ToolCallError(f"AMap POI API error: {data.get('info', 'unknown')}")

    results: list[dict] = []
    for poi in data.get("pois", [])[:top_k]:
        lng, lat = _split_location(str(poi.get("location", "")))
        biz_ext = poi.get("biz_ext") if isinstance(poi.get("biz_ext"), dict) else {}
        results.append(
            {
                "name": poi.get("name", ""),
                "address": poi.get("address", ""),
                "lng": lng,
                "lat": lat,
                "type": poi.get("type", ""),
                "rating": biz_ext.get("rating", ""),
            }
        )

    return results


@tool
async def poi_search(city: str, keyword: str, top_k: int = 5) -> list[dict]:
    """Search points of interest in a city, such as attractions or restaurants.

    Args:
        city: Target city name, citycode, or adcode, for example "北京".
        keyword: Search keyword, for example "故宫" or "历史文化景点".
        top_k: Maximum number of POI results to return, default is 5.

    Returns:
        A list of POI dictionaries with name, address, lng, lat, type, and rating.
    """
    start_time = time.perf_counter()
    logger.info("POI search city=%s keyword=%s top_k=%d", city, keyword, top_k)
    try:
        cached = await _get_cached_poi(city, keyword)
        if cached is not None:
            return cached[:top_k]

        results = await _fallback_poi_search(city, keyword, top_k)
        await _set_cached_poi(city, keyword, results)
        return results
    except Exception as exc:
        logger.exception(
            "POI search failed after %.3fs", time.perf_counter() - start_time
        )
        return [{"error": f"POI search unavailable: {exc}"}]
    finally:
        logger.info("POI search completed in %.3fs", time.perf_counter() - start_time)
