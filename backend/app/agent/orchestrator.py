"""Planning orchestration wrapper around the existing LangGraph planner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langgraph.graph.state import CompiledStateGraph

from app.agent.graph import build_graph
from app.agent.intent import TravelState


@dataclass(frozen=True)
class PlanningDomainAgent:
    """Logical planning agent mapped onto the current LangGraph/tool stack."""

    name: str
    responsibility: str
    tools: tuple[str, ...]


PLANNING_DOMAIN_AGENTS = (
    PlanningDomainAgent(
        "景点 Agent", "补充和验证真实 POI", ("poi_search", "rag_search")
    ),
    PlanningDomainAgent(
        "酒店 Agent", "根据行程区域和预算提出住宿策略", ("rag_search",)
    ),
    PlanningDomainAgent("交通 Agent", "规划城市间和市内交通方式", ("route_plan",)),
    PlanningDomainAgent("预算 Agent", "控制总预算并拆分费用", ()),
    PlanningDomainAgent(
        "路线 Agent", "串联每日动线和转场顺序", ("route_plan", "weather")
    ),
)


class PlanningOrchestrator:
    """Gate and build the planning graph only when requirements are complete."""

    def __init__(
        self,
        build_graph_func: Callable[..., Awaitable[CompiledStateGraph]] = build_graph,
    ) -> None:
        self._build_graph = build_graph_func
        self.domain_agents = PLANNING_DOMAIN_AGENTS

    async def build_graph(
        self,
        state: TravelState,
        **kwargs: Any,
    ) -> CompiledStateGraph:
        """Build the existing LangGraph planner after a stage gate."""
        if state.stage != "ready_to_plan":
            raise ValueError("Planning requires TravelState.stage == 'ready_to_plan'")
        return await self._build_graph(**kwargs)
