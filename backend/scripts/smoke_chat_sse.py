"""Smoke-test the live chat SSE endpoint before demos."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 180.0


@dataclass
class SmokeResult:
    name: str
    duration_seconds: float
    events: list[str]
    itinerary: dict[str, Any] | None
    content: str


def _parse_sse_block(block: str) -> tuple[str, dict[str, Any] | str] | None:
    event = "content"
    data_lines: list[str] = []

    for line in block.splitlines():
        if not line or line.startswith(":"):
            continue
        if line.startswith("event:"):
            event = line.removeprefix("event:").strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").lstrip())

    if not data_lines:
        return None

    raw_data = "\n".join(data_lines)
    try:
        data: dict[str, Any] | str = json.loads(raw_data)
    except json.JSONDecodeError:
        data = raw_data

    return event, data


async def _collect_sse(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    current_itinerary: dict[str, Any] | None = None,
    message: str,
    session_id: str,
) -> SmokeResult:
    started_at = time.perf_counter()
    events: list[str] = []
    content_parts: list[str] = []
    itinerary: dict[str, Any] | None = None
    buffer = ""

    async with client.stream(
        "POST",
        f"{base_url.rstrip('/')}/api/v1/chat",
        json={
            "message": message,
            "session_id": session_id,
            "current_itinerary": current_itinerary,
        },
        headers={"Accept": "text/event-stream"},
    ) as response:
        response.raise_for_status()
        async for chunk in response.aiter_text():
            buffer += chunk
            blocks = buffer.split("\n\n")
            buffer = blocks.pop() or ""
            for block in blocks:
                parsed = _parse_sse_block(block)
                if parsed is None:
                    continue
                event, data = parsed
                events.append(event)
                if isinstance(data, dict) and event == "content":
                    text = data.get("text")
                    if isinstance(text, str):
                        content_parts.append(text)
                if isinstance(data, dict) and event == "itinerary":
                    candidate = data.get("itinerary")
                    if isinstance(candidate, dict):
                        itinerary = candidate

    duration = time.perf_counter() - started_at
    return SmokeResult(
        name=session_id,
        duration_seconds=duration,
        events=events,
        itinerary=itinerary,
        content="".join(content_parts),
    )


def _assert_events(
    result: SmokeResult,
    *,
    expect_itinerary: bool,
    required_events: Iterable[str],
) -> None:
    missing = [event for event in required_events if event not in result.events]
    if missing:
        msg = f"{result.name} missing events: {', '.join(missing)}"
        raise AssertionError(msg)

    if expect_itinerary and result.itinerary is None:
        raise AssertionError(f"{result.name} did not return an itinerary event")
    if not expect_itinerary and result.itinerary is not None:
        raise AssertionError(f"{result.name} unexpectedly returned an itinerary")


async def run_smoke(args: argparse.Namespace) -> None:
    base_url = str(args.base_url)
    timeout = httpx.Timeout(float(args.timeout), connect=10.0)
    prefix = f"smoke-{uuid.uuid4().hex[:8]}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        clarify = await _collect_sse(
            client,
            base_url=base_url,
            message="我想去贵州旅游, 预算3000, 喜欢自然风光。",
            session_id=f"{prefix}-clarify",
        )
        _assert_events(
            clarify,
            expect_itinerary=False,
            required_events=["thinking", "content", "done"],
        )

        valid = await _collect_sse(
            client,
            base_url=base_url,
            message=args.valid_message,
            session_id=f"{prefix}-valid",
        )
        _assert_events(
            valid,
            expect_itinerary=True,
            required_events=["thinking", "content", "itinerary", "done"],
        )

        adjust = await _collect_sse(
            client,
            base_url=base_url,
            current_itinerary=valid.itinerary,
            message=args.adjust_message,
            session_id=f"{prefix}-adjust",
        )
        _assert_events(
            adjust,
            expect_itinerary=True,
            required_events=["thinking", "content", "itinerary", "done"],
        )

    for result in [clarify, valid, adjust]:
        event_sequence = " -> ".join(result.events)
        destination = (
            result.itinerary.get("destination")
            if isinstance(result.itinerary, dict)
            else "-"
        )
        print(
            f"[OK] {result.name}: {result.duration_seconds:.2f}s | "
            f"events={event_sequence} | destination={destination}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--valid-message",
        default="北京3天历史文化路线, 预算3000, 不吃辣。",
        help="Message expected to produce an itinerary.",
    )
    parser.add_argument(
        "--adjust-message",
        default="请把第二天下午调整为咖啡馆休息, 其余行程保持不变。",
        help="Follow-up message expected to update an existing itinerary.",
    )
    return parser.parse_args()


def main() -> None:
    asyncio.run(run_smoke(parse_args()))


if __name__ == "__main__":
    main()
