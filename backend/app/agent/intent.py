"""User travel intent extraction for the planning chat flow."""
# ruff: noqa: RUF001

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr, field_validator

from app.agent.llm_http import direct_http_clients
from app.agent.nodes import _extract_budget, _extract_destination
from app.config import get_settings

logger = logging.getLogger(__name__)

TravelStyle = Literal["穷游", "舒适", "高端", "亲子", "情侣", "特种兵", "休闲"]
TravelStage = Literal["collecting_info", "ready_to_plan", "planning", "completed"]
REQUIRED_INTENT_FIELDS = ("destination", "days", "people", "budget")
INTENT_FIELD_LABELS = {
    "destination": "目的地",
    "departure_city": "出发城市",
    "days": "出行天数",
    "people": "出行人数",
    "budget": "预算",
}
INVALID_INTENT_FIELD_MESSAGES = {
    "days": "出行天数需要大于 0 天",
    "people": "出行人数需要大于 0 人",
    "budget": "预算需要大于 0 元",
}

INTENT_SYSTEM_PROMPT = """你是旅游助手中的需求理解 Agent。
你的任务是从用户原始自然语言中抽取结构化旅游需求, 不生成行程, 不调用工具, 不决定下一步流程。

抽取要求:
- 只根据用户明确表达或上下文中已确认的信息填写字段, 不要编造。
- 输出结构化 JSON, 字段名必须使用 TravelIntent schema 中的英文名。
- budget 必须标准化为人民币总预算数字, 例如“1万元”输出 10000, “一千块/一千快”输出 1000。
- people 必须包含用户本人, 例如“我和父母”输出 3, “我和两个朋友”输出 3。
- days、people、budget 可以直接输出数字; 如果用户明确给出 0 或负数, 保留该数值, 由后端代码判定非法。
- 用户说“预算一般”“别太贵”等模糊预算时, budget 保持 null, 可把原话放入 constraints 或 preferences。
- 用户说“玩几天”“待几天”但没有明确数字时, days 保持 null。
- travel_style 只能从枚举中选择: 穷游、舒适、高端、亲子、情侣、特种兵、休闲。
- missing_fields 和 invalid_fields 由后端代码校验, 你可以给出建议但不要决定是否可以开始规划。
- confidence 表示本次结构化抽取整体置信度, 取 0 到 1。
"""


class TravelIntent(BaseModel):
    """Structured travel intent extracted from a user message."""

    destination: str | None = Field(default=None, description="用户想去的目的地")
    departure_city: str | None = Field(default=None, description="出发城市")
    start_date: str | None = Field(default=None, description="出发日期或大致时间")
    days: int | None = Field(default=None, description="游玩天数")
    people: int | None = Field(default=None, description="出行人数")
    budget: float | None = Field(default=None, description="总预算，人民币")
    travel_style: TravelStyle | None = Field(default=None, description="旅行风格")
    preferences: list[str] = Field(default_factory=list, description="用户偏好")
    must_visit: list[str] = Field(default_factory=list, description="明确想去的景点")
    constraints: list[str] = Field(default_factory=list, description="约束条件")
    missing_fields: list[str] = Field(default_factory=list, description="缺失字段")
    invalid_fields: list[str] = Field(default_factory=list, description="非法字段")
    confidence: float = Field(default=0.0, description="抽取置信度，0到1")

    @field_validator("destination", "departure_city", "start_date", mode="before")
    @classmethod
    def _blank_string_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return str(value)

    @field_validator("days", mode="before")
    @classmethod
    def _coerce_days(cls, value: Any) -> int | None:
        return _coerce_days_value(value)

    @field_validator("people", mode="before")
    @classmethod
    def _coerce_people(cls, value: Any) -> int | None:
        return _coerce_people_value(value)

    @field_validator("budget", mode="before")
    @classmethod
    def _coerce_budget(cls, value: Any) -> float | None:
        return _coerce_budget_value(value)

    @field_validator(
        "preferences",
        "must_visit",
        "constraints",
        "missing_fields",
        "invalid_fields",
        mode="before",
    )
    @classmethod
    def _string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, list):
            return [
                item.strip() for item in value if isinstance(item, str) and item.strip()
            ]
        return []

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, value: Any) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(parsed, 1.0))


