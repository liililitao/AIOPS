"""告警 Agent 的内部结构化输出契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Confidence = Literal["低", "中", "高"]
EvidenceSource = Literal["alert", "historical", "knowledge", "splunk"]


class RootCauseHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    confidence: Confidence


class RecommendedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Literal["低", "中", "高"]
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    requires_approval: bool = True


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: EvidenceSource
    reference: str = Field(min_length=1)
    claim: str = Field(min_length=1)


class AgentAnalysis(BaseModel):
    """经 Pydantic 与证据引用校验后才能进入业务输出。"""

    model_config = ConfigDict(extra="forbid")

    conclusion: str = Field(min_length=1)
    hypotheses: list[RootCauseHypothesis]
    impact: str = Field(min_length=1)
    actions: list[RecommendedAction]
    validation_steps: list[str]
    evidence_refs: list[EvidenceReference]
    evidence_gaps: list[str]
    confidence: Confidence


def render_agent_analysis(analysis: AgentAnalysis) -> str:
    """将结构化分析确定性渲染成兼容现有前端的 Markdown。"""
    hypotheses = "\n".join(
        f"- {item.hypothesis}（置信度：{item.confidence}）：{item.rationale}"
        for item in analysis.hypotheses
    ) or "- 暂无可验证的根因假设"
    actions = "\n".join(
        f"- [{item.priority}] {item.action}：{item.rationale}"
        for item in analysis.actions
    ) or "- 保持监控并等待补充证据"
    validation_steps = "\n".join(
        f"- {item}" for item in analysis.validation_steps
    ) or "- 补齐缺失证据后重新分析"
    gaps = "\n".join(
        f"- {item}" for item in analysis.evidence_gaps
    ) or "- 无已知证据缺口"
    return (
        f"## 分析结论\n\n{analysis.conclusion}\n\n"
        f"## 根因假设\n\n{hypotheses}\n\n"
        f"## 影响评估\n\n{analysis.impact}\n\n"
        f"## 处理建议\n\n{actions}\n\n"
        f"## 验证步骤\n\n{validation_steps}\n\n"
        f"## 证据缺口\n\n{gaps}\n\n"
        f"**总体置信度：{analysis.confidence}**"
    )
