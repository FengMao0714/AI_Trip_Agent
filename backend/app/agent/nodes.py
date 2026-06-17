"""LangGraph node functions for the travel planning agent."""
# ruff: noqa: RUF001

from __future__ import annotations

import json
import logging
import re
from typing import Any, Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


def get_llm_service_error_status(exc: BaseException) -> int | None:
    """Return an upstream LLM HTTP status code when it can be inferred."""
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    match = re.search(r"Error code:\s*(?P<status>\d{3})", str(exc))
    if match:
        return int(match.group("status"))

    return None


def is_llm_service_error(exc: BaseException) -> bool:
    """Return whether an exception came from the upstream LLM service."""
    if get_llm_service_error_status(exc) is not None:
        return True

    message = str(exc).lower()
    return "api key" in message and (
        "invalid" in message or "authentication" in message
    )


class ChatModel(Protocol):
    """Small protocol for chat models used by the planner node."""

    async def ainvoke(self, messages: Any) -> AIMessage:
        """Invoke the chat model asynchronously."""


async def run_planner(state: AgentState, llm: ChatModel) -> dict[str, Any]:
    """Planner node: call the LLM for the next ReAct step."""
    try:
        response = await llm.ainvoke(state["messages"])
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1,
        }
    except Exception as exc:
        if is_llm_service_error(exc):
            logger.exception("Planner LLM service failed: %s", exc)
            raise

        logger.exception("Planner node failed: %s", exc)
        return {
            "messages": [AIMessage(content="抱歉, 规划过程中遇到了问题, 请稍后重试。")],
            "should_end": True,
        }


def run_tools(tools: list[Any]) -> ToolNode:
    """Create a ToolNode for executing LangChain-compatible tools."""
    return ToolNode(
        tools,
        handle_tool_errors=(
            "工具调用失败或被限流。请基于已有行程和已获得的信息继续规划, "
            "必要时用保守估算补全结果。"
        ),
    )


async def generate_response(state: AgentState) -> dict[str, Any]:
    """Response node: finalize the current answer for downstream SSE output."""
    try:
        if not state["messages"]:
            return {
                "messages": [AIMessage(content="抱歉, 我没有生成有效回复。")],
                "should_end": True,
            }

        return {"should_end": True}
    except Exception as exc:
        logger.exception("Response node failed: %s", exc)
        return {
            "messages": [AIMessage(content="抱歉, 整理回复时遇到了问题。")],
            "should_end": True,
        }


async def handle_fallback(state: AgentState) -> dict[str, Any]:
    """Fallback node: stop the loop when the iteration limit is reached."""
    try:
        message = AIMessage(content=_build_stage_result_content(state))
        return {
            "messages": [message],
            "should_end": True,
        }
    except Exception as exc:
        logger.exception("Fallback node failed: %s", exc)
        return {
            "messages": [AIMessage(content="抱歉, 兜底处理时遇到了问题。")],
            "should_end": True,
        }


def route_decision(state: AgentState) -> str:
    """Route from the planner node to tools, fallback, or final response."""
    if state["iteration_count"] >= MAX_ITERATIONS:
        return "fallback_node"

    if not state["messages"]:
        return "response_node"

    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tool_node"

    return "response_node"


def _build_stage_result_content(state: AgentState) -> str:
    """Build a conservative visible result when the ReAct loop reaches its limit."""
    if state.get("itinerary"):
        itinerary = state["itinerary"]
        return (
            "工具调用没有在当前轮完成，我先保留并返回已有行程，"
            "你可以继续指定要细化的日期、地点或交通方式。\n\n"
            f"<itinerary_json>{json.dumps(itinerary, ensure_ascii=False)}</itinerary_json>"
        )

    user_message = _latest_human_text(state["messages"])
    destination = _extract_destination(user_message)
    return (
        "我还没有拿到足够可靠的真实 POI、地址和坐标，所以这次先不生成行程卡片，"
        "避免把占位内容误当成真实行程。"
        f"当前识别到的目的地是“{destination}”。如果你要去省级范围或多个城市，"
        "请再指定一个主要城市/区域，例如青岛、威海、烟台或“青岛+威海”，"
        "我会重新用工具补齐地点后再生成完整行程。"
    )


