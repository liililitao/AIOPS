"""分类未命中后的 LangGraph Tool-calling 告警分析 Agent。"""

from __future__ import annotations

import json
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agents.alert_analysis_graph import create_alert_analysis_graph
from app.config import get_settings
from app.core.alert_tool_runtime import AlertToolContext
from app.core.llm import get_executor_llm
from app.schemas.alert import RawAlert, TokenUsage
from app.schemas.agent_analysis import (
    AgentAnalysis,
    RecommendedAction,
    render_agent_analysis,
)

logger = logging.getLogger("aiops.alert_analysis_agent")


def resolve_agent_run_id(
    alert: RawAlert,
    *,
    alert_id: str,
    formal_output_exists: bool,
) -> str:
    """未完成运行稳定复用；正式输出后的主动重分析创建新运行。"""
    if formal_output_exists:
        return f"agent_{uuid4().hex}"
    canonical = json.dumps(
        alert.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(
        f"{alert_id}\0{canonical}".encode("utf-8")
    ).hexdigest()[:32]
    return f"agent_{digest}"


@dataclass
class AgentAnalysisResult:
    run_id: str
    started_at: str
    completed_at: str
    evidence: dict
    analysis: AgentAnalysis | None = None
    thread_id: str = ""
    status: str = "completed"
    degraded_reasons: list[str] = field(default_factory=list)
    validation_repair_count: int = 0
    steps: list[dict] = field(default_factory=list)
    investigation_plan: str = ""
    analysis_result: str = ""
    planning_token_usage: TokenUsage = field(default_factory=TokenUsage)
    execution_token_usage: TokenUsage = field(default_factory=TokenUsage)
    token_usage: TokenUsage = field(default_factory=TokenUsage)


class AlertAnalysisAgent:
    """让模型按需选择三个受控 Tool，并保留兼容的业务返回结构。"""

    def __init__(
        self,
        *,
        model=None,
        tools=None,
        max_steps: int | None = None,
        output_repair_limit: int | None = None,
        checkpointer=None,
        checkpoint_enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        if tools is None:
            from app.tools import ALERT_ANALYSIS_TOOLS

            tools = ALERT_ANALYSIS_TOOLS
        self.model = model
        self.tools = list(tools)
        self.max_steps = int(
            settings.MAX_AGENT_STEPS if max_steps is None else max_steps
        )
        self.output_repair_limit = int(
            settings.AGENT_OUTPUT_REPAIR_LIMIT
            if output_repair_limit is None
            else output_repair_limit
        )
        self.checkpointer = checkpointer
        self.checkpoint_enabled = (
            settings.AGENT_CHECKPOINT_ENABLED
            if checkpoint_enabled is None
            else bool(checkpoint_enabled)
        )
        self.checkpoint_db_path = settings.agent_checkpoint_db_path

    async def analyze(
        self,
        alert: RawAlert,
        *,
        alert_id: str,
        run_id: str | None = None,
        actor_id: str = "system",
    ) -> AgentAnalysisResult:
        started_at = datetime.now(timezone.utc).isoformat()
        run_id = run_id or f"agent_{uuid4().hex}"
        thread_id = f"{alert_id}:{run_id}"
        evidence = _empty_evidence()
        steps: list[dict[str, Any]] = []
        execution_usage = TokenUsage()
        structured_analysis: AgentAnalysis | None = None
        status = "completed"
        degraded_reasons: list[str] = []
        validation_repair_count = 0

        try:
            model = self.model or get_executor_llm()
            if self.checkpointer is not None:
                state = await self._invoke_graph(
                    model=model,
                    alert=alert,
                    alert_id=alert_id,
                    run_id=run_id,
                    actor_id=actor_id,
                    checkpointer=self.checkpointer,
                )
            elif self.checkpoint_enabled:
                from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

                self.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
                async with AsyncSqliteSaver.from_conn_string(
                    str(self.checkpoint_db_path)
                ) as saver:
                    state = await self._invoke_graph(
                        model=model,
                        alert=alert,
                        alert_id=alert_id,
                        run_id=run_id,
                        actor_id=actor_id,
                        checkpointer=saver,
                    )
            else:
                state = await self._invoke_graph(
                    model=model,
                    alert=alert,
                    alert_id=alert_id,
                    run_id=run_id,
                    actor_id=actor_id,
                    checkpointer=None,
                )
            messages = list(state.get("messages", []))
            evidence, steps = _collect_tool_evidence(messages)
            execution_usage = _sum_message_usage(messages)
            structured_analysis = AgentAnalysis.model_validate(state["analysis"])
            analysis = render_agent_analysis(structured_analysis)
            status = str(state.get("status") or "completed")
            degraded_reasons = list(state.get("degraded_reasons") or [])
            validation_repair_count = int(
                state.get("validation_repair_count", 0)
            )
        except Exception as exc:
            logger.warning("LangGraph alert analysis unavailable: %s", exc)
            steps = [{
                "step": 1,
                "name": "agent_model",
                "status": "degraded",
                "error_code": "agent_model_unavailable",
            }]
            status = "degraded"
            degraded_reasons = ["agent_model_unavailable"]
            structured_analysis = self._fallback_structured_analysis(
                evidence,
                degraded_reasons,
            )
            analysis = render_agent_analysis(structured_analysis)

        completed_at = datetime.now(timezone.utc).isoformat()
        return AgentAnalysisResult(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            evidence=evidence,
            analysis=structured_analysis,
            thread_id=thread_id,
            status=status,
            degraded_reasons=degraded_reasons,
            validation_repair_count=validation_repair_count,
            steps=steps,
            investigation_plan="",
            analysis_result=analysis,
            planning_token_usage=TokenUsage(),
            execution_token_usage=execution_usage,
            token_usage=execution_usage.model_copy(deep=True),
        )

    async def _invoke_graph(
        self,
        *,
        model,
        alert: RawAlert,
        alert_id: str,
        run_id: str,
        actor_id: str,
        checkpointer,
    ) -> dict[str, Any]:
        graph = create_alert_analysis_graph(
            model=model,
            tools=self.tools,
            max_steps=self.max_steps,
            output_schema=AgentAnalysis,
            output_repair_limit=self.output_repair_limit,
            checkpointer=checkpointer,
        )
        config = (
            {"configurable": {"thread_id": f"{alert_id}:{run_id}"}}
            if checkpointer is not None
            else None
        )
        graph_input: dict[str, Any] | None = {
            "messages": [
                SystemMessage(content=self._system_prompt()),
                HumanMessage(content=self._build_query(alert)),
            ],
            "iteration": 0,
            "exhausted": False,
            "evidence": _empty_evidence(),
            "validation_repair_count": 0,
        }
        if checkpointer is not None and await checkpointer.aget_tuple(config):
            graph_input = None
        return await graph.ainvoke(
            graph_input,
            config=config,
            context=AlertToolContext(
                alert_id=alert_id,
                run_id=run_id,
                actor_id=actor_id,
            ),
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是 AIOps 告警证据分析 Agent。分类库已经未命中。"
            "你只能按需要调用已注册的历史告警、知识库/CMDB 和 Splunk 日志 Tool。"
            "Tool 失败或无结果只代表证据缺失，不代表事件不存在。"
            "不得输出任意 SPL、密钥、破坏性命令或未经批准的系统变更。"
            "历史案例只能作为参考，CMDB 和当前日志事实优先。"
        )

    @staticmethod
    def _build_query(alert: RawAlert) -> str:
        first = alert.results[0]
        fields = (
            ("告警名称", alert.alert_name),
            ("触发原因", alert.trigger_reason),
            ("应用", alert.application_code),
            ("资源", first.id),
            ("域名", first.properties_hostname),
            ("请求", first.properties_requestUri),
            ("动作", first.properties_action),
        )
        return "\n".join(
            f"{key}: {value}"
            for key, value in fields
            if str(value or "").strip()
        )

    @staticmethod
    def _fallback_analysis(evidence: dict) -> str:
        available = [
            name
            for name, data in evidence.items()
            if isinstance(data, dict) and data.get("success")
        ]
        unavailable = [
            name
            for name, data in evidence.items()
            if not isinstance(data, dict) or not data.get("success")
        ]
        return (
            "已按当前可用信息完成受控调查："
            f"可用证据为 {('、'.join(available) or '无')}；"
            f"缺失或不可用证据为 {('、'.join(unavailable) or '无')}。"
            "证据缺失不代表事件不存在，需在依赖恢复后重新分析或人工确认。"
        )

    @classmethod
    def _fallback_structured_analysis(
        cls,
        evidence: dict,
        reasons: list[str],
    ) -> AgentAnalysis:
        return AgentAnalysis(
            conclusion=cls._fallback_analysis(evidence),
            hypotheses=[],
            impact="影响范围暂无法可靠确认。",
            actions=[RecommendedAction(
                priority="中",
                action="依赖恢复后重新分析或转交人工确认。",
                rationale="当前 Agent 未能生成通过校验的完整分析。",
                requires_approval=False,
            )],
            validation_steps=["检查模型与数据源状态", "重新执行告警分析"],
            evidence_refs=[],
            evidence_gaps=list(reasons) or ["Agent 分析不可用"],
            confidence="低",
        )


TOOL_EVIDENCE_KEYS = {
    "search_historical_alerts": "historical",
    "search_knowledge_base": "knowledge",
    "investigate_splunk_logs": "splunk",
}


def _empty_evidence() -> dict[str, dict]:
    return {"historical": {}, "knowledge": {}, "splunk": {}}


def _decode_tool_content(content: Any) -> dict:
    if isinstance(content, dict):
        return content
    try:
        decoded = json.loads(str(content or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"success": False, "error_code": "invalid_tool_result"}
    if not isinstance(decoded, dict):
        return {"success": False, "error_code": "invalid_tool_result"}
    return decoded


def _collect_tool_evidence(
    messages: list[Any],
) -> tuple[dict[str, dict], list[dict[str, Any]]]:
    evidence = _empty_evidence()
    steps: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        payload = _decode_tool_content(message.content)
        key = TOOL_EVIDENCE_KEYS.get(str(message.name or ""))
        if key:
            evidence[key] = payload
        steps.append({
            "step": len(steps) + 1,
            "name": f"tool:{message.name}",
            "status": "completed" if payload.get("success") else "degraded",
            "error_code": payload.get("error_code"),
            "tool_call_id": message.tool_call_id,
        })
    return evidence, steps


def _message_text(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", "")).strip()
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ).strip()
    return str(content or "").strip()


def _last_ai_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _message_text(message)
            if text:
                return text
    return ""


def _sum_message_usage(messages: list[Any]) -> TokenUsage:
    usage = TokenUsage()
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        metadata = getattr(message, "usage_metadata", {}) or {}
        prompt = int(metadata.get("input_tokens", 0) or 0)
        completion = int(metadata.get("output_tokens", 0) or 0)
        total = int(metadata.get("total_tokens", 0) or 0)
        usage.prompt_tokens += prompt
        usage.completion_tokens += completion
        usage.total_tokens += total or prompt + completion
    return usage
