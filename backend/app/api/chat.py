"""Chat API routes with Server-Sent Events streaming."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncIterator
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.agent.clarification import ClarificationAgent
from app.agent.graph import build_graph
from app.agent.intent import (
    RequirementValidator,
    TravelIntent,
    TravelState,
    extract_travel_intent,
    intent_from_user_profile,
    travel_state_from_user_profile,
    travel_state_with_stage,
    update_travel_state,
    user_profile_with_travel_state,
)
from app.agent.nodes import (
    _build_conservative_itinerary,
    _extract_budget,
    _extract_days,
    _extract_destination,
    get_llm_service_error_status,
)
from app.agent.orchestrator import PlanningOrchestrator
from app.agent.prompts import render_system_prompt
from app.agent.state import AgentState
from app.config import get_settings
from app.models.schemas import ChatRequest
from app.services.cache import get_redis_client
from app.services.demo_itinerary import build_demo_itinerary
from app.services.session import get_session, save_session
from app.tools.poi_search import poi_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
CHAT_RATE_LIMIT_MAX_REQUESTS = 10
CHAT_RATE_LIMIT_WINDOW_SECONDS = 60.0
MAX_SESSION_MESSAGES = 20
CHINESE_WEEKDAY_OFFSETS = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
}
CHINESE_DAY_RE = re.compile(r"[一二两三四五六七八九十]{1,3}\s*(?:天|日)")
DIGIT_DAY_RE = re.compile(r"\d{1,2}\s*(?:天|日)")
WEEK_DURATION_RE = re.compile(r"(?:1|一|一个)\s*(?:周|星期|礼拜)")
DESTINATION_RE = re.compile(
    r"(?:去|到|目的地[: ]*)(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12})"
)
DESTINATION_WITH_DAYS_RE = re.compile(
    r"(?:^|[\u3002\uff01\uff1f\uff0c,\.!\?\s])"
    r"(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12})"
    r"(?:\d{1,2}|[一二两三四五六七八九十]{1,3})\s*天"
)
DESTINATION_CONTEXT_RE = re.compile(
    r"(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12}?)"
    r"(?:情侣|亲子|老人|国庆|春节|五一|暑假|旅行|旅游|行程|游)"
)
REPLAN_DESTINATION_RE = re.compile(
    r"(?:换成|改成|替换为|换到|改去|再生成|再给我|给我生成|来一份)"
    r"(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12}?)"
    r"(?:的)?(?:\d{1,2}|[一二两三四五六七八九十]{1,3})\s*(?:天|日)"
)
NO_SELF_DRIVE_KEYWORDS = (
    "不会开车",
    "不开车",
    "不自驾",
    "不租车",
    "不能开车",
    "不会自驾",
)
NEARBY_STAY_KEYWORDS = ("附近住", "住附近", "就近住", "附近住宿", "哪里玩就")
REPLACE_ACTIVITY_KEYWORDS = ("换一个", "换个", "换一家", "换成", "替换", "改成")
REPLAN_ITINERARY_KEYWORDS = (
    "不去",
    "不要",
    "换成",
    "改成",
    "重新生成",
    "重新规划",
    "重新做",
    "新行程",
    "另一份",
    "另外一份",
    "再生成",
    "再给我",
    "给我生成",
    "来一份",
)
SCENIC_REPLACEMENT_KEYWORDS = (
    "风景",
    "看景",
    "观景",
    "江景",
    "河景",
    "湖景",
    "日落",
    "夜景",
    "露台",
    "窗边",
)
RESTFUL_REPLACEMENT_KEYWORDS = ("坐着", "坐下", "休息", "不累", "轻松", "慢一点")
SUPPORTED_KNOWLEDGE_AREAS = ("北京", "上海", "成都", "贵州", "贵阳")
RAG_SOURCE_RE = re.compile(r"\brag_search\b|RAG\s*(?:推荐|检索)?|本地知识库", re.I)
_RATE_LIMIT_BUCKET: dict[str, list[float]] = {}


def _generation_source(
    kind: str,
    label: str,
    detail: str,
    *,
    tools: list[str] | None = None,
    is_fallback: bool = False,
) -> dict[str, Any]:
    """Build a serializable generation source payload for SSE and itinerary."""
    return {
        "kind": kind,
        "label": label,
        "detail": detail,
        "tools": tools or [],
        "is_fallback": is_fallback,
    }


def _attach_generation_source(
    itinerary: dict[str, Any] | None,
    source: dict[str, Any],
) -> dict[str, Any] | None:
    """Attach generation source metadata to an itinerary dictionary."""
    if itinerary is None:
        return None

    itinerary["generation_source"] = source
    return itinerary


def _attach_trip_start_date(
    itinerary: dict[str, Any] | None,
    intent: TravelIntent | None,
    request_text: str,
) -> dict[str, Any] | None:
    """Attach the requested trip start date when it can be inferred."""
    if itinerary is None:
        return itinerary

    start_date = _extract_trip_start_date_text(request_text, intent)
    if start_date:
        itinerary["start_date"] = _normalize_trip_start_date(start_date)
    return itinerary


def _extract_trip_start_date_text(
    request_text: str,
    intent: TravelIntent | None,
) -> str | None:
    """Infer a trip start date phrase from intent or the user's original text."""
    normalized = re.sub(r"\s+", "", request_text)
    patterns = (
        r"\d{4}\s*[-/年]\s*\d{1,2}\s*[-/月]\s*\d{1,2}\s*(?:日|号)?",
        r"\d{1,2}\s*月\s*\d{1,2}\s*(?:日|号)?",
        r"下(?:周|星期|礼拜)[一二三四五六日天]?",
        r"今天|明天|后天|周末|星期末",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return match.group(0)

    if intent is not None and intent.start_date:
        return intent.start_date

    return None


def _normalize_trip_start_date(value: str, today: date | None = None) -> str:
    """Return an ISO date for common Chinese date phrases when possible."""
    normalized = re.sub(r"\s+", "", value)
    base_date = today or datetime.now().date()

    concrete_match = re.search(
        r"(?:(\d{4})\s*[-/年]\s*)?(\d{1,2})\s*(?:[-/月])\s*(\d{1,2})",
        normalized,
    )
    if concrete_match:
        year = int(concrete_match.group(1) or base_date.year)
        month = int(concrete_match.group(2))
        day = int(concrete_match.group(3))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return value

    if "今天" in normalized:
        return base_date.isoformat()
    if "明天" in normalized:
        return (base_date + timedelta(days=1)).isoformat()
    if "后天" in normalized:
        return (base_date + timedelta(days=2)).isoformat()

    next_weekday_match = re.search(
        r"下(?:周|星期|礼拜)([一二三四五六日天])", normalized
    )
    if next_weekday_match:
        monday = _next_monday(base_date)
        offset = CHINESE_WEEKDAY_OFFSETS[next_weekday_match.group(1)]
        return (monday + timedelta(days=offset)).isoformat()

    if "下周" in normalized:
        return _next_monday(base_date).isoformat()

    if "周末" in normalized or "星期末" in normalized:
        days_until_saturday = (5 - base_date.weekday()) % 7 or 7
        return (base_date + timedelta(days=days_until_saturday)).isoformat()

    return value


def _next_monday(today: date) -> date:
    days_until_next_monday = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_until_next_monday)


def _prepare_itinerary_for_output(
    itinerary: dict[str, Any] | None,
    source: dict[str, Any],
    intent: TravelIntent | None,
    request_text: str,
) -> dict[str, Any] | None:
    """Attach frontend-visible itinerary metadata in one place."""
    return _attach_trip_start_date(
        _attach_generation_source(itinerary, source),
        intent,
        request_text,
    )


def _agent_generation_source(
    *,
    knowledge_base_covered: bool,
    load_mcp_tools: bool,
) -> dict[str, Any]:
    """Return source metadata for the live Agent graph path."""
    tools = ["rag_search"] if knowledge_base_covered else []
    tools.extend(
        ["amap_mcp"] if load_mcp_tools else ["poi_search", "route_plan", "weather"]
    )

    rag_text = (
        "会使用本地 RAG 知识库检索目的地资料"
        if knowledge_base_covered
        else "本地 RAG 暂未覆盖该目的地"
    )
    map_text = (
        "并通过高德 MCP 工具补充 POI、路线和天气证据"
        if load_mcp_tools
        else "并通过 HTTP 地图、路线和天气工具补充证据"
    )

    return _generation_source(
        "agent_graph",
        "真实 Agent 工具链",
        f"{rag_text}, {map_text}; 具体调用会通过 tool_call/tool_result 事件展示。",
        tools=tools,
    )