def _latest_human_text(messages: list[Any]) -> str:
    """Return the latest human message content as text."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return _message_text(message)
    return ""


def _message_text(message: BaseMessage) -> str:
    """Normalize a LangChain message into plain text."""
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


def _extract_destination(text: str) -> str:
    """Best-effort destination extraction from a Chinese travel request."""
    normalized_text = _strip_leading_date_words(text)
    patterns = [
        r"(?:换成|改成|替换为|换到|改去|再生成|再给我|给我生成|来一份)(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12}?)(?:的)?(?:\d{1,2}|[一二两三四五六七八九十]{1,3})\s*(?:天|日)",
        r"去(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12}?)(?:玩|旅行|旅游|行程|游|的行程)",
        r"(?:^|[，,。.!！?？\s])(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12}?)(?:\d{1,2}|[一二两三四五六七八九十]{1,3})\s*(?:天|日)",
        r"(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12}?)(?:情侣|亲子|老人|国庆|春节|五一|暑假|旅行|旅游|行程|游)",
        r"目的地[：: ]*(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12})",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match:
            destination = _clean_destination(match.group("destination"))
            if destination is not None:
                return destination
    return "目的地待确认"


def _strip_leading_date_words(text: str) -> str:
    """Remove month words that can be mistaken for a destination prefix."""
    return re.sub(r"\d{1,2}\s*月份?", "", text)


def _clean_destination(value: str) -> str | None:
    """Clean a best-effort destination candidate without inventing a route."""
    candidate = value.strip(" ，,。.!！?？:：;；")
    candidate = re.sub(r"\d{1,2}\s*(?:天|日).*$", "", candidate)
    candidate = re.sub(r"[一二两三四五六七八九十]{1,3}\s*(?:天|日).*$", "", candidate)
    for suffix in ("旅游", "旅行", "行程", "游", "的"):
        candidate = candidate.removesuffix(suffix)
    candidate = candidate.strip(" ，,。.!！?？:：;；")
    invalid_tokens = (
        "我们",
        "两个",
        "个人",
        "情侣",
        "预算",
        "没有",
        "忌口",
        "想去",
        "打算",
        "计划",
        "准备",
    )
    if not 2 <= len(candidate) <= 12:
        return None
    if any(token in candidate for token in invalid_tokens):
        return None
    return candidate


def _extract_days(text: str) -> int:
    """Best-effort day count extraction."""
    digit_match = re.search(r"(?P<days>\d{1,2})\s*(?:天|日)", text)
    if digit_match:
        return _clamp_days(int(digit_match.group("days")))

    chinese_match = re.search(
        r"(?P<days>[一二两三四五六七八九十]{1,3})\s*(?:天|日)", text
    )
    if chinese_match:
        return _clamp_days(_chinese_number(chinese_match.group("days")))

    if re.search(r"(?:1|一|一个)\s*(?:周|星期|礼拜)", text):
        return 7

    return 3


def _extract_budget(text: str) -> int | None:
    """Best-effort budget extraction."""
    amount_pattern = (
        r"(?:\d+(?:\.\d+)?|[零〇一二两三四五六七八九十百千万]+)\s*(?:万|千|百|k|K)?"
    )
    patterns = [
        rf"(?:预算|人均|总预算|费用|花费|开销)\s*(?:大概|大约|约|是|为|有|在|控制在|不超过|以内)?\s*(?P<budget>{amount_pattern})\s*(?:元|块|人民币)?",
        rf"(?P<budget>{amount_pattern})\s*(?:元|块|人民币)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        budget = _parse_budget_amount(match.group("budget"))
        if budget is not None:
            return budget
    return None


def _clamp_days(days: int) -> int:
    """Keep fallback itinerary length reasonable."""
    return max(1, min(days, 7))


def _parse_budget_amount(value: str) -> int | None:
    """Parse common Chinese budget expressions into RMB."""
    token = re.sub(r"[\s,，￥¥元块人民币]", "", value)
    if not token:
        return None

    digit_match = re.fullmatch(
        r"(?P<number>\d+(?:\.\d+)?)(?P<unit>万|千|百|k|K)?", token
    )
    if digit_match:
        number = float(digit_match.group("number"))
        unit = digit_match.group("unit")
        multiplier = {"万": 10000, "千": 1000, "百": 100, "k": 1000, "K": 1000}.get(
            unit,
            1,
        )
        budget = int(number * multiplier)
        return budget if budget >= 100 else None

    colloquial_wan_match = re.fullmatch(
        r"(?P<wan>[零〇一二两三四五六七八九十百千]+)万(?P<tail>[一二两三四五六七八九])",
        token,
    )
    if colloquial_wan_match:
        budget = (
            _chinese_integer(colloquial_wan_match.group("wan")) * 10000
            + _chinese_integer(colloquial_wan_match.group("tail")) * 1000
        )
        return budget if budget >= 100 else None

    budget = _chinese_integer(token)
    return budget if budget >= 100 else None


def _chinese_integer(value: str) -> int:
    """Parse a Chinese integer with units up to 万."""
    digit_map = {
        "零": 0,
        "〇": 0,
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
    }
    unit_map = {"十": 10, "百": 100, "千": 1000}
    total = 0
    section = 0
    number = 0

    for char in value:
        if char in digit_map:
            number = digit_map[char]
            continue
        if char in unit_map:
            section += (number or 1) * unit_map[char]
            number = 0
            continue
        if char == "万":
            total += (section + number or 1) * 10000
            section = 0
            number = 0

    return total + section + number


def _chinese_number(value: str) -> int:
    """Parse a small Chinese day count."""
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
    if value == "十":
        return 10
    if value.startswith("十"):
        return 10 + mapping.get(value[-1], 0)
    if "十" in value:
        left, right = value.split("十", 1)
        return mapping.get(left, 1) * 10 + mapping.get(right, 0)
    return mapping.get(value, 3)


def _build_conservative_itinerary(
    *,
    destination: str,
    days: int,
    budget: int | None,
    user_message: str,
) -> dict[str, Any]:
    """Create a conservative itinerary skeleton from user constraints."""
    estimated_total = budget * 8 // 10 if budget else days * 700
    daily_budget = max(150, estimated_total // days)
    style_note = _style_note(user_message)
    days_payload = []

    for day_index in range(1, days + 1):
        day_cost = daily_budget
        days_payload.append(
            {
                "day": day_index,
                "date": f"第 {day_index} 天",
                "weather": {
                    "condition": "待确认",
                    "advice": "实时天气未确认，建议保留室内备选并预留交通缓冲。",
                },
                "activities": [
                    {
                        "time_slot": "09:00-11:30",
                        "place_name": f"{destination}核心区域游览",
                        "place_type": "景点",
                        "lng": 0,
                        "lat": 0,
                        "description": f"围绕{style_note}安排上午主线，具体 POI 待工具补齐。",
                        "cost": day_cost // 3,
                    },
                    {
                        "time_slot": "12:00-13:30",
                        "place_name": f"{destination}本地餐饮",
                        "place_type": "餐厅",
                        "lng": 0,
                        "lat": 0,
                        "description": "优先选择动线附近、评价稳定的餐厅，避免为用餐跨城移动。",
                        "cost": day_cost // 4,
                        "transport": {
                            "mode": "未知",
                            "distance_km": 0,
                            "duration_min": 0,
                            "description": "路线待地图工具确认。",
                        },
                    },
                    {
                        "time_slot": "14:30-17:30",
                        "place_name": f"{destination}下午体验点",
                        "place_type": "景点",
                        "lng": 0,
                        "lat": 0,
                        "description": "下午安排节奏较慢的体验或备选景点，便于按天气调整。",
                        "cost": day_cost // 3,
                        "transport": {
                            "mode": "未知",
                            "distance_km": 0,
                            "duration_min": 0,
                            "description": "路线待地图工具确认。",
                        },
                    },
                ],
            }
        )

    return {
        "destination": destination,
        "budget": budget,
        "total_cost": estimated_total,
        "summary": (
            f"{destination}{days}天阶段性方案，先按预算和偏好控制节奏，"
            "坐标、实时天气与路线需在下一轮继续补齐。"
        ),
        "days": days_payload,
    }


def _style_note(text: str) -> str:
    """Return a short style note from the user request."""
    if "情侣" in text:
        return "情侣出行、轻松拍照和舒适节奏"
    if "老人" in text or "父母" in text:
        return "少步行、低强度和方便休息"
    if "亲子" in text or "孩子" in text:
        return "亲子友好、互动体验和安全动线"
    if "历史" in text or "文化" in text:
        return "历史文化和城市代表性"
    return "代表性景点、餐饮和交通效率"