class TravelState(BaseModel):
    """Persisted multi-turn state for collecting travel requirements."""

    raw_messages: list[str] = Field(default_factory=list)
    intent: TravelIntent = Field(default_factory=TravelIntent)
    confirmed: bool = False
    stage: TravelStage = "collecting_info"


class RequirementValidationResult(BaseModel):
    """Code-owned requirement validation result."""

    missing_fields: list[str] = Field(default_factory=list)
    invalid_fields: list[str] = Field(default_factory=list)
    ready_to_plan: bool = False
    stage: TravelStage = "collecting_info"


class RequirementValidator:
    """Validate whether collected travel requirements are ready for planning."""

    required_fields: tuple[str, ...] = REQUIRED_INTENT_FIELDS

    def validate_intent(self, intent: TravelIntent) -> RequirementValidationResult:
        """Return code-computed missing fields and planning readiness."""
        data = intent.model_dump()
        invalid_fields = [
            field
            for field in ("days", "people", "budget")
            if data.get(field) is not None and data[field] <= 0
        ]
        missing_fields = [
            field
            for field in self.required_fields
            if field not in invalid_fields and not data.get(field)
        ]
        ready_to_plan = len(missing_fields) == 0 and len(invalid_fields) == 0
        return RequirementValidationResult(
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            ready_to_plan=ready_to_plan,
            stage="ready_to_plan" if ready_to_plan else "collecting_info",
        )

    def apply(self, state: TravelState) -> TravelState:
        """Return a TravelState with code-validated missing fields and stage."""
        validation = self.validate_intent(state.intent)
        intent_data = state.intent.model_dump()
        intent_data["missing_fields"] = validation.missing_fields
        intent_data["invalid_fields"] = validation.invalid_fields
        return TravelState(
            raw_messages=state.raw_messages,
            intent=TravelIntent.model_validate(intent_data),
            confirmed=state.confirmed or validation.ready_to_plan,
            stage=validation.stage,
        )

    def field_labels(self, missing_fields: list[str]) -> list[str]:
        """Return user-facing labels for missing field ids."""
        return [
            INTENT_FIELD_LABELS[field]
            for field in missing_fields
            if field in INTENT_FIELD_LABELS
        ]

    def invalid_field_messages(self, invalid_fields: list[str]) -> list[str]:
        """Return user-facing invalid field messages."""
        return [
            INVALID_INTENT_FIELD_MESSAGES[field]
            for field in invalid_fields
            if field in INVALID_INTENT_FIELD_MESSAGES
        ]


class IntentExtractionAgent:
    """LLM-backed intent extractor with a deterministic fallback."""

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm

    async def extract(
        self,
        message: str,
        previous_intent: TravelIntent | None = None,
    ) -> TravelIntent:
        """Extract a TravelIntent from the user message."""
        rule_intent = build_heuristic_travel_intent(message)
        fallback_intent = (
            merge_travel_intents(previous_intent, rule_intent)
            if previous_intent is not None
            else rule_intent
        )
        if not _llm_extraction_enabled():
            return fallback_intent

        llm = self.llm or _build_intent_llm()
        if llm is None:
            return fallback_intent

        try:
            llm_intent = await self._extract_with_llm(
                llm,
                message,
                previous_intent,
                rule_intent,
            )
        except Exception as exc:
            logger.warning("IntentExtractionAgent LLM extraction failed: %s", exc)
            return fallback_intent

        if llm_intent is None:
            return fallback_intent

        return normalize_intent(merge_travel_intents(fallback_intent, llm_intent))

    async def _extract_with_llm(
        self,
        llm: Any,
        message: str,
        previous_intent: TravelIntent | None,
        rule_intent: TravelIntent,
    ) -> TravelIntent | None:
        previous_payload = (
            previous_intent.model_dump(exclude_none=True)
            if previous_intent is not None
            else None
        )
        rule_payload = rule_intent.model_dump(exclude_none=True)
        human_prompt = (
            "用户原始输入:\n"
            f"{message}\n\n"
            "规则辅助抽取结果, 只作为高确定性线索, 不是最终结果:\n"
            f"{json.dumps(rule_payload, ensure_ascii=False)}\n\n"
            "已知上一轮结构化需求, 可能为空:\n"
            f"{json.dumps(previous_payload, ensure_ascii=False)}"
        )

        if hasattr(llm, "with_structured_output"):
            structured_llm = llm.with_structured_output(TravelIntent)
            result = await structured_llm.ainvoke(
                [
                    SystemMessage(content=INTENT_SYSTEM_PROMPT),
                    HumanMessage(content=human_prompt),
                ]
            )
        else:
            result = await llm.ainvoke(
                [
                    SystemMessage(content=INTENT_SYSTEM_PROMPT),
                    HumanMessage(content=human_prompt),
                ]
            )

        if isinstance(result, TravelIntent):
            return normalize_intent(result)
        if isinstance(result, dict):
            return normalize_intent(TravelIntent.model_validate(result))

        content = getattr(result, "content", result)
        if not isinstance(content, str):
            return None

        return normalize_intent(
            TravelIntent.model_validate_json(_extract_json_object(content))
        )