async def _enforce_chat_rate_limit(session_id: str) -> None:
    """Apply rate limiting per chat session, preferring Redis for consistency."""
    try:
        await _enforce_redis_chat_rate_limit(session_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Redis chat rate limit failed, using memory fallback: %s", exc)
        _enforce_memory_chat_rate_limit(session_id)


async def _enforce_redis_chat_rate_limit(session_id: str) -> None:
    """Apply an atomic Redis counter limit for the current window."""
    redis_client = get_redis_client()
    key = f"rate_limit:chat:{session_id}"
    request_count = await redis_client.incr(key)
    if request_count == 1:
        await redis_client.expire(key, int(CHAT_RATE_LIMIT_WINDOW_SECONDS))

    if request_count > CHAT_RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many chat requests. Please try again shortly.",
        )


def _enforce_memory_chat_rate_limit(session_id: str) -> None:
    """Apply a best-effort in-process fallback rate limit per chat session."""
    now = time.monotonic()
    window_start = now - CHAT_RATE_LIMIT_WINDOW_SECONDS
    recent_requests = [
        request_time
        for request_time in _RATE_LIMIT_BUCKET.get(session_id, [])
        if request_time >= window_start
    ]

    if len(recent_requests) >= CHAT_RATE_LIMIT_MAX_REQUESTS:
        _RATE_LIMIT_BUCKET[session_id] = recent_requests
        raise HTTPException(
            status_code=429,
            detail="Too many chat requests. Please try again shortly.",
        )

    recent_requests.append(now)
    _RATE_LIMIT_BUCKET[session_id] = recent_requests


def _message_text(message: BaseMessage) -> str:
    """Normalize LangChain message content into plain text."""
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return str(content)


