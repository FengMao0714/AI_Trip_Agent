"""Natural clarification question generation for incomplete travel state."""
# ruff: noqa: RUF001

from __future__ import annotations

from app.agent.intent import INVALID_INTENT_FIELD_MESSAGES, TravelIntent, TravelState

QUESTION_BY_FIELD = {
    "destination": "想去哪个城市或区域",
    "departure_city": "从哪个城市出发",
    "days": "计划玩几天",
    "people": "几个人出行",
    "budget": "总预算大概多少",
}


class ClarificationAgent:
    """Generate concise follow-up questions from code-validated missing fields."""

    def ask(self, state: TravelState) -> str:
        """Ask for missing required fields while reflecting known information."""
        missing_fields = [
            field for field in state.intent.missing_fields if field in QUESTION_BY_FIELD
        ]
        invalid_messages = [
            INVALID_INTENT_FIELD_MESSAGES[field]
            for field in state.intent.invalid_fields
            if field in INVALID_INTENT_FIELD_MESSAGES
        ]
        if not missing_fields and not invalid_messages:
            return "信息已经比较完整了，我可以开始规划。"

        known_summary = _known_summary(state.intent)
        question_items = [QUESTION_BY_FIELD[field] for field in missing_fields[:4]]
        question_text = "、".join(question_items)
        invalid_text = "、".join(invalid_messages)

        if invalid_messages and question_items:
            correction_text = f"{invalid_text}; 还需要补充: {question_text}"
        elif invalid_messages:
            correction_text = invalid_text
        else:
            correction_text = (
                f"还需要你补充 {len(question_items)} 个信息: {question_text}"
            )

        if known_summary:
            return f"可以，我会按“{known_summary}”来规划。{correction_text}。"

        return f"可以，我先帮你把需求框起来。{correction_text}。"


def _known_summary(intent: TravelIntent) -> str:
    parts: list[str] = []
    if intent.travel_style == "情侣":
        parts.append("情侣出行")
    elif intent.travel_style:
        parts.append(intent.travel_style)

    if intent.departure_city:
        parts.append(f"{intent.departure_city}出发")
    if intent.destination:
        parts.append(intent.destination)
    if intent.start_date:
        parts.append(intent.start_date)
    if intent.days and intent.days > 0:
        parts.append(f"{intent.days}天")
    if intent.people and intent.people > 0:
        parts.append(f"{intent.people}人")

    budget_text = _budget_text(intent)
    if budget_text:
        parts.append(budget_text)

    for text in [*intent.preferences, *intent.constraints]:
        normalized = _normalize_preference(text)
        if normalized and normalized not in parts:
            parts.append(normalized)

    return " + ".join(parts[:6])


def _budget_text(intent: TravelIntent) -> str | None:
    if intent.budget is not None and intent.budget > 0:
        return f"预算{int(intent.budget)}元"
    if any(
        text in intent.constraints for text in ("预算一般", "别太贵", "预算不要太高")
    ):
        return "中等预算" if "预算一般" in intent.constraints else "控制预算"
    return None


def _normalize_preference(text: str) -> str | None:
    if text in {"不想太累", "别太累", "不要太累"}:
        return "不太累"
    if text == "预算一般":
        return "中等预算"
    if text == "别太贵":
        return "控制预算"
    return text