QueryUnderstandingAgent = IntentExtractionAgent


async def extract_travel_intent(
    message: str,
    previous_intent: TravelIntent | None = None,
    *,
    llm: Any | None = None,
) -> TravelIntent:
    """Extract travel intent with an LLM first and heuristics as fallback."""
    return await IntentExtractionAgent(llm=llm).extract(message, previous_intent)


def build_heuristic_travel_intent(
    message: str,
    previous_intent: TravelIntent | None = None,
) -> TravelIntent:
    """Build a conservative intent from deterministic local parsing."""
    destination = _extract_destination_from_message(message)
    days = _extract_explicit_days(message)
    budget = _extract_budget(message)
    people = _extract_people(message)
    departure_city = _extract_departure_city(message)
    if people is None and departure_city is not None and days is not None:
        people = 1
    travel_style = _extract_travel_style(message)

    intent = TravelIntent(
        destination=destination,
        departure_city=departure_city,
        start_date=_extract_start_date(message),
        days=days,
        people=people,
        budget=float(budget) if budget is not None else None,
        travel_style=travel_style,
        preferences=_extract_preferences(message),
        must_visit=_extract_must_visit(message),
        constraints=_extract_constraints(message),
        confidence=_heuristic_confidence(destination, days, people, budget),
    )

    if previous_intent is not None:
        intent = merge_travel_intents(previous_intent, intent)

    return normalize_intent(intent)


def normalize_intent(intent: TravelIntent) -> TravelIntent:
    """Validate missing fields and normalize list values."""
    data = intent.model_dump()
    data["preferences"] = _dedupe(data.get("preferences", []))
    data["must_visit"] = _dedupe(data.get("must_visit", []))
    data["constraints"] = _dedupe(data.get("constraints", []))
    data["invalid_fields"] = _dedupe(data.get("invalid_fields", []))
    normalized = TravelIntent.model_validate(data)
    validation = RequirementValidator().validate_intent(normalized)
    data["missing_fields"] = validation.missing_fields
    data["invalid_fields"] = validation.invalid_fields
    return TravelIntent.model_validate(data)


def merge_travel_intents(
    previous: TravelIntent | None,
    current: TravelIntent,
) -> TravelIntent:
    """Merge a newly extracted intent into previous session intent."""
    if previous is None:
        return normalize_intent(current)

    previous_data = previous.model_dump()
    current_data = current.model_dump()
    destination_changed = (
        bool(current_data.get("destination"))
        and bool(previous_data.get("destination"))
        and current_data["destination"] != previous_data["destination"]
    )

    if destination_changed:
        data = previous_data
        data["destination"] = None
        data["start_date"] = None
        data["days"] = None
        data["travel_style"] = None
        data["preferences"] = []
        data["must_visit"] = []
    else:
        data = previous_data

    scalar_fields = (
        "destination",
        "departure_city",
        "start_date",
        "days",
        "people",
        "budget",
        "travel_style",
    )
    for field in scalar_fields:
        if current_data.get(field) is not None:
            data[field] = current_data[field]

    for field in ("preferences", "must_visit", "constraints"):
        data[field] = _dedupe([*data.get(field, []), *current_data.get(field, [])])

    if current_data.get("people") == 1 and current_data.get("travel_style") is None:
        if data.get("travel_style") == "情侣":
            data["travel_style"] = None
        data["preferences"] = [
            preference
            for preference in data.get("preferences", [])
            if preference != "情侣出行"
        ]

    data["confidence"] = max(float(data.get("confidence") or 0.0), current.confidence)
    data["missing_fields"] = current_data.get("missing_fields", [])
    data["invalid_fields"] = current_data.get("invalid_fields", [])
    return normalize_intent(TravelIntent.model_validate(data))


