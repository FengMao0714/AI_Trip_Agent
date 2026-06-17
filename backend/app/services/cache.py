"""Redis cache helpers."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol, cast

import redis.asyncio as redis

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL_SECONDS = 3600
POI_CACHE_TTL_SECONDS = 24 * 60 * 60
ROUTE_CACHE_TTL_SECONDS = 24 * 60 * 60
WEATHER_CACHE_TTL_SECONDS = 6 * 60 * 60


class RedisClient(Protocol):
    """Subset of Redis async methods used by the application."""

    async def ping(self) -> bool:
        """Ping Redis and return whether it responds."""

    async def get(self, name: str) -> str | None:
        """Get a Redis value by key."""

    async def incr(self, name: str) -> int:
        """Increment a Redis integer key."""

    async def expire(self, name: str, time: int) -> Any:
        """Set an expiration time on a Redis key."""

    async def setex(self, name: str, time: int, value: str) -> Any:
        """Set a Redis value with TTL."""

    async def delete(self, *names: str) -> int:
        """Delete Redis keys."""

    async def aclose(self) -> None:
        """Close the Redis client."""


_redis_client: RedisClient | None = None


def build_redis_client(settings: Settings | None = None) -> RedisClient:
    """Build a decode-responses Redis client from settings."""
    resolved_settings = settings or get_settings()
    return cast(
        RedisClient,
        redis.Redis(
            host=resolved_settings.redis_host,
            port=resolved_settings.redis_port,
            decode_responses=True,
        ),
    )


async def init_redis(settings: Settings | None = None) -> None:
    """Initialize the shared Redis client."""
    global _redis_client

    if _redis_client is None:
        _redis_client = build_redis_client(settings)


async def close_redis() -> None:
    """Close the shared Redis client."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
    _redis_client = None


def set_redis_client(client: RedisClient | None) -> None:
    """Override the Redis client, primarily for tests."""
    global _redis_client
    _redis_client = client


def get_redis_client() -> RedisClient:
    """Return the shared Redis client, creating it lazily if needed."""
    global _redis_client

    if _redis_client is None:
        _redis_client = build_redis_client()
    return _redis_client


async def get_cache(key: str) -> Any | None:
    """Read a JSON value from Redis cache."""
    raw_value = await get_redis_client().get(key)
    if raw_value is None:
        return None

    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON cache payload for key=%s", key)
        return None


async def set_cache(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL_SECONDS) -> None:
    """Write a JSON value to Redis cache with TTL."""
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    await get_redis_client().setex(key, ttl, payload)


async def delete_cache(key: str) -> None:
    """Delete a Redis cache key."""
    await get_redis_client().delete(key)


def poi_cache_key(city: str, keyword: str) -> str:
    """Return the POI cache key for a city and keyword."""
    return f"poi:{city}:{keyword}"


def route_cache_key(
    origin: str,
    destination: str,
    mode: str,
    city: str = "",
) -> str:
    """Return the route cache key for origin, destination, mode and city."""
    base_key = f"route:{origin}:{destination}:{mode.lower()}"
    return f"{base_key}:{city}" if city else base_key


def weather_cache_key(city: str) -> str:
    """Return the weather cache key for a city."""
    return f"weather:{city}"
