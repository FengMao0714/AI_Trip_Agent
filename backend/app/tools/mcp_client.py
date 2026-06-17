"""MCP client helpers for loading external LangChain tools."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import get_settings

logger = logging.getLogger(__name__)

MCP_CONNECT_TIMEOUT_SECONDS = 5.0
NPM_REGISTRY_ARG = "--registry=https://registry.npmjs.org"
AMAP_MCP_SERVER_NAME = "amap-maps"
AMAP_MCP_SERVER_ARGS = [
    NPM_REGISTRY_ARG,
    "-y",
    "@amap/amap-maps-mcp-server",
]
_mcp_tools_cache: list[BaseTool] | None = None


async def get_mcp_tools(timeout: float = MCP_CONNECT_TIMEOUT_SECONDS) -> list[BaseTool]:
    """Load AMap MCP tools, returning an empty list if the server is unavailable."""
    global _mcp_tools_cache

    if _mcp_tools_cache is not None:
        return _mcp_tools_cache

    settings = get_settings()
    if not settings.amap_api_key:
        logger.warning("AMAP_API_KEY is not configured; MCP tools are unavailable")
        _mcp_tools_cache = []
        return []

    env = {
        **os.environ,
        "AMAP_API_KEY": settings.amap_api_key,
        "AMAP_MAPS_API_KEY": settings.amap_api_key,
    }

    client = MultiServerMCPClient(
        {
            AMAP_MCP_SERVER_NAME: {
                "transport": "stdio",
                "command": "npx",
                "args": AMAP_MCP_SERVER_ARGS,
                "env": env,
            }
        }
    )

    try:
        logger.info("Loading AMap MCP tools via %s", AMAP_MCP_SERVER_NAME)
        tools: list[BaseTool] = await asyncio.wait_for(
            client.get_tools(),
            timeout=timeout,
        )
    except TimeoutError:
        logger.warning(
            "AMap MCP connection via %s timed out after %.1fs",
            AMAP_MCP_SERVER_NAME,
            timeout,
        )
        _mcp_tools_cache = []
        return []
    except Exception as exc:
        logger.warning(
            "AMap MCP connection via %s failed: %s", AMAP_MCP_SERVER_NAME, exc
        )
        _mcp_tools_cache = []
        return []

    if tools:
        logger.info("Loaded %d AMap MCP tools via %s", len(tools), AMAP_MCP_SERVER_NAME)
        _mcp_tools_cache = tools
        return tools

    logger.warning("AMap MCP server %s returned no tools", AMAP_MCP_SERVER_NAME)

    _mcp_tools_cache = []
    return []


def describe_tool(tool: BaseTool) -> dict[str, Any]:
    """Return safe diagnostic metadata for an MCP tool."""
    return {
        "name": tool.name,
        "description": tool.description,
        "args": getattr(tool, "args", {}),
    }