def intent_from_user_profile(
    user_profile: dict[str, Any] | None,
) -> TravelIntent | None:
    """Read a TravelIntent from the persisted user profile if present."""
    travel_state = travel_state_from_user_profile(user_profile)
    if _intent_has_data(travel_state.intent):
        return travel_state.intent
    return None


def travel_state_from_user_profile(user_profile: dict[str, Any] | None) -> TravelState:
    """Read TravelState from persisted user profile, falling back to legacy intent."""
    if not isinstance(user_profile, dict):
        return TravelState()

    raw_state = user_profile.get("travel_state")
    if isinstance(raw_state, dict):
        try:
            return RequirementValidator().apply(TravelState.model_validate(raw_state))
        except Exception:
            logger.warning("Ignoring invalid persisted travel state")

    raw_intent = user_profile.get("intent")
    if isinstance(raw_intent, dict):
        try:
            intent = normalize_intent(TravelIntent.model_validate(raw_intent))
            return RequirementValidator().apply(TravelState(intent=intent))
        except Exception:
            logger.warning("Ignoring invalid persisted travel intent")

    legacy_data = {
        field: user_profile.get(field)
        for field in (
            "destination",
            "departure_city",
            "start_date",
            "days",
            "people",
            "budget",
            "travel_style",
            "preferences",
            "must_visit",
            "constraints",
            "missing_fields",
            "invalid_fields",
            "confidence",
        )
        if field in user_profile
    }
    if not legacy_data:
        return TravelState()

    try:
        intent = normalize_intent(TravelIntent.model_validate(legacy_data))
        return RequirementValidator().apply(TravelState(intent=intent))
    except Exception:
        logger.warning("Ignoring invalid legacy user profile intent")
        return TravelState()


def update_travel_state(
    state: TravelState,
    raw_message: str,
    extracted_intent: TravelIntent,
) -> TravelState:
    """Append the new raw message and merge newly extracted fields into state."""
    merged_intent = merge_travel_intents(state.intent, extracted_intent)
    raw_messages = [*state.raw_messages, raw_message]
    updated = TravelState(
        raw_messages=raw_messages,
        intent=merged_intent,
        confirmed=state.confirmed,
        stage=state.stage,
    )
    return RequirementValidator().apply(updated)


def travel_state_with_stage(
    state: TravelState,
    stage: TravelStage,
    *,
    confirmed: bool | None = None,
) -> TravelState:
    """Return a copy of state with a runtime stage update."""
    return TravelState(
        raw_messages=state.raw_messages,
        intent=state.intent,
        confirmed=state.confirmed if confirmed is None else confirmed,
        stage=stage,
    )


def has_persisted_travel_state(user_profile: dict[str, Any] | None) -> bool:
    """Return whether the session already has explicit TravelState data."""
    return isinstance(user_profile, dict) and isinstance(
        user_profile.get("travel_state"), dict
    )


def user_profile_with_travel_state(
    user_profile: dict[str, Any] | None,
    state: TravelState,
) -> dict[str, Any]:
    """Persist TravelState while keeping common fields at top level."""
    updated = dict(user_profile or {})
    validation = RequirementValidator().validate_intent(state.intent)
    intent_data = state.intent.model_dump()
    intent_data["missing_fields"] = validation.missing_fields
    intent_data["invalid_fields"] = validation.invalid_fields
    validated_state = TravelState(
        raw_messages=state.raw_messages,
        intent=TravelIntent.model_validate(intent_data),
        confirmed=state.confirmed or validation.ready_to_plan,
        stage=state.stage,
    )
    state_payload = validated_state.model_dump(exclude_none=True)
    intent_payload = validated_state.intent.model_dump(exclude_none=True)
    updated["travel_state"] = state_payload
    updated["intent"] = intent_payload

    for field in (
        "destination",
        "departure_city",
        "start_date",
        "days",
        "people",
        "budget",
        "travel_style",
        "preferences",
        "must_visit",
        "constraints",
        "missing_fields",
        "invalid_fields",
        "confidence",
    ):
        if field in intent_payload:
            updated[field] = intent_payload[field]

    updated["stage"] = validated_state.stage
    updated["confirmed"] = validated_state.confirmed
    return updated


