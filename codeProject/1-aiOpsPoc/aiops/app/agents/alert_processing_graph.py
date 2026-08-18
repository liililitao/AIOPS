"""确定性的告警分类顶层 LangGraph。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class AlertProcessingGraphState(TypedDict, total=False):
    alert_id: str
    alert: Any
    classification_status: Literal["pending", "hit", "miss", "unavailable"]
    classification_result: dict[str, Any] | None
    classification_score: int | None
    match_usage: Any
    route: Literal["reuse", "analyze"]
    result: Any


GraphNode = Callable[[AlertProcessingGraphState], Awaitable[dict[str, Any]]]


def create_alert_processing_graph(
    *,
    classify: GraphNode,
    reuse: GraphNode,
    analyze: GraphNode,
):
    """构建“先分类，命中复用，未命中进入 Agent”的固定路由。"""

    async def classify_node(state: AlertProcessingGraphState) -> dict[str, Any]:
        return await classify(state)

    async def reuse_node(state: AlertProcessingGraphState) -> dict[str, Any]:
        return {"route": "reuse", **(await reuse(state))}

    async def analyze_node(state: AlertProcessingGraphState) -> dict[str, Any]:
        return {"route": "analyze", **(await analyze(state))}

    def route_after_classification(
        state: AlertProcessingGraphState,
    ) -> Literal["reuse", "analyze"]:
        return "reuse" if state.get("classification_status") == "hit" else "analyze"

    builder = StateGraph(AlertProcessingGraphState)
    builder.add_node("classify", classify_node)
    builder.add_node("reuse", reuse_node)
    builder.add_node("analyze", analyze_node)
    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_after_classification,
        {"reuse": "reuse", "analyze": "analyze"},
    )
    builder.add_edge("reuse", END)
    builder.add_edge("analyze", END)
    return builder.compile()
