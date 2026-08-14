"""告警分类库未命中后的三 Tool AI 分析 Agent。

Agent 负责受控地收集历史实例、知识库/CMDB 和 Splunk 日志证据，再让执行模型
对证据作出可审计的简短研判。报告和处置建议仍由报告服务生成，保证输出格式
与前端保持一致。所有 Tool 调用、失败状态和模型 Token 都会被调用方持久化。
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.config import get_settings
from app.core.llm import call_llm_with_retry, get_executor_llm, get_planner_llm
from app.schemas.alert import RawAlert, TokenUsage

logger = logging.getLogger("aiops.alert_analysis_agent")


@dataclass
class AgentAnalysisResult:
    run_id: str
    started_at: str
    completed_at: str
    evidence: dict
    steps: list[dict] = field(default_factory=list)
    investigation_plan: str = ""
    analysis_result: str = ""
    planning_token_usage: TokenUsage = field(default_factory=TokenUsage)
    execution_token_usage: TokenUsage = field(default_factory=TokenUsage)
    token_usage: TokenUsage = field(default_factory=TokenUsage)


class AlertAnalysisAgent:
    """执行既定的、可审计的三 Tool 告警调查流程。

    Tool 的参数都从告警与服务端配置生成。模型只负责解释已取得的证据，不能
    生成 SPL、访问任意文件或跳过审计记录。
    """

    async def analyze(self, alert: RawAlert, *, alert_id: str) -> AgentAnalysisResult:
        settings = get_settings()
        started_at = datetime.now(timezone.utc).isoformat()
        run_id = f"agent_{uuid4().hex}"
        alert_context = self._build_query(alert)
        first = alert.results[0]
        steps: list[dict] = []

        # 第一阶段不是让模型自由调用外部能力，而是把告警字段转化为可审计的
        # 调查假设与检查重点。无论模型是否可用，后续三个 Tool 都必须执行。
        plan, plan_usage = await self._plan(alert, alert_context)
        steps.append({
            "step": 1, "name": "ai_investigation_planning",
            "status": "completed" if plan else "degraded",
            "message": "规划模型已生成调查假设、证据优先级与验证重点" if plan else "规划模型不可用，使用保守默认调查计划",
            "token_usage": plan_usage.model_dump(),
        })

        # 使用 to_thread，既不阻塞 FastAPI 的事件循环，也让同事的 Splunk Tool
        # 可以安全地在自己的线程中调用 asyncio.run。
        historical = await self._run_tool(
            steps, "historical_alert_search", "检索历史相似告警",
            self._historical, alert_context, settings.HISTORICAL_ALERT_TOP_K,
        )
        knowledge = await self._run_tool(
            steps, "knowledge_base_search", "查询知识库与 CMDB",
            self._knowledge, alert_context, first.id, first.properties_hostname,
            settings.KNOWLEDGE_BASE_TOP_K,
        )
        splunk = await self._run_tool(
            steps, "splunk_log_investigation", "调查受控 Splunk 日志证据",
            self._splunk, alert_id,
        )
        evidence = {
            "historical": historical,
            "knowledge": knowledge,
            "splunk": splunk,
        }
        analysis, execution_usage = await self._summarize(alert, plan, evidence)
        total_usage = _sum_usage(plan_usage, execution_usage)
        steps.append({
            "step": 5,
            "name": "ai_evidence_analysis",
            "status": "completed" if analysis else "degraded",
            "message": "执行模型已结合调查计划与三个 Tool 的返回证据完成结构化研判" if analysis else "执行模型不可用，已保留 Tool 原始证据",
            "token_usage": execution_usage.model_dump(),
        })
        return AgentAnalysisResult(
            run_id=run_id, started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(), evidence=evidence,
            steps=steps, investigation_plan=plan, analysis_result=analysis,
            planning_token_usage=plan_usage, execution_token_usage=execution_usage,
            token_usage=total_usage,
        )

    async def _run_tool(self, steps: list[dict], name: str, message: str, func, *args) -> dict:
        number = len(steps) + 1
        try:
            result = await asyncio.to_thread(func, *args)
            success = bool(result.get("success", False)) if isinstance(result, dict) else False
            steps.append({"step": number, "name": name, "status": "completed" if success else "degraded",
                          "message": message, "error_code": result.get("error_code") if isinstance(result, dict) else "invalid_tool_result"})
            return result if isinstance(result, dict) else {"success": False, "error_code": "invalid_tool_result"}
        except Exception as exc:  # Tool 故障不得阻断新告警的报告与建议输出。
            logger.warning("Agent tool %s unavailable: %s", name, exc)
            steps.append({"step": number, "name": name, "status": "degraded", "message": message, "error_code": "tool_unavailable"})
            return {"success": False, "error_code": "tool_unavailable"}

    @staticmethod
    def _historical(query: str, top_k: int) -> dict:
        from app.tools.historical_alert_tool import run_historical_alert_search
        return run_historical_alert_search(query, top_k=top_k)

    @staticmethod
    def _knowledge(query: str, resource_id: str, hostname: str, top_k: int) -> dict:
        from app.tools.knowledge_base_tool import _get_default_service
        return _get_default_service().search(
            query=query, knowledge_type="auto", resource_id=resource_id,
            hostname=hostname, top_k=top_k,
        )

    @staticmethod
    def _splunk(alert_id: str) -> dict:
        from app.tools.splunk_log_tool import run_splunk_investigation
        return run_splunk_investigation(
            alert_id, ["temporal_pattern", "source_concentration", "historical_baseline"], 30,
        )

    async def _plan(self, alert: RawAlert, alert_context: str) -> tuple[str, TokenUsage]:
        """生成调查计划；计划不能跳过或替换后续固定的三个 Tool。"""
        usage = TokenUsage()
        system_prompt = """你是 AIOps 应用告警调查规划 Agent。你的任务是把一条新告警转化为