def user_profile_with_intent(
    user_profile: dict[str, Any] | None,
    intent: TravelIntent,
) -> dict[str, Any]:
    """Persist intent while keeping common fields at top level for compatibility."""
    state = travel_state_from_user_profile(user_profile)
    state = TravelState(
        raw_messages=state.raw_messages,
        intent=normalize_intent(intent),
        confirmed=state.confirmed,
        stage=state.stage,
    )
    return user_profile_with_travel_state(user_profile, state)


def _llm_extraction_enabled() -> bool:
    settings = get_settings()
    return bool(settings.intent_extraction_llm_enabled and settings.deepseek_api_key)


def _build_intent_llm() -> ChatOpenAI | None:
    settings = get_settings()
    if not settings.deepseek_api_key:
        return None

    extra_body: dict[str, Any] = {}
    if not settings.llm_thinking_enabled:
        extra_body["thinking"] = {"type": "disabled"}

    return ChatOpenAI(
        api_key=SecretStr(settings.deepseek_api_key),
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        extra_body=extra_body or None,
        streaming=False,
        **direct_http_clients(),
    )


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in intent response")
    return text[start : end + 1]


def _coerce_days_value(value: Any) -> int | None:
    """Normalize LLM or heuristic day expressions to an integer."""
    simple_number = _coerce_int_literal(value)
    if simple_number is not None:
        return simple_number
    if not isinstance(value, str):
        return None

    parsed = _extract_explicit_days(value)
    if parsed is not None:
        return parsed

    stripped = value.strip()
    return _chinese_number(stripped) or None


def _coerce_people_value(value: Any) -> int | None:
    """Normalize LLM or heuristic traveler expressions to an integer."""
    simple_number = _coerce_int_literal(value)
    if simple_number is not None:
        return simple_number
    if not isinstance(value, str):
        return None

    parsed = _extract_people(value)
    if parsed is not None:
        return parsed

    stripped = value.strip()
    return _chinese_number(stripped) or None


def _coerce_budget_value(value: Any) -> float | None:
    """Normalize budget expressions to RMB while preserving invalid numbers."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    signed_number = _coerce_float_literal(text)
    if signed_number is not None:
        return signed_number

    negative_match = re.search(
        r"(?:预算|人均|总预算|费用|花费|开销)?\s*[-负]\s*(?P<number>\d+(?:\.\d+)?)",
        text,
    )
    if negative_match:
        return -float(negative_match.group("number"))

    parsed = _extract_budget(f"预算{text}")
    return float(parsed) if parsed is not None else None


def _coerce_int_literal(value: Any) -> int | None:
    """Parse plain numeric literals without discarding zero or negatives."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    signed_number = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if signed_number is None:
        return None

    parsed = float(signed_number.group(0))
    return int(parsed) if parsed.is_integer() else None


def _coerce_float_literal(value: str) -> float | None:
    """Parse a plain signed number string without interpreting unit suffixes."""
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value):
        return None
    return float(value)


def _none_if_unknown(value: str | None) -> str | None:
    if not value or value == "目的地待确认":
        return None
    return value


