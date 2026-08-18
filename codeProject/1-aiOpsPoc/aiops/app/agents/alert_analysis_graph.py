"""告警分析 Tool-calling Agent 的 LangGraph。"""

from __future__ import annotations

import json
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, ValidationError

from app.core.alert_tool_runtime import AlertToolContext
from app.schemas.agent_analysis import AgentAnalysis, RecommendedAction


TOOL_EVIDENCE_KEYS = {
    "search_historical_alerts": "historical",
    "search_knowledge_base": "knowledge",
    "investigate_splunk_logs": "splunk",
}


class AlertAnalysisGraphState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    iteration: int
    exhausted: bool
    evidence: dict[str, dict[str, Any]]
    analysis: dict[str, Any] | None
    validation_errors: list[str]
    validation_repair_count: int
    degraded_reasons: list[str]
    status: str


def _empty_evidence() -> dict[str, dict[str, Any]]:
    return {"historical": {}, "knowledge": {}, "splunk": {}}


def _decode_tool_content(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    try:
        decoded = json.loads(str(content or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"success": False, "error_code": "invalid_tool_result"}
    return decoded if isinstance(decoded, dict) else {
        "success": False,
        "error_code": "invalid_tool_result",
    }


def _validate_evidence_references(
    analysis: BaseModel,
    evidence: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    for item in getattr(analysis, "evidence_refs", []):
        source = str(item.source)
        if source == "alert":
            continue
        payload = evidence.get(source) or {}
        if not payload.get("success"):
            errors.append(f"evidence_ref_unavailable:{source}:{item.reference}")
            continue
        locator = str(item.reference).split(":", 1)[-1].strip()
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if locator and locator not in serialized:
            errors.append(f"evidence_ref_missing:{source}:{item.reference}")
    gap_text = " ".join(
        str(item).lower() for item in getattr(analysis, "evidence_gaps", [])
    )
    gap_aliases = {
        "historical": ("historical", "历史"),
        "knowledge": ("knowledge", "知识库", "cmdb", "sop", "运维手册"),
        "splunk": ("splunk", "日志"),
    }
    for source, payload in evidence.items():
        if not payload or payload.get("success") is not False:
            continue
        if not any(alias in gap_text for alias in gap_aliases.get(source, (source,))):
            errors.append(f"failed_tool_gap_missing:{source}")
    return errors


def _degraded_analysis(reasons: list[str]) -> AgentAnalysis:
    details = reasons or ["structured_output_unavailable"]
    return AgentAnalysis(
        conclusion="当前证据不足，无法形成通过结构化校验的完整结论。",
        hypotheses=[],
        impact="影响范围暂无法可靠确认。",
        actions=[RecommendedAction(
            priority="中",
            action="补齐缺失证据后重新分析或转交人工复核。",
            rationale="避免将格式错误或不存在的证据引用作为告警事实。",
            requires_approval=False,
        )],
        validation_steps=["恢复不可用的数据源", "使用新的分析运行重新校验"],
        evidence_refs=[],
        evidence_gaps=[f"结构化输出校验失败：{item}" for item in details],
        confidence="低",
    )


def create_alert_analysis_graph(
    *,
    model,
    tools,
    max_steps: int,
    output_schema: type[BaseModel] | None = None,
    output_repair_limit: int = 1,
    checkpointer=None,
):
    """构建有步数上限、可选结构化终结与 checkpoint 的模型/Tool 循环。"""
    step_limit = max(1, int(max_steps))
    repair_limit = max(0, min(1, int(output_repair_limit)))
    bound_model = model.bind_tools(tools)
    structured_model = (
        model.with_structured_output(output_schema)
        if output_schema is not None
        else None
    )

    async def call_model(state: AlertAnalysisGraphState):
        next_iteration = int(state.get("iteration", 0)) + 1
        if next_iteration > step_limit:
            return {
                "iteration": next_iteration,
                "exhausted": True,
                "messages": [AIMessage(
                    content="已达到最大调查步数，按现有证据降级输出。"
                )],
            }
        response = await bound_model.ainvoke(state.get("messages", []))
        return {
            "iteration": next_iteration,
            "exhausted": False,
            "messages": [response],
        }

    async def collect_evidence(state: AlertAnalysisGraphState):
        evidence = {**_empty_evidence(), **dict(state.get("evidence") or {})}
        for message in state.get("messages", []):
            if not isinstance(message, ToolMessage):
                continue
            key = TOOL_EVIDENCE_KEYS.get(str(message.name or ""))
            if key:
                evidence[key] = _decode_tool_content(message.content)
        return {"evidence": evidence}

    async def finalize_analysis(state: AlertAnalysisGraphState):
        assert structured_model is not None
        repair_errors = state.get("validation_errors") or []
        instruction = (
            "基于当前告警和 Tool 证据生成最终结构化分析。"
            "不得引用不存在或查询失败的证据；证据不足必须写入 evidence_gaps。"
        )
        if repair_errors:
            instruction += (
                "上一次输出未通过校验，请只修复这些错误："
                + "; ".join(repair_errors)
            )
        try:
            candidate = await structured_model.ainvoke([
                *state.get("messages", []),
                HumanMessage(content=instruction),
            ])
            validated = output_schema.model_validate(candidate)
            return {
                "analysis": validated.model_dump(mode="json"),
                "validation_errors": [],
            }
        except (ValidationError, TypeError, ValueError) as exc:
            return {
                "analysis": None,
                "validation_errors": [f"structured_output_invalid:{exc}"],
            }
        except Exception as exc:
            return {
                "analysis": None,
                "validation_errors": [
                    f"structured_output_unavailable:{type(exc).__name__}"
                ],
            }

    def validate_agent_output(state: AlertAnalysisGraphState):
        candidate = state.get("analysis")
        errors = list(state.get("validation_errors") or [])
        if candidate is not None:
            try:
                validated = output_schema.model_validate(candidate)
                errors.extend(_validate_evidence_references(
                    validated,
                    state.get("evidence") or _empty_evidence(),
                ))
            except (ValidationError, TypeError, ValueError) as exc:
                errors.append(f"structured_output_invalid:{exc}")
        elif not errors:
            errors.append("structured_output_missing")

        if not errors:
            return {
                "status": "completed",
                "validation_errors": [],
                "validation_repair_count": int(
                    state.get("validation_repair_count", 0)
                ),
            }

        repairs = int(state.get("validation_repair_count", 0))
        if repairs < repair_limit:
            return {
                "status": "repairing",
                "validation_errors": errors,
                "validation_repair_count": repairs + 1,
            }
        return {"status": "invalid", "validation_errors": errors}

    def build_degraded_analysis(state: AlertAnalysisGraphState):
        reasons = list(state.get("validation_errors") or [])
        if state.get("exhausted"):
            reasons.append("max_agent_steps_exceeded")
        degraded = _degraded_analysis(reasons)
        return {
            "analysis": degraded.model_dump(mode="json"),
            "status": "degraded",
            "degraded_reasons": reasons or ["structured_output_unavailable"],
        }

    def route_after_model(state: AlertAnalysisGraphState):
        if state.get("exhausted"):
            return "degraded_analysis" if output_schema is not None else END
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return "finalize_analysis" if output_schema is not None else END

    def route_after_validation(state: AlertAnalysisGraphState):
        if state.get("status") == "completed":
            return END
        if state.get("status") == "repairing":
            return "finalize_analysis"
        return "degraded_analysis"

    builder = StateGraph(
        AlertAnalysisGraphState,
        context_schema=AlertToolContext,
    )
    builder.add_node("agent_model", call_model)
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    builder.add_node("collect_evidence", collect_evidence)
    builder.add_edge(START, "agent_model")
    builder.add_conditional_edges("agent_model", route_after_model)
    builder.add_edge("tools", "collect_evidence")
    builder.add_edge("collect_evidence", "agent_model")
    if output_schema is not None:
        builder.add_node("finalize_analysis", finalize_analysis)
        builder.add_node("validate_agent_output", validate_agent_output)
        builder.add_node("degraded_analysis", build_degraded_analysis)
        builder.add_edge("finalize_analysis", "validate_agent_output")
        builder.add_conditional_edges(
            "validate_agent_output",
            route_after_validation,
        )
        builder.add_edge("degraded_analysis", END)
    return builder.compile(checkpointer=checkpointer)