可审计的调查计划，而不是直接下结论、更改系统或编造证据。

必须遵循：
1. 分类库已经未命中；后续系统将强制调用历史告警、知识库/CMDB、Splunk 日志三个 Tool。
2. 只能依据输入中明确给出的告警字段；字段为空、模拟环境和 Tool 未来可能不可用都必须作为不确定项。
3. 不得把“应用异常”改写为 WAF 拦截或网络攻击；不得默认生产环境、真实用户影响或根因。
4. 优先区分：应用逻辑/权限、认证会话、依赖服务、容量性能、配置发布、恶意访问或监控噪声。
5. 每个假设都要说明需要哪一类证据来证实或证伪。
6. 不输出 SPL、Shell 命令、密钥、个人信息或最终处置命令。

严格按以下 Markdown 小节输出：
## 告警边界
## 初始风险假设（最多 3 条，含验证条件）
## 三个 Tool 的调查重点
## 证据优先级与冲突处理
## 需人工确认的缺口"""
        try:
            content, message = await call_llm_with_retry(
                get_planner_llm(),
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"请为以下应用告警制定调查计划：\n{alert_context}"}],
                max_retries=2, base_delay=1, timeout=40,
            )
            usage = _usage_from_message(message)
            return str(content or "").strip(), usage
        except Exception as exc:
            logger.warning("Agent investigation planning unavailable: %s", exc)
            return self._fallback_plan(alert), usage

    async def _summarize(self, alert: RawAlert, plan: str, evidence: dict) -> tuple[str, TokenUsage]:
        context = json.dumps(evidence, ensure_ascii=False)[:get_settings().AGENT_EVIDENCE_MAX_CONTEXT_CHARS]
        prompt = f"""你是 AIOps 应用告警证据分析 Agent。现在已得到调查计划和三个受控 Tool 的结果。

执行约束：
1. 只能将 Tool 返回的内容和原始告警字段称为“事实”；不要使用常识补齐缺失日志。
2. Tool 的 success=false、error_code、warnings、空数组代表“无可用证据”，绝不代表事件不存在。
3. CMDB 资产事实优先于名称猜测；历史案例只能作为参考，不能当作当前告警的根因。
4. 若环境为 Non-Production 或模拟标识，必须明确其为非生产模拟环境，不得夸大业务影响。
5. 不得默认这是 WAF 事件、攻击事件或真实生产故障；根据告警语义选择应用运维措辞。
6. 对每个根因假设给出支持证据、反证/缺口和置信度（高/中/低）；置信度不是风险等级。
7. 建议必须可执行、按优先级排序，并包含验证完成条件与需要人工确认的权限边界。
8. 不得输出密钥、个人数据、任意 SPL、破坏性命令或未经批准的变更。

严格按以下 Markdown 小节输出，不能遗漏：
## 研判结论
## 证据台账
## 根因假设与置信度
## 影响范围与风险说明
## 优先处置路径
## 验证标准
## 证据缺口与人工确认项

原始告警：
{self._build_query(alert)}

规划模型调查计划：
{plan or '规划模型不可用；按默认三 Tool 调查执行。'}

三个 Tool 的原始受控证据：
{context}"""
        usage = TokenUsage()
        try:
            content, message = await call_llm_with_retry(
                get_executor_llm(),
                [{"role": "system", "content": "输出客观、可审计的应用告警证据研判。"}, {"role": "user", "content": prompt}],
                max_retries=2, base_delay=1, timeout=40,
            )
            usage = _usage_from_message(message)
            return str(content or "").strip(), usage
        except Exception as exc:
            logger.warning("Agent evidence analysis unavailable: %s", exc)
            return self._fallback_analysis(evidence), usage

    @staticmethod
    def _build_query(alert: RawAlert) -> str:
        first = alert.results[0]
        fields = (
            ("告警名称", alert.alert_name), ("触发原因", alert.trigger_reason),
            ("应用", alert.application_code), ("资源", first.id),
            ("域名", first.properties_hostname), ("请求", first.properties_requestUri),
            ("动作", first.properties_action),
        )
        return "\n".join(f"{key}: {value}" for key, value in fields if str(value or "").strip())

    @staticmethod
    def _fallback_analysis(evidence: dict) -> str:
        available = [name for name, data in evidence.items() if isinstance(data, dict) and data.get("success")]
        unavailable = [name for name, data in evidence.items() if not isinstance(data, dict) or not data.get("success")]
        return (
            f"已完成受控证据调查：可用 Tool 为 {('、'.join(available) or '无')}；"
            f"不可用或无结果的 Tool 为 {('、'.join(unavailable) or '无')}。"
            "AI 证据汇总服务暂不可用，以下分析报告与处理建议会基于当前告警及可用证据生成。"
        )

    @staticmethod
    def _fallback_plan(alert: RawAlert) -> str:
        return (
            "## 告警边界\n仅依据当前告警字段进行调查，未将未提供信息视为事实。\n\n"
            "## 初始风险假设（最多 3 条，含验证条件）\n"
            "- 应用功能、认证、权限或依赖异常：需由历史案例、知识库/CMDB 与日志证据交叉验证。\n"
            "- 监控规则或配置变化导致的异常：需人工比对近期发布、阈值与告警规则。\n\n"
            "## 三个 Tool 的调查重点\n历史相似案例、资产/SOP 事实、受控日志时间分布与基线。\n\n"
            "## 证据优先级与冲突处理\n优先采用 CMDB 和实时日志；历史案例仅供参考。\n\n"
            "## 需人工确认的缺口\n发布变更、真实用户影响及需要授权的系统操作。"
        )


def _usage_from_message(message) -> TokenUsage:
    metadata = getattr(message, "usage_metadata", {}) or {}
    return TokenUsage(
        prompt_tokens=int(metadata.get("input_tokens", 0) or 0),
        completion_tokens=int(metadata.get("output_tokens", 0) or 0),
        total_tokens=int(metadata.get("input_tokens", 0) or 0) + int(metadata.get("output_tokens", 0) or 0),
    )


def _sum_usage(*items: TokenUsage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=sum(item.prompt_tokens for item in items),
        completion_tokens=sum(item.completion_tokens for item in items),
        total_tokens=sum(item.total_tokens for item in items),
    )