def _extract_destination_from_message(text: str) -> str | None:
    """Extract a likely destination with high-confidence local patterns."""
    patterns = [
        r"(?:换成|改成|替换为|换到|改去|再生成|再给我|给我生成|来一份)(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12}?)(?:的)?(?:\d{1,2}|[一二两三四五六七八九十]{1,3})\s*(?:天|日)",
        r"(?:去|到|目的地[:： ]*)(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12}?)(?:玩|旅行|旅游|行程|游|[，,。.!！?？\s]|$)",
        r"(?:安排|规划|设计|做)(?:一个|一趟)?(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12})(?:旅行|旅游|行程|游)",
        r"(?P<destination>[\u4e00-\u9fffA-Za-z]{2,12})(?:旅行|旅游|行程|游)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        cleaned = _clean_destination_candidate(match.group("destination"))
        if cleaned is not None:
            return cleaned

    return _none_if_unknown(_extract_destination(text))


def _clean_destination_candidate(value: str) -> str | None:
    candidate = value.strip(" ，,。.!！?？:：;；")
    prefixes = (
        "帮我安排一个",
        "帮我安排",
        "帮我规划一个",
        "帮我规划",
        "安排一个",
        "规划一个",
        "我想",
        "想",
        "一个",
        "一趟",
    )
    for prefix in prefixes:
        if candidate.startswith(prefix):
            candidate = candidate.removeprefix(prefix)
    candidate = candidate.strip(" ，,。.!！?？:：;；")
    invalid_tokens = ("帮我", "安排", "规划", "设计", "旅行", "旅游", "行程")
    if not 2 <= len(candidate) <= 12:
        return None
    if any(token in candidate for token in invalid_tokens):
        return None
    return candidate


def _extract_explicit_days(text: str) -> int | None:
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

    return None


def _extract_people(text: str) -> int | None:
    normalized = re.sub(r"\s+", "", text)
    parent_pairs = ("父母", "爸妈", "爸爸妈妈", "爹妈", "父亲母亲")
    single_parent = ("爸爸", "妈妈", "父亲", "母亲", "老爸", "老妈")

    if any(parent in normalized for parent in parent_pairs):
        parent_pair_pattern = "|".join(parent_pairs)
        if re.search(
            rf"(?:我|自己|本人)(?:要|想|打算|计划|准备)?"
            rf"(?:和|跟|带|陪|以及|还有)(?:{parent_pair_pattern})",
            normalized,
        ) or re.search(
            rf"(?:{parent_pair_pattern})(?:和|跟|带|陪|以及|还有)(?:我|自己|本人)",
            normalized,
        ):
            return 3
        return 2

    if any(parent in normalized for parent in single_parent) and re.search(
        r"(?:我|自己|本人)(?:和|跟|带|陪|以及|还有)",
        normalized,
    ):
        return 2

    if any(
        keyword in normalized
        for keyword in ("女朋友", "男朋友", "对象", "情侣", "夫妻")
    ):
        return 2

    family_match = re.search(r"一家(?P<count>\d{1,2}|[三四五六七八九十])口", normalized)
    if family_match:
        return _parse_count(family_match.group("count"))

    companion_match = re.search(
        r"(?:我|自己|本人)(?:和|跟|带|陪|以及|还有)"
        r"(?P<count>\d{1,2}|[一二两三四五六七八九十]{1,3})"
        r"\s*(?:个|位)?(?:朋友|同学|同事|老人|大人|成人|孩子|小孩)",
        normalized,
    )
    if companion_match:
        return _parse_count(companion_match.group("count")) + 1

    digit_match = re.search(
        r"(?P<count>\d{1,2})\s*(?:个|位)?(?:个人|人|老人|大人|成人|孩子|小孩|学生|朋友|同学|同事)",
        normalized,
    )
    if digit_match:
        return int(digit_match.group("count"))

    chinese_match = re.search(
        r"(?P<count>[一二两三四五六七八九十]{1,3})\s*(?:个|位)?(?:个人|人|老人|大人|成人|孩子|小孩|学生|朋友|同学|同事)",
        normalized,
    )
    if chinese_match:
        return _chinese_number(chinese_match.group("count"))

    if any(
        keyword in normalized
        for keyword in ("一个人", "单人", "独自", "自己去", "自己一个", "我自己")
    ) and not _has_group_traveler_keyword(normalized):
        return 1

    if _looks_like_solo_first_person_request(normalized):
        return 1

    return None


def _parse_count(value: str) -> int:
    """Parse a small Arabic or Chinese people count."""
    if value.isdigit():
        return int(value)
    return _chinese_number(value)


def _looks_like_solo_first_person_request(text: str) -> bool:
    """Infer one traveler for simple first-person singular requests."""
    if not re.search(
        r"(?:^|[，,。.!！?？])我[^，,。.!！?？]{0,12}?"
        r"(?:要|想|打算|计划|准备|会)?(?:去|到|出发|玩)",
        text,
    ):
        return False

    return not _has_group_traveler_keyword(text)


def _has_group_traveler_keyword(text: str) -> bool:
    """Return whether text names companions or a group."""
    group_keywords = (
        "我们",
        "咱们",
        "我和",
        "我跟",
        "我带",
        "我陪",
        "父母",
        "爸妈",
        "爸爸",
        "妈妈",
        "朋友",
        "同学",
        "同事",
        "家人",
        "老人",
        "孩子",
        "小孩",
        "女朋友",
        "男朋友",
        "对象",
        "情侣",
        "夫妻",
        "一家",
    )
    return any(keyword in text for keyword in group_keywords)


def _extract_departure_city(text: str) -> str | None:
    match = re.search(r"从(?P<city>[\u4e00-\u9fffA-Za-z]{2,12})出发", text)
    if not match:
        return None
    city = match.group("city").strip(" ，,。.!！?？:：;；")
    return city if 2 <= len(city) <= 12 else None


def _extract_start_date(text: str) -> str | None:
    patterns = [
        r"\d{1,2}\s*月\s*\d{1,2}\s*[日号]?",
        r"\d{1,2}\s*月份?",
        r"下周[一二三四五六日天]",
        r"毕业后",
        r"国庆",
        r"春节",
        r"五一",
        r"暑假",
        r"寒假",
        r"下周",
        r"周末",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).replace(" ", "")
    return None


def _extract_travel_style(text: str) -> TravelStyle | None:
    if any(keyword in text for keyword in ("穷游", "省钱", "便宜")):
        return "穷游"
    if any(keyword in text for keyword in ("高端", "奢华", "豪华")):
        return "高端"
    if any(keyword in text for keyword in ("亲子", "孩子", "小孩")):
        return "亲子"
    if any(keyword in text for keyword in ("女朋友", "男朋友", "对象", "情侣")):
        return "情侣"
    if "特种兵" in text:
        return "特种兵"
    if any(
        keyword in text
        for keyword in (
            "休闲",
            "轻松",
            "别太累",
            "不要太累",
            "不想太累",
            "老人",
            "父母",
            "爸妈",
        )
    ):
        return "休闲"
    if any(keyword in text for keyword in ("舒适", "预算一般", "预算中等")):
        return "舒适"
    return None


def _extract_preferences(text: str) -> list[str]:
    keywords = (
        "美食",
        "自然风光",
        "山水",
        "历史文化",
        "博物馆",
        "拍照",
        "咖啡",
        "温泉",
        "夜景",
        "徒步",
    )
    preferences = [keyword for keyword in keywords if keyword in text]
    if any(keyword in text for keyword in ("女朋友", "男朋友", "对象", "情侣")):
        preferences.append("情侣出行")
    if any(keyword in text for keyword in ("亲子", "孩子", "小孩")):
        preferences.append("亲子友好")
    if any(keyword in text for keyword in ("老人", "父母", "爸妈")):
        preferences.append("老人友好")
    return preferences


def _extract_constraints(text: str) -> list[str]:
    candidates = (
        "不要太累",
        "别太累",
        "不想太累",
        "避开人多",
        "预算不要太高",
        "别太贵",
        "预算一般",
        "带老人",
        "老人",
        "父母",
        "爸妈",
        "老人友好",
        "带小孩",
        "不吃辣",
        "没有忌口",
        "不自驾",
        "不会开车",
    )
    return [candidate for candidate in candidates if candidate in text]


def _extract_must_visit(text: str) -> list[str]:
    match = re.search(
        r"(?:必须去|一定要去|必去|想打卡)(?P<places>[^。！？!?]{2,40})", text
    )
    if not match:
        return []

    places = re.split(r"[、,，和以及]", match.group("places"))
    return [
        place.strip(" ，,。.!！?？:：;；")
        for place in places
        if 2 <= len(place.strip(" ，,。.!！?？:：;；")) <= 12
    ]


def _heuristic_confidence(
    destination: str | None,
    days: int | None,
    people: int | None,
    budget: int | None,
) -> float:
    confidence = 0.2
    if destination:
        confidence += 0.25
    if days:
        confidence += 0.25
    if people:
        confidence += 0.1
    if budget:
        confidence += 0.1
    return min(confidence, 0.8)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _intent_has_data(intent: TravelIntent) -> bool:
    return any(
        [
            intent.destination,
            intent.departure_city,
            intent.start_date,
            intent.days,
            intent.people,
            intent.budget,
            intent.travel_style,
            intent.preferences,
            intent.must_visit,
            intent.constraints,
        ]
    )


def _clamp_days(days: int) -> int:
    return max(1, min(days, 30))


def _chinese_number(value: str) -> int:
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
    return mapping.get(value, 0)