def _sse(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_error_message(exc: BaseException) -> str:
    """Map runtime exceptions to a user-facing SSE error message."""
    status_code = get_llm_service_error_status(exc)
    if status_code in {401, 403}:
        return (
            "模型服务鉴权失败: DEEPSEEK_API_KEY 无效或已过期。"
            "请更新 backend/.env 后重启后端, 再重新生成行程。"
        )
    if status_code == 429:
        return "模型服务请求过于频繁或额度不足, 请稍后重试或检查服务额度。"
    if status_code == 400:
        return "模型服务拒绝了本次请求, 请检查模型配置、接口地址或思考模式参数。"
    if status_code is not None and status_code >= 500:
        return "模型服务当前不可用, 请稍后重试。"

    if "DEEPSEEK_API_KEY is not configured" in str(exc):
        return "模型服务未配置: 请在 backend/.env 中设置 DEEPSEEK_API_KEY 后重启后端。"

    return "对话服务暂时不可用, 请稍后重试。"


def _tool_call_events(message: AIMessage) -> list[tuple[str, dict[str, Any]]]:
    """Convert AI tool calls into SSE tool_call events."""
    events: list[tuple[str, dict[str, Any]]] = []
    for tool_call in message.tool_calls:
        events.append(
            (
                "tool_call",
                {
                    "tool": tool_call.get("name", ""),
                    "args": tool_call.get("args", {}),
                },
            )
        )
    return events


def _tool_result_event(message: ToolMessage) -> tuple[str, dict[str, Any]]:
    """Convert a ToolMessage into an SSE tool_result event."""
    return (
        "tool_result",
        {
            "tool": message.name or "",
            "result": _message_text(message),
        },
    )


ITINERARY_TAG_RE = re.compile(
    r"<itinerary_json>\s*(?P<json>.*?)\s*</itinerary_json>",
    re.DOTALL,
)
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(?P<json>\{.*?\})\s*```", re.DOTALL)


def _find_itinerary_dict(value: Any) -> dict[str, Any] | None:
    """Find an itinerary-shaped dictionary inside parsed JSON."""
    if not isinstance(value, dict):
        return None

    itinerary = value.get("itinerary")
    if isinstance(itinerary, dict):
        nested = _find_itinerary_dict(itinerary)
        return nested or itinerary

    if isinstance(value.get("days"), list):
        return value

    for child in value.values():
        found = _find_itinerary_dict(child)
        if found is not None:
            return found

    return None


def _parse_itinerary_json(raw_json: str) -> dict[str, Any] | None:
    """Parse a JSON string and return an itinerary-shaped dictionary."""
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    itinerary = _find_itinerary_dict(parsed)
    return _sanitize_itinerary_confidence(itinerary)


def _sanitize_itinerary_confidence(
    itinerary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Downgrade unsupported RAG provenance so it is not shown as trusted."""
    if itinerary is None:
        return None

    destination = itinerary.get("destination")
    knowledge_base_covered = (
        _knowledge_base_covers_destination(destination)
        if isinstance(destination, str)
        else False
    )

    days = itinerary.get("days")
    if not isinstance(days, list):
        return itinerary

    for day in days:
        if not isinstance(day, dict):
            continue
        activities = day.get("activities")
        if not isinstance(activities, list):
            continue
        for activity in activities:
            if isinstance(activity, dict):
                _sanitize_activity_confidence(
                    activity,
                    knowledge_base_covered=knowledge_base_covered,
                )

    return itinerary


def _sanitize_activity_confidence(
    activity: dict[str, Any],
    *,
    knowledge_base_covered: bool,
) -> None:
    """Mark raw RAG references outside local KB coverage as untrusted."""
    source = str(activity.get("source") or "")
    refs = activity.get("source_refs")
    ref_values = [str(ref) for ref in refs if ref] if isinstance(refs, list) else []
    source_text = " ".join([source, *ref_values])
    if knowledge_base_covered:
        _remove_warning(activity, "知识库未覆盖")
        return

    if not source_text or not RAG_SOURCE_RE.search(source_text):
        return

    if any(area in source_text for area in SUPPORTED_KNOWLEDGE_AREAS):
        _remove_warning(activity, "知识库未覆盖")
        return

    if not re.search(r"高德|amap|poi|用户指定", source, re.I):
        activity["source"] = "来源待确认"
        activity["is_verified"] = False

    warnings = activity.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    if "知识库未覆盖" not in warnings:
        warnings.append("知识库未覆盖")
    activity["warnings"] = warnings


def _remove_warning(activity: dict[str, Any], warning: str) -> None:
    warnings = activity.get("warnings")
    if not isinstance(warnings, list):
        return

    activity["warnings"] = [item for item in warnings if item != warning]


def _extract_tagged_or_fenced_itinerary(text: str) -> tuple[str, dict[str, Any] | None]:
    """Extract tagged/fenced itinerary JSON from assistant text."""
    tag_match = ITINERARY_TAG_RE.search(text)
    if tag_match:
        cleaned = f"{text[: tag_match.start()]}\n{text[tag_match.end() :]}".strip()
        return cleaned, _parse_itinerary_json(tag_match.group("json"))

    open_tag_index = text.find("<itinerary_json>")
    if open_tag_index >= 0:
        return text[:open_tag_index].strip(), None

    fence_match = JSON_FENCE_RE.search(text)
    if fence_match:
        itinerary = _parse_itinerary_json(fence_match.group("json"))
        if itinerary is not None:
            cleaned = (
                f"{text[: fence_match.start()]}\n{text[fence_match.end() :]}".strip()
            )
            return cleaned, itinerary

    return text, None


def _extract_inline_itinerary(text: str) -> dict[str, Any] | None:
    """Best-effort extraction for JSON embedded directly in assistant text."""
    decoder = json.JSONDecoder()
    index = 0
    while index < len(text):
        brace_index = text.find("{", index)
        if brace_index < 0:
            return None

        try:
            parsed, end_index = decoder.raw_decode(text[brace_index:])
        except json.JSONDecodeError:
            index = brace_index + 1
            continue

        itinerary = _find_itinerary_dict(parsed)
        if itinerary is not None:
            return _sanitize_itinerary_confidence(itinerary)

        index = brace_index + max(end_index, 1)

    return None


def _split_content_and_itinerary(text: str) -> tuple[str, dict[str, Any] | None]:
    """Split assistant text into visible content and optional itinerary JSON."""
    cleaned, itinerary = _extract_tagged_or_fenced_itinerary(text)
    if itinerary is not None or cleaned != text:
        return cleaned, itinerary

    return text, _extract_inline_itinerary(text)


def _demo_mode_enabled() -> bool:
    """Return whether deterministic demo itineraries may short-circuit chat."""
    return get_settings().demo_mode


def _demo_fallback_enabled() -> bool:
    """Return whether known demo prompts may use local resilient fallbacks."""
    settings = get_settings()
    return settings.demo_mode or settings.demo_fallback_enabled


def _amap_mcp_enabled() -> bool:
    """Return whether chat should load optional AMap MCP tools."""
    return get_settings().enable_amap_mcp


def _knowledge_base_covers_destination(destination: str | None) -> bool:
    """Return whether the local RAG corpus covers the destination."""
    if not destination:
        return False

    return any(
        area in destination or destination in area for area in SUPPORTED_KNOWLEDGE_AREAS
    )


def _request_knowledge_base_covered(
    message: str,
    user_profile: dict[str, Any] | None,
    current_itinerary: dict[str, Any] | None,
) -> bool:
    """Infer whether this turn should be allowed to use local RAG."""
    extracted_destination = _extract_destination(message)
    if extracted_destination != "目的地待确认":
        return _knowledge_base_covers_destination(extracted_destination)

    profile_intent = intent_from_user_profile(user_profile)
    if profile_intent is not None and profile_intent.destination:
        return _knowledge_base_covers_destination(profile_intent.destination)

    profile_destination = user_profile.get("destination") if user_profile else None
    if isinstance(profile_destination, str):
        return _knowledge_base_covers_destination(profile_destination)

    itinerary_destination = (
        current_itinerary.get("destination") if current_itinerary else None
    )
    if isinstance(itinerary_destination, str):
        return _knowledge_base_covers_destination(itinerary_destination)

    return False


def _render_prompt_for_knowledge_strategy(
    *,
    current_itinerary: dict[str, Any] | None,
    knowledge_base_covered: bool,
    user_profile: dict[str, Any] | None,
) -> str:
    """Render the system prompt with a per-turn RAG/tool strategy."""
    prompt = render_system_prompt(
        user_profile=user_profile,
        current_itinerary=current_itinerary,
    )
    if knowledge_base_covered:
        return (
            f"{prompt}\n\n"
            "## 本轮知识库策略\n"
            "当前主要目的地在本地知识库覆盖范围内。生成新行程时, 可以先用 "
            "`rag_search` 获取规划背景、适合人群、预算和注意事项; 但具体地点的"
            "地址、坐标、评分仍必须用 `poi_search` 验证。"
        )

    return (
        f"{prompt}\n\n"
        "## 本轮知识库策略\n"
        "当前主要目的地不在本地知识库覆盖范围内。本轮不要调用或声称使用 "
        "`rag_search` / 本地知识库; 具体地点请用 `poi_search`, 转场用 "
        "`route_plan`, 天气用 `weather`。若无法验证, 请把 source 写为"
        "“来源待确认”, 并在 warnings 中加入“知识库未覆盖”。"
    )


def format_graph_event(event: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Map a LangGraph update event into public SSE events."""
    sse_events: list[tuple[str, dict[str, Any]]] = []
    for node_name, patch in event.items():
        if not isinstance(patch, dict):
            continue

        if node_name == "planner_node":
            sse_events.append(("thinking", {"step": "正在分析您的需求..."}))

        messages = patch.get("messages", [])
        if not isinstance(messages, list):
            messages = [messages]

        for message in messages:
            if isinstance(message, AIMessage):
                if message.tool_calls:
                    sse_events.extend(_tool_call_events(message))
                else:
                    text = _message_text(message)
                    if text:
                        content, itinerary = _split_content_and_itinerary(text)
                        if content:
                            sse_events.append(("content", {"text": content}))
                        if itinerary is not None:
                            sse_events.append(("itinerary", {"itinerary": itinerary}))
            elif isinstance(message, ToolMessage):
                sse_events.append(_tool_result_event(message))

        itinerary = patch.get("itinerary")
        if itinerary is not None:
            sanitized_itinerary = _sanitize_itinerary_confidence(
                _dict_or_none(itinerary)
            )
            if sanitized_itinerary is not None:
                sse_events.append(("itinerary", {"itinerary": sanitized_itinerary}))

    return sse_events


async def sse_generator(
    session_id: str,
    message: str,
    request_itinerary: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """Generate SSE events from the Agent graph stream."""
    yield _sse("thinking", {"step": "正在分析您的旅行需求..."})

    session_data = await _load_session(session_id)
    user_profile = _dict_or_none(session_data.get("user_profile"))
    current_itinerary = request_itinerary or _dict_or_none(
        session_data.get("itinerary")
    )
    session_messages = _session_messages(session_data.get("messages"))
    message_count = _int_value(session_data.get("message_count")) + 1
    assistant_content_parts: list[str] = []
    yielded_itinerary = False
    stream_failed = False
    demo_mode = _demo_mode_enabled()
    demo_fallback_enabled = _demo_fallback_enabled()
    travel_state = travel_state_from_user_profile(user_profile)
    replaced_itinerary = current_itinerary
    is_replacing_itinerary = False
    replacement_destination: str | None = None
    planning_message = _build_contextual_planning_message(
        message,
        session_messages,
        current_itinerary,
    )

    local_followup = await _build_local_followup_response(
        message,
        current_itinerary,
    )
    if local_followup is not None:
        travel_state = travel_state_with_stage(
            travel_state, "completed", confirmed=True
        )
        user_profile = user_profile_with_travel_state(user_profile, travel_state)
        source = _generation_source(
            "local_followup",
            "本地规则微调",
            "基于当前行程和用户偏好在后端本地规则中调整, 未重新运行完整 Agent 图。",
            tools=["current_itinerary"],
        )
        content_text, current_itinerary = local_followup
        current_itinerary = _prepare_itinerary_for_output(
            current_itinerary,
            source,
            travel_state.intent,
            planning_message,
        )
        session_messages = _append_session_turn(
            session_messages,
            user_content=message,
            assistant_content=content_text,
        )
        await _save_session(
            session_id=session_id,
            user_profile=user_profile,
            itinerary=current_itinerary,
            message_count=message_count,
            messages=session_messages,
        )
        yield _sse("thinking", {"step": "正在理解局部修改..."})
        yield _sse("thinking", {"step": "正在更新行程卡片..."})
        yield _sse("source", source)
        yield _sse("content", {"text": content_text})
        yield _sse("itinerary", {"itinerary": current_itinerary})
        yield _sse("done", {})
        return

    previous_intent = travel_state.intent
    travel_intent = await extract_travel_intent(planning_message, previous_intent)
    travel_state = update_travel_state(travel_state, message, travel_intent)
    user_profile = user_profile_with_travel_state(user_profile, travel_state)

    if _is_new_itinerary_request(message, travel_intent, current_itinerary):
        is_replacing_itinerary = True
        replacement_destination = _requested_itinerary_destination(
            message,
            travel_intent,
        )
        current_itinerary = None

    planning_message = _build_agent_planning_message(
        planning_message,
        travel_state.intent,
        is_replacing_itinerary=is_replacing_itinerary,
        has_session_context=bool(session_messages),
    )

    knowledge_base_covered = _request_knowledge_base_covered(
        planning_message,
        user_profile,
        current_itinerary,
    )

    clarification = _build_clarification_message(
        planning_message,
        current_itinerary,
        has_session_context=bool(session_messages),
        travel_state=travel_state if current_itinerary is None else None,
    )
    if clarification is not None:
        yield _sse(
            "source",
            _generation_source(
                "clarification",
                "需求补充提示",
                "当前输入缺少代码校验要求的关键字段, 后端未进入行程生成和工具调用。",
            ),
        )
        session_messages = _append_session_turn(
            session_messages,
            user_content=message,
            assistant_content=clarification,
        )
        await _save_session(
            session_id=session_id,
            user_profile=user_profile,
            itinerary=current_itinerary,
            message_count=message_count,
            messages=session_messages,
        )
        yield _sse("content", {"text": clarification})
        yield _sse("done", {})
        return

    demo_itinerary = (
        build_demo_itinerary(planning_message, current_itinerary)
        if demo_fallback_enabled
        else None
    )
    if current_itinerary is not None and demo_itinerary is not None:
        travel_state = travel_state_with_stage(
            travel_state, "completed", confirmed=True
        )
        user_profile = user_profile_with_travel_state(user_profile, travel_state)
        source = _generation_source(
            "demo_fallback",
            "演示兜底局部调整",
            "命中内置演示行程模板, 用于保证端到端演示稳定; 仍会在活动卡片中标注待确认信息。",
            tools=["demo_itinerary"],
            is_fallback=True,
        )
        current_itinerary = demo_itinerary
        current_itinerary = _prepare_itinerary_for_output(
            current_itinerary,
            source,
            travel_state.intent,
            planning_message,
        )
        content_text = "已按你的要求完成局部调整, 未提到的行程保持不变。"
        session_messages = _append_session_turn(
            session_messages,
            user_content=message,
            assistant_content=content_text,
        )
        await _save_session(
            session_id=session_id,
            user_profile=user_profile,
            itinerary=current_itinerary,
            message_count=message_count,
            messages=session_messages,
        )
        yield _sse("thinking", {"step": "正在根据已有行程进行局部微调..."})
        yield _sse("source", source)
        yield _sse("content", {"text": content_text})
        yield _sse("itinerary", {"itinerary": current_itinerary})
        yield _sse("done", {})
        return
    if current_itinerary is None and demo_itinerary is not None:
        travel_state = travel_state_with_stage(
            travel_state, "completed", confirmed=True
        )
        user_profile = user_profile_with_travel_state(user_profile, travel_state)
        source = _generation_source(
            "demo_fallback",
            "演示兜底行程",
            "命中内置演示行程模板, 用于保证端到端演示稳定; 适合公开 Demo 快速展示, 非完整实时工具链。",
            tools=["demo_itinerary"],
            is_fallback=True,
        )
        current_itinerary = demo_itinerary
        current_itinerary = _prepare_itinerary_for_output(
            current_itinerary,
            source,
            travel_state.intent,
            planning_message,
        )
        content_text = "已生成一版可执行行程, 右侧已同步行程卡片和地图标注。"
        if demo_mode:
            content_text = "已生成可用于端到端冒烟测试的演示行程。"
        session_messages = _append_session_turn(
            session_messages,
            user_content=message,
            assistant_content=content_text,
        )
        await _save_session(
            session_id=session_id,
            user_profile=user_profile,
            itinerary=current_itinerary,
            message_count=message_count,
            messages=session_messages,
        )
        thinking_text = "正在准备可执行兜底行程..."
        if demo_mode:
            thinking_text = "正在准备端到端演示行程..."
        yield _sse("thinking", {"step": thinking_text})
        yield _sse("source", source)
        yield _sse("content", {"text": content_text})
        yield _sse("itinerary", {"itinerary": current_itinerary})
        yield _sse("done", {})
        return

    initial_state: AgentState = {
        "messages": [
            SystemMessage(
                content=_render_prompt_for_knowledge_strategy(
                    user_profile=user_profile,
                    current_itinerary=current_itinerary,
                    knowledge_base_covered=knowledge_base_covered,
                )
            )
        ],
        "user_profile": user_profile,
        "itinerary": current_itinerary,
        "iteration_count": 0,
        "should_end": False,
    }
    initial_state["messages"].extend(
        _agent_context_messages(
            session_messages,
            is_replacing_itinerary=is_replacing_itinerary,
        )
    )
    initial_state["messages"].append(HumanMessage(content=planning_message))

    try:
        load_mcp_tools = _amap_mcp_enabled()
        source = _agent_generation_source(
            knowledge_base_covered=knowledge_base_covered,
            load_mcp_tools=load_mcp_tools,
        )
        yield _sse(
            "thinking",
            {
                "step": (
                    "正在连接高德 MCP 工具和知识库..."
                    if load_mcp_tools and knowledge_base_covered
                    else "本地知识库暂未覆盖该目的地, 正在准备地图、路线和天气工具..."
                    if not knowledge_base_covered
                    else "正在准备知识库和地图 HTTP 工具..."
                )
            },
        )
        yield _sse("source", source)
        orchestrator = PlanningOrchestrator(build_graph_func=build_graph)
        graph = await orchestrator.build_graph(
            travel_state,
            load_mcp_tools=load_mcp_tools,
            load_rag_tool=knowledge_base_covered,
        )
        travel_state = travel_state_with_stage(travel_state, "planning", confirmed=True)
        user_profile = user_profile_with_travel_state(user_profile, travel_state)
        initial_state["user_profile"] = user_profile
        logger.info(
            "Chat stream started",
            extra={"session_id": session_id, "message_count": message_count},
        )
        async for graph_event in graph.astream(
            initial_state,
            config={"metadata": {"session_id": session_id}},
        ):
            for event_type, data in format_graph_event(graph_event):
                if _is_stale_replacement_content(
                    event_type,
                    data,
                    is_replacing_itinerary=is_replacing_itinerary,
                ):
                    continue

                if event_type == "itinerary":
                    candidate_itinerary = _prepare_itinerary_for_output(
                        _sanitize_itinerary_confidence(
                            _dict_or_none(data.get("itinerary"))
                        ),
                        source,
                        travel_state.intent,
                        planning_message,
                    )
                    if _is_stale_replacement_itinerary(
                        candidate_itinerary,
                        replaced_itinerary,
                        replacement_destination,
                        is_replacing_itinerary=is_replacing_itinerary,
                    ):
                        continue

                    current_itinerary = candidate_itinerary
                    if current_itinerary is not None:
                        yielded_itinerary = True
                        yield _sse("itinerary", {"itinerary": current_itinerary})
                    continue

                yield _sse(event_type, data)
                if event_type == "content" and isinstance(data.get("text"), str):
                    assistant_content_parts.append(data["text"])
            extracted_itinerary = _extract_itinerary(graph_event, current_itinerary)
            candidate_itinerary = _prepare_itinerary_for_output(
                extracted_itinerary,
                source,
                travel_state.intent,
                planning_message,
            )
            if not _is_stale_replacement_itinerary(
                candidate_itinerary,
                replaced_itinerary,
                replacement_destination,
                is_replacing_itinerary=is_replacing_itinerary,
            ):
                current_itinerary = candidate_itinerary
    except Exception as exc:
        stream_failed = True
        logger.exception("Chat SSE stream failed: %s", exc)
        yield _sse("error", {"message": _stream_error_message(exc)})
    finally:
        if current_itinerary is None and demo_fallback_enabled:
            current_itinerary = build_demo_itinerary(planning_message)
            if current_itinerary is None and not stream_failed:
                current_itinerary = _build_conservative_fallback_itinerary(
                    planning_message,
                    travel_intent,
                )
            if current_itinerary is not None and not yielded_itinerary:
                source = _generation_source(
                    "conservative_fallback",
                    "保守兜底行程",
                    "外部 Agent 生成链路未返回可解析行程, 后端用保守规则生成一版可展示行程并标注待确认项。",
                    tools=["conservative_itinerary"],
                    is_fallback=True,
                )
                current_itinerary = _prepare_itinerary_for_output(
                    current_itinerary,
                    source,
                    travel_state.intent,
                    planning_message,
                )
                fallback_text = (
                    "外部生成链路没有返回可解析的行程卡片, "
                    "我先给出一版保守兜底行程并标注待确认项, "
                    "你可以继续要求我按预算、节奏或地点偏好微调。"
                )
                if demo_mode:
                    source = _generation_source(
                        "demo_fallback",
                        "演示兜底行程",
                        "外部服务响应不稳定时使用本地演示兜底, 用于保证公开 Demo 稳定。",
                        tools=["demo_itinerary"],
                        is_fallback=True,
                    )
                    current_itinerary = _prepare_itinerary_for_output(
                        current_itinerary,
                        source,
                        travel_state.intent,
                        planning_message,
                    )
                    fallback_text = "外部服务响应不稳定, 我先给出可演示的本地兜底行程。"
                assistant_content_parts.append(fallback_text)
                yield _sse("source", source)
                yield _sse("content", {"text": fallback_text})
                yield _sse("itinerary", {"itinerary": current_itinerary})
                yielded_itinerary = True

        if current_itinerary is not None:
            travel_state = travel_state_with_stage(
                travel_state,
                "completed",
                confirmed=True,
            )
        else:
            travel_state = RequirementValidator().apply(travel_state)
        user_profile = user_profile_with_travel_state(user_profile, travel_state)
        session_messages = _append_session_turn(
            session_messages,
            user_content=message,
            assistant_content="".join(assistant_content_parts),
        )
        await _save_session(
            session_id=session_id,
            user_profile=user_profile,
            itinerary=current_itinerary,
            message_count=message_count,
            messages=session_messages,
        )
        yield _sse("done", {})


@router.post("/chat")
async def chat_endpoint(request: ChatRequest) -> StreamingResponse:
    """Chat endpoint returning an SSE stream."""
    await _enforce_chat_rate_limit(request.session_id)
    return StreamingResponse(
        sse_generator(
            request.session_id,
            request.message,
            request.current_itinerary,
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    """Return value if it is a dictionary."""
    return value if isinstance(value, dict) else None


def _int_value(value: Any) -> int:
    """Convert a value to int, returning 0 on invalid input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _build_clarification_message(
    message: str,
    current_itinerary: dict[str, Any] | None,
    *,
    has_session_context: bool = False,
    travel_state: TravelState | None = None,
    intent: TravelIntent | None = None,
) -> str | None:
    """Ask for required planning fields before entering the costly Agent loop."""
    if current_itinerary is not None:
        return None

    if travel_state is None and has_session_context:
        return None

    if travel_state is not None:
        missing_fields = _intent_missing_field_labels(travel_state.intent)
        invalid_fields = travel_state.intent.invalid_fields
    elif intent is None:
        missing_fields = []
        invalid_fields = []
        if not _has_destination(message):
            missing_fields.append("目的地")
        if not _has_trip_days(message):
            missing_fields.append("出行天数")
    else:
        missing_fields = _intent_missing_field_labels(intent)
        invalid_fields = intent.invalid_fields

    if not missing_fields and not invalid_fields:
        return None

    if travel_state is not None:
        return ClarificationAgent().ask(travel_state)

    if missing_fields == ["出行天数"]:
        return (
            "我已经看到你的目的地、预算和偏好。还差一个关键信息: "
            "这次准备玩几天?\n\n"
            "你可以直接回复比如“4天3晚”或“国庆假期玩5天”, "
            "我再开始生成完整行程, 避免现在默认天数导致方案太薄。"
        )

    if missing_fields == ["目的地"]:
        return (
            "我还需要先确认目的地。请告诉我这次想去哪个城市或区域, "
            "以及准备玩几天; 预算和偏好也可以一起补充。"
        )

    return (
        "为了生成可执行行程, 我还需要确认目的地和出行天数。"
        "请按“目的地 + 几天 + 预算 + 偏好”的形式补充一下。"
    )


def _intent_missing_field_labels(intent: TravelIntent) -> list[str]:
    """Convert structured missing field ids to user-facing field names."""
    return RequirementValidator().field_labels(intent.missing_fields)


def _should_enforce_requirement_collection(
    session_messages: list[dict[str, str]],
    had_persisted_travel_state: bool,
) -> bool:
    """Return whether this turn should enforce TravelState requirements."""
    return (
        not session_messages
        or had_persisted_travel_state
        or _last_assistant_asked_for_requirements(session_messages)
    )


def _has_destination(message: str) -> bool:
    """Return whether a message contains a likely destination."""
    normalized_message = _strip_leading_date_words(message)
    if DESTINATION_WITH_DAYS_RE.search(normalized_message):
        return True

    if DESTINATION_RE.search(message):
        return True

    return bool(DESTINATION_CONTEXT_RE.search(normalized_message))


def _has_trip_days(message: str) -> bool:
    """Return whether a message contains an explicit trip length."""
    return bool(
        DIGIT_DAY_RE.search(message)
        or CHINESE_DAY_RE.search(message)
        or WEEK_DURATION_RE.search(message)
    )


def _strip_leading_date_words(message: str) -> str:
    """Remove leading month phrases so region+days can be detected."""
    return re.sub(r"\d{1,2}\s*月份?", "", message)


def _build_contextual_planning_message(
    message: str,
    session_messages: list[dict[str, str]],
    current_itinerary: dict[str, Any] | None,
) -> str:
    """Merge short day-only replies with the pending planning request."""
    if current_itinerary is not None or not _is_trip_days_answer(message):
        return message

    if not _last_assistant_asked_for_days(session_messages):
        return message

    previous_request = _latest_user_message(session_messages)
    if previous_request is None:
        return message

    return f"{previous_request.rstrip()}。补充确认出行天数: {message.strip()}。"


def _build_agent_planning_message(
    message: str,
    intent: TravelIntent | None,
    *,
    is_replacing_itinerary: bool,
    has_session_context: bool,
) -> str:
    """Add code-validated requirements so the Agent needn't infer from old history."""
    if has_session_context and not is_replacing_itinerary:
        return message

    if intent is None:
        return message

    fields: list[str] = []
    if intent.destination:
        fields.append(f"目的地: {intent.destination}")
    if intent.departure_city:
        fields.append(f"出发城市: {intent.departure_city}")
    start_date = _extract_trip_start_date_text(message, intent)
    if start_date:
        fields.append(f"出发日期: {_normalize_trip_start_date(start_date)}")
    if intent.days and intent.days > 0:
        fields.append(f"游玩天数: {intent.days}天")
    if intent.people and intent.people > 0:
        fields.append(f"出行人数: {intent.people}人")
    if intent.budget is not None and intent.budget > 0:
        fields.append(f"总预算: {int(intent.budget)}元")
    if intent.travel_style:
        fields.append(f"旅行风格: {intent.travel_style}")
    if intent.preferences:
        fields.append(f"偏好: {'、'.join(intent.preferences)}")
    if intent.constraints:
        fields.append(f"约束: {'、'.join(intent.constraints)}")

    if not fields:
        return message

    mode_note = (
        "这是一次全新目的地的完整行程规划。请不要沿用上一趟行程的地点、骨架或兜底说明。"
        if is_replacing_itinerary
        else "请以这些结构化需求为准生成本轮完整行程。"
    )
    field_text = "\n".join(f"- {field}" for field in fields)
    return (
        f"{message.strip()}\n\n"
        "后端已确认的本轮结构化需求如下:\n"
        f"{field_text}\n"
        f"{mode_note}"
    )


def _agent_context_messages(
    session_messages: list[dict[str, str]],
    *,
    is_replacing_itinerary: bool,
) -> list[BaseMessage]:
    """Return prior chat turns that are safe to inject into the Agent graph."""
    if is_replacing_itinerary:
        return []

    return _to_langchain_messages(session_messages)


def _is_new_itinerary_request(
    message: str,
    intent: TravelIntent | None,
    current_itinerary: dict[str, Any] | None,
) -> bool:
    """Return whether this turn should replace, not edit, the current itinerary."""
    if current_itinerary is None:
        return False

    requested_destination = _requested_itinerary_destination(message, intent)
    requested_destination = requested_destination.strip()
    current_destination = str(current_itinerary.get("destination") or "").strip()
    if requested_destination in {"", "目的地待确认"}:
        return False

    normalized = message.replace(" ", "")
    has_replan_keyword = any(
        keyword in normalized for keyword in REPLAN_ITINERARY_KEYWORDS
    )

    if current_destination and requested_destination != current_destination:
        return True

    return has_replan_keyword and _has_trip_days(message)


def _requested_itinerary_destination(
    message: str,
    intent: TravelIntent | None,
) -> str:
    """Return the best destination candidate for the current user turn."""
    return (
        _extract_replan_destination(message)
        or (intent.destination if intent else None)
        or _extract_destination(message)
    )


def _extract_replan_destination(message: str) -> str | None:
    """Extract the destination from whole-itinerary replacement wording."""
    match = REPLAN_DESTINATION_RE.search(message.replace(" ", ""))
    if not match:
        return None

    destination = match.group("destination").strip("的")
    return destination or None


def _is_stale_replacement_content(
    event_type: str,
    data: dict[str, Any],
    *,
    is_replacing_itinerary: bool,
) -> bool:
    """Return whether fallback text would wrongly imply keeping the old trip."""
    if not is_replacing_itinerary or event_type != "content":
        return False

    text = data.get("text")
    return isinstance(text, str) and "保留并返回已有行程" in text


def _is_stale_replacement_itinerary(
    itinerary: dict[str, Any] | None,
    replaced_itinerary: dict[str, Any] | None,
    replacement_destination: str | None,
    *,
    is_replacing_itinerary: bool,
) -> bool:
    """Return whether an itinerary event is the old trip resurfacing."""
    if (
        not is_replacing_itinerary
        or itinerary is None
        or replaced_itinerary is None
        or not replacement_destination
    ):
        return False

    destination = str(itinerary.get("destination") or "").strip()
    old_destination = str(replaced_itinerary.get("destination") or "").strip()
    return bool(
        destination
        and old_destination
        and destination == old_destination
        and destination != replacement_destination
    )


def _is_trip_days_answer(message: str) -> bool:
    """Return whether the user likely only answered the missing trip length."""
    normalized = re.sub(r"\s+", "", message)
    if not normalized or len(normalized) > 20:
        return False
    if _has_destination(normalized):
        return False
    return _has_trip_days(normalized)


def _last_assistant_asked_for_days(
    session_messages: list[dict[str, str]],
) -> bool:
    """Return whether the last assistant turn was a missing-days clarification."""
    for item in reversed(session_messages):
        if item.get("role") != "assistant":
            continue
        content = item.get("content", "")
        return "准备玩几天" in content or "出行天数" in content
    return False


def _last_assistant_asked_for_requirements(
    session_messages: list[dict[str, str]],
) -> bool:
    """Return whether the last assistant turn asked for structured requirements."""
    for item in reversed(session_messages):
        if item.get("role") != "assistant":
            continue
        content = item.get("content", "")
        return (
            "还需要确认" in content
            or "不会重新开始收集" in content
            or _last_assistant_asked_for_days(session_messages)
        )
    return False


def _latest_user_message(session_messages: list[dict[str, str]]) -> str | None:
    """Return the latest user message retained in the session."""
    for item in reversed(session_messages):
        if item.get("role") == "user":
            content = item.get("content", "").strip()
            if content:
                return content
    return None


def _build_conservative_fallback_itinerary(
    message: str,
    intent: TravelIntent | None = None,
) -> dict[str, Any] | None:
    """Build a visible conservative itinerary when the model omits JSON."""
    if intent is not None and intent.destination and intent.days and intent.days > 0:
        itinerary = _build_conservative_itinerary(
            destination=intent.destination,
            days=intent.days,
            budget=(
                int(intent.budget)
                if intent.budget is not None and intent.budget > 0
                else None
            ),
            user_message=message,
        )
        for day in itinerary.get("days", []):
            activities = day.get("activities") if isinstance(day, dict) else None
            if not isinstance(activities, list):
                continue
            for activity in activities:
                if not isinstance(activity, dict):
                    continue
                activity.setdefault("source", "本地保守兜底, 待工具复核")
                activity.setdefault("is_verified", False)
                activity.setdefault(
                    "warnings",
                    ["坐标待确认", "评分待确认", "到达路线待确认", "来源待确认"],
                )
        return itinerary

    if not (_has_destination(message) and _has_trip_days(message)):
        return None

    destination = _extract_destination(message)
    if destination == "目的地待确认":
        return None

    itinerary = _build_conservative_itinerary(
        destination=destination,
        days=_extract_days(message),
        budget=_extract_budget(message),
        user_message=message,
    )
    for day in itinerary.get("days", []):
        activities = day.get("activities") if isinstance(day, dict) else None
        if not isinstance(activities, list):
            continue
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            activity.setdefault("source", "本地保守兜底, 待工具复核")
            activity.setdefault("is_verified", False)
            activity.setdefault(
                "warnings",
                ["坐标待确认", "评分待确认", "到达路线待确认", "来源待确认"],
            )
    return itinerary


async def _build_local_followup_response(
    message: str,
    current_itinerary: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]] | None:
    """Handle low-risk itinerary preference edits without another tool loop."""
    if current_itinerary is None:
        return None

    quick_adjust = await _build_local_quick_adjust_response(
        message,
        current_itinerary,
    )
    if quick_adjust is not None:
        return quick_adjust

    normalized = message.replace(" ", "")
    wants_no_self_drive = any(
        keyword in normalized for keyword in NO_SELF_DRIVE_KEYWORDS
    )
    wants_nearby_stay = any(keyword in normalized for keyword in NEARBY_STAY_KEYWORDS)
    if not (wants_no_self_drive or wants_nearby_stay):
        return None

    itinerary = deepcopy(current_itinerary)
    days = itinerary.get("days")
    if not isinstance(days, list):
        return None

    for day in days:
        if not isinstance(day, dict):
            continue
        activities = day.get("activities")
        if not isinstance(activities, list):
            continue

        anchor = _find_day_stay_anchor(activities)
        for activity in activities:
            if not isinstance(activity, dict):
                continue
            _apply_no_self_drive_transport(activity)
            if wants_nearby_stay and activity.get("place_type") == "住宿":
                _move_lodging_near_anchor(activity, anchor)

    itinerary["summary"] = _append_summary_note(
        itinerary.get("summary"),
        "已按不自驾和就近住宿偏好调整, 优先使用公共交通、网约车、接驳车和景区附近住宿。",
    )
    content = (
        "已根据你的补充把方案调整为不自驾版本: 城市内优先公共交通/网约车, "
        "景区之间优先接驳车或包车服务; 住宿改为尽量靠近当天主要游玩区域。"
        "这样会比固定住一个地方更少折返, 也更适合不会开车的行程。"
    )
    return content, itinerary


async def _build_local_quick_adjust_response(
    message: str,
    current_itinerary: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    """Handle anchored quick-adjust button requests without a full Agent loop."""
    target = _find_target_activity(message, current_itinerary)
    if target is None:
        return None

    itinerary = deepcopy(current_itinerary)
    copied_target = _find_target_activity(message, itinerary)
    if copied_target is None:
        return None

    day, activities, activity_index, activity = copied_target
    normalized = message.replace(" ", "")
    day_number = day.get("day", "?")
    place_name = str(activity.get("place_name") or "目标活动")

    if any(keyword in normalized for keyword in ("加休息", "增加休息", "休息时间")):
        _insert_rest_activity(activities, activity_index, activity)
        itinerary["summary"] = _append_summary_note(
            itinerary.get("summary"),
            f"已在第 {day_number} 天 {place_name} 前后增加休息缓冲。",
        )
        return (
            f"已快速更新: 在第 {day_number} 天「{place_name}」前后增加休息缓冲, "
            "未提到的日期和活动保持不变。",
            _recalculate_total_cost(itinerary),
        )

    if any(keyword in normalized for keyword in ("降预算", "降低预算", "费用更低")):
        original_cost = _number_value(activity.get("cost"))
        reduced_cost = max(0, int(original_cost * 0.8))
        activity["cost"] = reduced_cost
        activity["description"] = _append_summary_note(
            activity.get("description"),
            "已按降预算偏好压低该活动的费用估算。",
        )
        itinerary["summary"] = _append_summary_note(
            itinerary.get("summary"),
            f"已降低第 {day_number} 天 {place_name} 的费用估算。",
        )
        return (
            f"已快速更新: 将第 {day_number} 天「{place_name}」的预算从 "
            f"{int(original_cost)} 元下调到 {reduced_cost} 元, 其余行程保持不变。",
            _recalculate_total_cost(itinerary),
        )

    if any(keyword in normalized for keyword in ("少走路", "减少步行", "步行更少")):
        _reduce_walking_for_activity(activity)
        itinerary["summary"] = _append_summary_note(
            itinerary.get("summary"),
            f"已按少走路偏好优化第 {day_number} 天 {place_name} 的到达方式。",
        )
        return (
            f"已快速更新: 第 {day_number} 天「{place_name}」优先改为少步行的到达方式, "
            "具体车程和费用建议出发前再确认。",
            _recalculate_total_cost(itinerary),
        )

    if any(keyword in normalized for keyword in REPLACE_ACTIVITY_KEYWORDS):
        poi_result, poi_keyword, poi_error = await _search_replacement_poi(
            itinerary,
            activity,
            message,
        )
        if poi_result is not None:
            replacement_name = _replace_activity_with_poi_result(
                activity,
                message,
                poi_result,
                poi_keyword,
            )
            itinerary["summary"] = _append_summary_note(
                itinerary.get("summary"),
                f"已重新查询 POI 并将第 {day_number} 天 {place_name} 替换为 {replacement_name}。",
            )
            return (
                f"已重新查询并替换: 将第 {day_number} 天「{place_name}」改为"
                f"「{replacement_name}」。地点信息来自高德 POI 查询, "
                "其余日期和未提到的活动保持不变; 替换后的到达路线建议出发前再复核。",
                _recalculate_total_cost(itinerary),
            )

        replacement_name = _replace_activity_with_pending_candidate(
            itinerary,
            activity,
            message,
            poi_error,
        )
        itinerary["summary"] = _append_summary_note(
            itinerary.get("summary"),
            f"POI 查询暂未返回可用结果, 已将第 {day_number} 天 {place_name} 调整为待复核备选 {replacement_name}。",
        )
        content = (
            f"我尝试重新查询 POI, 但暂时没有拿到可用真实地点"
            f"{f'({poi_error})' if poi_error else ''}。"
            f"已先将第 {day_number} 天「{place_name}」改为「{replacement_name}」并标注待复核, "
            "其余日期和未提到的活动保持不变。"
        )
        return content, _recalculate_total_cost(itinerary)

    return None


def _find_target_activity(
    message: str,
    itinerary: dict[str, Any],
) -> tuple[dict[str, Any], list[Any], int, dict[str, Any]] | None:
    """Find the activity explicitly mentioned by a quick-adjust prompt."""
    days = itinerary.get("days")
    if not isinstance(days, list):
        return None

    requested_day = _extract_requested_day(message)
    for day in days:
        if not isinstance(day, dict):
            continue
        day_number = _int_value(day.get("day"))
        if requested_day is not None and day_number != requested_day:
            continue

        activities = day.get("activities")
        if not isinstance(activities, list):
            continue

        for index, activity in enumerate(activities):
            if not isinstance(activity, dict):
                continue
            place_name = activity.get("place_name")
            if not isinstance(place_name, str) or place_name not in message:
                continue
            time_slot = activity.get("time_slot")
            if isinstance(time_slot, str) and time_slot in message:
                return day, activities, index, activity
            if requested_day is not None:
                return day, activities, index, activity

    return None


def _extract_requested_day(message: str) -> int | None:
    digit_match = re.search(r"第\s*(?P<day>\d{1,2})\s*天", message)
    if digit_match:
        return int(digit_match.group("day"))

    chinese_match = re.search(r"第\s*(?P<day>[一二两三四五六七八九十])\s*天", message)
    if chinese_match:
        mapping = {
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }
        return mapping.get(chinese_match.group("day"))

    return None


async def _search_replacement_poi(
    itinerary: dict[str, Any],
    activity: dict[str, Any],
    message: str,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Search a real replacement POI for an anchored activity."""
    city = _replacement_search_city(itinerary, activity)
    if not city:
        return None, None, "缺少可用于 POI 查询的城市"

    last_error: str | None = None
    original_name = str(activity.get("place_name") or "")
    for keyword in _replacement_search_keywords(activity, message):
        try:
            results = await poi_search.ainvoke(
                {"city": city, "keyword": keyword, "top_k": 8}
            )
        except Exception as exc:
            logger.warning(
                "Replacement POI search failed city=%s keyword=%s: %s",
                city,
                keyword,
                exc,
            )
            last_error = str(exc)
            continue

        if not isinstance(results, list):
            last_error = "POI 查询返回格式异常"
            continue

        error_result = next(
            (
                str(item.get("error"))
                for item in results
                if isinstance(item, dict) and item.get("error")
            ),
            None,
        )
        if error_result:
            last_error = error_result
            continue

        candidate = _select_replacement_poi(results, original_name)
        if candidate is not None:
            return candidate, keyword, None

        last_error = "POI 查询没有返回可替换的有效地点"

    return None, None, last_error


def _replacement_search_city(
    itinerary: dict[str, Any],
    activity: dict[str, Any],
) -> str:
    destination = str(itinerary.get("destination") or "").strip()
    if destination:
        return destination

    address = str(activity.get("address") or "").strip()
    city_match = re.search(r"(?P<city>[\u4e00-\u9fff]{2,8}市)", address)
    if city_match:
        return city_match.group("city")

    return ""


def _replacement_search_keywords(
    activity: dict[str, Any],
    message: str,
) -> list[str]:
    normalized = message.replace(" ", "")
    place_type = str(activity.get("place_type") or "")
    description = str(activity.get("description") or "")
    has_scenic_preference = any(
        keyword in normalized for keyword in SCENIC_REPLACEMENT_KEYWORDS
    )
    has_restful_preference = any(
        keyword in normalized for keyword in RESTFUL_REPLACEMENT_KEYWORDS
    )

    if place_type == "餐厅":
        keywords: list[str] = []
        if has_scenic_preference:
            keywords.extend(["观景餐厅", "江景餐厅", "露台餐厅"])
        if has_restful_preference:
            keywords.append("休闲餐厅")
        if "川菜" in description or "川菜" in normalized:
            keywords.append("川菜餐厅")
        keywords.append("餐厅")
        return _dedupe_strings(keywords)

    if place_type == "景点":
        keywords = []
        if has_scenic_preference:
            keywords.extend(["观景景点", "自然风光景点", "公园"])
        if has_restful_preference:
            keywords.append("休闲景点")
        keywords.append("景点")
        return _dedupe_strings(keywords)

    if place_type == "住宿":
        return ["酒店", "民宿", "住宿"]

    if place_type == "交通":
        return ["交通枢纽"]

    return _dedupe_strings([place_type, "旅游"])


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _select_replacement_poi(
    results: list[Any],
    original_name: str,
) -> dict[str, Any] | None:
    normalized_original = _normalize_place_name(original_name)
    for item in results:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        normalized_name = _normalize_place_name(name)
        if normalized_name and (
            normalized_name == normalized_original
            or normalized_name in normalized_original
            or normalized_original in normalized_name
        ):
            continue

        lng = _optional_number_value(item.get("lng"))
        lat = _optional_number_value(item.get("lat"))
        if not _valid_lng_lat(lng, lat):
            continue

        return item

    return None


def _replace_activity_with_poi_result(
    activity: dict[str, Any],
    message: str,
    poi: dict[str, Any],
    keyword: str | None,
) -> str:
    original_name = str(activity.get("place_name") or "原活动")
    original_place_type = str(activity.get("place_type") or "其他")
    replacement_name = str(poi.get("name") or "").strip()
    lng = _optional_number_value(poi.get("lng"))
    lat = _optional_number_value(poi.get("lat"))
    rating = _optional_number_value(poi.get("rating"))

    activity["place_name"] = replacement_name
    activity["place_type"] = _normalize_replacement_place_type(
        original_place_type,
        poi,
    )
    activity["lng"] = lng
    activity["lat"] = lat
    activity["address"] = str(poi.get("address") or "地址待确认")
    activity["description"] = _build_verified_replacement_description(
        original_name,
        replacement_name,
        original_place_type,
        message,
    )
    activity["source"] = "高德 POI 查询"
    source_refs = [f"POI: {replacement_name}"]
    if keyword:
        source_refs.append(f"搜索关键词: {keyword}")
    activity["source_refs"] = source_refs
    activity["is_verified"] = True
    if rating is not None and rating > 0:
        activity["rating"] = rating
    else:
        activity.pop("rating", None)

    warnings: list[str] = ["到达路线待确认"]
    if rating is None or rating <= 0:
        warnings.append("评分待确认")
    activity["warnings"] = warnings

    transport = activity.get("transport")
    if isinstance(transport, dict):
        transport["mode"] = "未知"
        transport["distance_km"] = 0
        transport["duration_min"] = 0
        transport["description"] = (
            "替换地点已通过 POI 查询确认, 但需要重新规划到达路线。"
        )

    return replacement_name


def _normalize_replacement_place_type(
    fallback_type: str,
    poi: dict[str, Any],
) -> str:
    poi_type = str(poi.get("type") or "")
    if "餐饮" in poi_type or "餐厅" in poi_type or "饭店" in poi_type:
        return "餐厅"
    if "风景" in poi_type or "景点" in poi_type or "公园" in poi_type:
        return "景点"
    if "酒店" in poi_type or "住宿" in poi_type or "宾馆" in poi_type:
        return "住宿"
    if "交通" in poi_type or "车站" in poi_type or "机场" in poi_type:
        return "交通"
    if fallback_type in {"景点", "餐厅", "住宿", "交通", "其他"}:
        return fallback_type
    return "其他"


def _build_verified_replacement_description(
    original_name: str,
    replacement_name: str,
    place_type: str,
    message: str,
) -> str:
    normalized = message.replace(" ", "")
    preference_notes: list[str] = []
    if any(keyword in normalized for keyword in SCENIC_REPLACEMENT_KEYWORDS):
        preference_notes.append("更贴近看风景的偏好")
    if any(keyword in normalized for keyword in RESTFUL_REPLACEMENT_KEYWORDS):
        preference_notes.append("更适合坐下休息、放慢节奏")
    if any(keyword in normalized for keyword in ("更近", "距离近", "少走路", "转场少")):
        preference_notes.append("优先减少转场和步行压力")
    preference_text = ", ".join(preference_notes) or f"保持{place_type}类型相近"
    return (
        f"已根据局部微调要求, 通过 POI 查询将原{place_type}「{original_name}」"
        f"替换为「{replacement_name}」。调整方向: {preference_text}。"
        "替换后的具体到达路线建议出发前再复核。"
    )


def _normalize_place_name(value: str) -> str:
    return re.sub("[\\s\\uFF08\\uFF09()「」【】\\\\-]", "", value).lower()


def _optional_number_value(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _valid_lng_lat(lng: float | None, lat: float | None) -> bool:
    return (
        isinstance(lng, int | float)
        and isinstance(lat, int | float)
        and -180 <= lng <= 180
        and -90 <= lat <= 90
        and not (lng == 0 and lat == 0)
    )


def _replace_activity_with_pending_candidate(
    itinerary: dict[str, Any],
    activity: dict[str, Any],
    message: str,
    poi_error: str | None = None,
) -> str:
    """Replace an anchored activity immediately while marking it for POI review."""
    original_name = str(activity.get("place_name") or "原活动")
    place_type = str(activity.get("place_type") or "其他")
    destination = str(itinerary.get("destination") or "").strip()
    replacement_name = _build_replacement_place_name(
        destination,
        original_name,
        place_type,
        message,
    )
    original_cost = int(_number_value(activity.get("cost")))

    activity["place_name"] = replacement_name
    activity["description"] = _build_replacement_description(
        original_name,
        place_type,
        message,
    )
    activity["cost"] = original_cost
    activity["address"] = "待根据实时 POI 查询确认"
    activity["lng"] = 0
    activity["lat"] = 0
    activity["source"] = "用户局部微调, POI 待复核"
    activity["source_refs"] = [original_name]
    activity["is_verified"] = False
    activity.pop("rating", None)

    warnings = [
        "替换地点待 POI 复核",
        "坐标待确认",
        "到达路线待确认",
        "来源待确认",
    ]
    if poi_error:
        warnings.append(f"POI 查询失败: {poi_error}")
    for warning in warnings:
        _add_warning(activity, warning)

    transport = activity.get("transport")
    if isinstance(transport, dict):
        transport["mode"] = "未知"
        transport["distance_km"] = 0
        transport["duration_min"] = 0
        transport["description"] = (
            "替换地点确认后需要重新规划到达路线, 当前先保留局部微调意图。"
        )

    return replacement_name


def _build_replacement_place_name(
    destination: str,
    original_name: str,
    place_type: str,
    message: str,
) -> str:
    normalized = message.replace(" ", "")
    has_scenic_preference = any(
        keyword in normalized for keyword in SCENIC_REPLACEMENT_KEYWORDS
    )
    has_restful_preference = any(
        keyword in normalized for keyword in RESTFUL_REPLACEMENT_KEYWORDS
    )

    if place_type == "餐厅" and (has_scenic_preference or has_restful_preference):
        descriptor = "观景休闲餐厅备选"
    elif place_type == "餐厅":
        descriptor = "同类型餐厅备选"
    elif place_type == "景点" and has_scenic_preference:
        descriptor = "观景休闲景点备选"
    elif place_type == "景点":
        descriptor = "同类型景点备选"
    elif place_type == "住宿":
        descriptor = "同区域住宿备选"
    else:
        descriptor = f"同类型{place_type}备选"

    prefix = destination or f"{original_name}附近"
    return f"{prefix}{descriptor}(待确认)"


def _build_replacement_description(
    original_name: str,
    place_type: str,
    message: str,
) -> str:
    normalized = message.replace(" ", "")
    preference_notes: list[str] = []
    if any(keyword in normalized for keyword in SCENIC_REPLACEMENT_KEYWORDS):
        preference_notes.append("优先满足可看风景、临窗/露台或靠近公园水岸")
    if any(keyword in normalized for keyword in RESTFUL_REPLACEMENT_KEYWORDS):
        preference_notes.append("优先选择可以坐下休息、节奏更轻松")
    if any(keyword in normalized for keyword in ("更近", "距离近", "少走路", "转场少")):
        preference_notes.append("优先减少转场距离和步行时间")
    if any(keyword in normalized for keyword in ("便宜", "别太贵", "预算", "降预算")):
        preference_notes.append("优先控制费用")

    preference_text = "、".join(preference_notes) or f"保持{place_type}类型相近"
    return (
        f"根据局部微调要求, 已将原{place_type}「{original_name}」替换为待复核备选。"
        f"筛选方向: {preference_text}。正式出发前建议用地图或点评工具确认营业状态、"
        "具体位置、评分和到达路线。"
    )


def _insert_rest_activity(
    activities: list[Any],
    activity_index: int,
    anchor: dict[str, Any],
) -> None:
    rest_name = f"{anchor.get('place_name', '当前地点')}附近休息"
    if any(
        isinstance(item, dict) and item.get("place_name") == rest_name
        for item in activities
    ):
        return

    rest_activity: dict[str, Any] = {
        "time_slot": "活动后 30 分钟",
        "place_name": rest_name,
        "place_type": "其他",
        "lng": anchor.get("lng", 0),
        "lat": anchor.get("lat", 0),
        "description": "预留补水、休息和临时调整时间, 避免行程过于紧凑。",
        "cost": 0,
        "address": anchor.get("address"),
        "source": "用户微调",
        "source_refs": [str(anchor.get("place_name") or "当前活动")],
        "is_verified": False,
        "warnings": ["休息点可按现场状态调整"],
    }
    activities.insert(activity_index + 1, rest_activity)


def _reduce_walking_for_activity(activity: dict[str, Any]) -> None:
    transport = activity.get("transport")
    if not isinstance(transport, dict):
        activity["transport"] = {
            "mode": "打车",
            "distance_km": 0,
            "duration_min": 0,
            "description": "已按少走路偏好建议打车或接驳, 具体路线待出发前确认。",
        }
        _add_warning(activity, "到达路线待确认")
        return

    mode = str(transport.get("mode") or "")
    if mode in {"步行", "公交", "地铁", "未知"}:
        transport["mode"] = "打车"

    duration = _number_value(transport.get("duration_min"))
    if duration > 0:
        transport["duration_min"] = max(5, int(duration * 0.65))

    description = str(transport.get("description") or "")
    transport["description"] = _append_summary_note(
        description,
        "已按少走路偏好优先选择打车、接驳或更短步行方案。",
    )
    _add_warning(activity, "费用和车程出发前复核")


def _recalculate_total_cost(itinerary: dict[str, Any]) -> dict[str, Any]:
    total = 0
    days = itinerary.get("days")
    if not isinstance(days, list):
        return itinerary

    for day in days:
        if not isinstance(day, dict):
            continue
        activities = day.get("activities")
        if not isinstance(activities, list):
            continue
        for activity in activities:
            if isinstance(activity, dict):
                total += int(_number_value(activity.get("cost")))

    itinerary["total_cost"] = total
    return itinerary


def _number_value(value: Any) -> float:
    return float(value) if isinstance(value, int | float) and value >= 0 else 0.0


def _add_warning(activity: dict[str, Any], warning: str) -> None:
    warnings = activity.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    if warning not in warnings:
        warnings.append(warning)
    activity["warnings"] = warnings


def _find_day_stay_anchor(activities: list[Any]) -> dict[str, Any] | None:
    """Find the activity whose surrounding area should guide same-day lodging."""
    preferred_types = {"景点", "其他"}
    for activity in reversed(activities):
        if not isinstance(activity, dict):
            continue
        if activity.get("place_type") in preferred_types:
            return activity
    for activity in reversed(activities):
        if isinstance(activity, dict) and activity.get("place_type") != "交通":
            return activity
    return None


def _apply_no_self_drive_transport(activity: dict[str, Any]) -> None:
    """Replace self-driving wording in activity transport with non-driving options."""
    transport = activity.get("transport")
    if isinstance(transport, dict):
        mode = str(transport.get("mode", ""))
        description = str(transport.get("description", ""))
        if mode in {"自驾", "租车", "驾车"} or any(
            keyword in description for keyword in ("自驾", "租车", "SUV", "开车")
        ):
            transport["mode"] = "打车"
            transport["description"] = (
                "按不自驾偏好调整为网约车、公共交通或景区接驳; "
                "具体班次和车程建议出发前确认。"
            )

    activity_description = activity.get("description")
    if isinstance(activity_description, str):
        activity["description"] = (
            activity_description.replace("自驾", "乘车")
            .replace("租车", "网约车")
            .replace("经济型SUV", "网约车/接驳车")
        )


def _move_lodging_near_anchor(
    lodging: dict[str, Any],
    anchor: dict[str, Any] | None,
) -> None:
    """Move a lodging activity near the day's main play area."""
    if anchor is None:
        lodging["description"] = (
            "建议选择当天主要游玩区域附近住宿, 减少晚间转场和第二天折返。"
        )
        return

    anchor_name = str(anchor.get("place_name") or "当天主要游玩区域")
    lodging["place_name"] = f"{anchor_name}附近住宿"
    lodging["description"] = (
        f"根据不自驾偏好, 建议住在{anchor_name}附近, "
        "优先选择步行可达餐饮或可预约接驳的酒店/民宿。"
    )
    if _valid_coordinate(anchor.get("lng")) and _valid_coordinate(anchor.get("lat")):
        lodging["lng"] = anchor["lng"]
        lodging["lat"] = anchor["lat"]


def _valid_coordinate(value: Any) -> bool:
    """Return whether a coordinate value is a finite non-zero number."""
    return isinstance(value, int | float) and value != 0


def _append_summary_note(value: Any, note: str) -> str:
    """Append a short note to an itinerary summary."""
    summary = value if isinstance(value, str) and value.strip() else ""
    if not summary:
        return note
    if note in summary:
        return summary
    return f"{summary} {note}"


async def _load_session(session_id: str) -> dict[str, Any]:
    """Load session data while keeping chat resilient to Redis failures."""
    try:
        return await get_session(session_id) or {}
    except Exception as exc:
        logger.warning("Failed to load session_id=%s: %s", session_id, exc)
        return {}


async def _save_session(
    *,
    session_id: str,
    user_profile: dict[str, Any] | None,
    itinerary: dict[str, Any] | None,
    message_count: int,
    messages: list[dict[str, str]],
) -> None:
    """Save session data while keeping SSE completion resilient."""
    try:
        await save_session(
            session_id,
            {
                "user_profile": user_profile,
                "itinerary": itinerary,
                "message_count": message_count,
                "messages": messages,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as exc:
        logger.warning("Failed to save session_id=%s: %s", session_id, exc)


def _extract_itinerary(
    graph_event: dict[str, Any],
    current_itinerary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extract the latest itinerary patch from a graph event."""
    for patch in graph_event.values():
        if isinstance(patch, dict):
            itinerary = patch.get("itinerary")
            if isinstance(itinerary, dict):
                return _sanitize_itinerary_confidence(itinerary)
            messages = patch.get("messages", [])
            if not isinstance(messages, list):
                messages = [messages]
            for message in messages:
                if isinstance(message, AIMessage):
                    _, extracted = _split_content_and_itinerary(_message_text(message))
                    if extracted is not None:
                        return extracted
    return current_itinerary


def _session_messages(value: Any) -> list[dict[str, str]]:
    """Normalize stored session messages and keep the latest context window."""
    if not isinstance(value, list):
        return []

    messages: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue

        content = content.strip()
        if not content:
            continue

        message = {"role": role, "content": content}
        created_at = item.get("created_at")
        if isinstance(created_at, str):
            message["created_at"] = created_at
        messages.append(message)

    return messages[-MAX_SESSION_MESSAGES:]


def _to_langchain_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
    """Convert persisted session messages into LangChain message objects."""
    converted: list[BaseMessage] = []
    for message in messages:
        if message["role"] == "user":
            converted.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            converted.append(AIMessage(content=message["content"]))
    return converted


def _append_session_turn(
    messages: list[dict[str, str]],
    *,
    user_content: str,
    assistant_content: str,
) -> list[dict[str, str]]:
    """Append one user/assistant turn and trim to the context window."""
    created_at = datetime.now(UTC).isoformat()
    next_messages = [
        *messages,
        {
            "role": "user",
            "content": user_content.strip(),
            "created_at": created_at,
        },
    ]
    if assistant_content.strip():
        next_messages.append(
            {
                "role": "assistant",
                "content": assistant_content.strip(),
                "created_at": created_at,
            }
        )

    return next_messages[-MAX_SESSION_MESSAGES:]
