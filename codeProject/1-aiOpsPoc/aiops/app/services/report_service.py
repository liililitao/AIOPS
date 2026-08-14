"""
报告生成服务 - LLM 生成分析报告和处理建议
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from urllib.parse import parse_qsl, urlsplit

from app.config import get_settings
from app.core.llm import get_report_llm, call_llm_with_retry, LLM_MAX_RETRIES
from app.schemas.alert import EnrichedAlert, TokenUsage
from app.schemas.cmdb import CmdbLookupResult
from app.schemas.risk import RiskAssessment
from app.core.attack_classifier import get_attack_type_summary

logger = logging.getLogger("aiops.report")

# The alert cache can contain complete request query strings collected by Splunk.
# Those values are not needed for a security assessment, may include user data or
# signatures, and can make an otherwise small prompt unexpectedly large.
_REPORT_URI_LIMIT = 1200
_REPORT_TEXT_LIMIT = 1200
_SENSITIVE_QUERY_KEYS = {
    "access_token", "apikey", "api_key", "code", "encrypt_type", "nonce",
    "openid", "password", "secret", "signature", "sign", "token",
    "msg_signature", "timestamp",
}


def _safe_request_paths(value: str) -> str:
    """Return a compact, parameter-free request-path summary for the LLM.

    The original value remains in the alert JSON and Splunk link; this is only
    the external-model representation.
    """
    if not value:
        return ""

    paths: list[str] = []
    # Splunk joins values with spaces. WAF URI values usually start with a slash, so
    # splitting at whitespace immediately before a slash preserves individual
    # paths without exposing query-string values.
    for raw_uri in re.split(r"\s+(?=/)", value.strip()):
        try:
            parsed = urlsplit(raw_uri)
            path = parsed.path or "/"
            query_keys = [key for key, _ in parse_qsl(parsed.query, keep_blank_values=True)]
            if query_keys:
                sensitive_count = sum(key.lower() in _SENSITIVE_QUERY_KEYS for key in query_keys)
                path += f"?[… {len(query_keys)} parameters, {sensitive_count} masked]"
        except ValueError:
            # Invalid URLs are kept only as a bounded path-like fragment.
            path = raw_uri.split("?", 1)[0]
        if path and path not in paths:
            paths.append(path)

    summary = "\n".join(f"- {path}" for path in paths[:12])
    if len(paths) > 12:
        summary += f"\n- … {len(paths) - 12} more unique paths"
    if len(summary) > _REPORT_URI_LIMIT:
        summary = summary[:_REPORT_URI_LIMIT] + "\n- … truncated"
    return summary


def _build_alert_prompt_data(alert: EnrichedAlert) -> dict:
    """Build the minimum, privacy-safe alert context required by the LLM."""
    results = []
    for result in alert.results[:5]:
        results.append({
            "resource_id": result.id,
            "hostname": result.properties_hostname,
            "request_paths": _safe_request_paths(result.properties_requestUri),
            "waf_action": result.properties_action,
            "count": result.count_int,
        })
    return {
        "alert_name": alert.alert_name,
        "application_code": alert.application_code,
        "trigger_time": alert.trigger_time,
        "event_count": alert.event_count,
        "trigger_reason": (alert.trigger_reason or "")[:_REPORT_TEXT_LIMIT],
        "search_terms": (alert.search_terms or "")[:_REPORT_TEXT_LIMIT],
        "operator_notes": (alert.operator_notes or "")[:_REPORT_TEXT_LIMIT],
        "results": results,
        "note": "Query parameter values and raw multi-value fields are retained locally but masked for AI analysis.",
    }


def _ensure_splunk_link(content: str, splunk_url: str) -> str:
    """Keep the original traceability link in the final local report."""
    if not splunk_url or splunk_url in content:
        return content
    return f"{content}\n\n## Splunk 溯源链接\n- [在 Splunk 中查看]({splunk_url})"


def _estimate_tokens(text: str) -> int:
    """根据文本长度粗略估算 token 数 (中文 ~1.5 字/token, 英文 ~4 字/token)"""
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)


def _extract_token_usage(response) -> TokenUsage:
    """从 LangChain AIMessage 中提取 token 用量，兼容多种 API 格式"""
    try:
        meta = getattr(response, "response_metadata", {}) or {}

        # 方式 1: OpenAI 标准 response_metadata["token_usage"]
        usage = meta.get("token_usage", None)
        if usage:
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

        # 方式 2: langchain usage_metadata (v0.3+)
        um = getattr(response, "usage_metadata", None)
        if um:
            return TokenUsage(
                prompt_tokens=um.get("input_tokens", 0),
                completion_tokens=um.get("output_tokens", 0),
                total_tokens=um.get("total_tokens", 0),
            )

        # 方式 3: 直接在 response_metadata 顶层
        if "prompt_tokens" in meta or "input_tokens" in meta:
            return TokenUsage(
                prompt_tokens=meta.get("prompt_tokens") or meta.get("input_tokens", 0),
                completion_tokens=meta.get("completion_tokens") or meta.get("output_tokens", 0),
                total_tokens=meta.get("total_tokens", 0),
            )

        # 方式 4: llm_output (旧版 langchain)
        llm_out = getattr(response, "llm_output", {}) or {}
        if llm_out and "token_usage" in llm_out:
            usage = llm_out["token_usage"]
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

        # 无 token 数据，记录一次 metadata 结构以便调试
        logger.debug(f"[TOKEN] Unknown metadata structure: keys={list(meta.keys())}, "
                     f"has_usage_metadata={hasattr(response, 'usage_metadata')}, "
                     f"has_llm_output={hasattr(response, 'llm_output')}")
        return TokenUsage()
    except Exception as e:
        logger.debug(f"[TOKEN] Extract failed: {e}")
        return TokenUsage()

# ==========================================
# 报告类型与 Prompt
# ==========================================


def _is_application_alert(alert: EnrichedAlert) -> bool:
    """模拟/受管应用的告警使用应用运维报告，不套用 WAF 安全报告模板。"""
    if str(alert.application_code or "").strip():
        return True
    first = alert.results[0] if alert.results else None
    return bool(first and (
        str(first.id or "").upper().endswith("-APP-SIM")
        or str(first.properties_hostname or "").lower().endswith(".simulated.local")
        or str(first.properties_action or "") == "应用异常"
    ))

ANALYSIS_REPORT_SYSTEM = """你是一位资深的网络安全运维专家。请根据以下告警数据和 CMDB 资产信息，生成一份专业的 WAF 告警分析报告。

报告要求:
1. 使用 Markdown 格式
2. 包含以下章节:
   - 告警概要 (告警名称、触发时间、风险等级)
   - 告警数据详情 (受影响资源、攻击路径、WAF动作)
   - CMDB 资产信息 (证据溯源，附 CMDB 查询方式和结果)
   - 攻击分析 (攻击类型分类、攻击特征、风险评估)
   - 综合风险评估 (三维度判定详情)
   - 相关运维参考
3. 对于 CMDB 查询结果和攻击分类结果，必须在报告中标注为【证据溯源】
4. 语言专业、客观、准确
5. 在 Splunk 中查看的原始链接必须保留"""

ANALYSIS_REPORT_USER = """请根据以下信息生成 WAF 告警分析报告:

## 告警数据
{alert_json}

## CMDB 查询结果
{cmdb_json}

## 风险判定
{risk_json}

## 攻击类型分析
{attack_json}

## 相关知识库参考（RAG 检索结果）
{rag_context}

请开始生成报告。"""

APPLICATION_ANALYSIS_REPORT_SYSTEM = """你是一位资深应用运维与安全分析工程师。请根据应用告警、CMDB 资产信息和已检索的运维证据，生成专业的应用告警分析报告。

重要限制：这是应用日志/业务异常告警，不是 WAF 告警。不得把“应用异常”描述为 WAF 拦截，不得编造攻击源 IP、WAF 规则、封禁动作或安全攻击事实。

报告要求：
1. 使用 Markdown，一级标题必须为“应用告警分析报告：告警名称”。
2. 包含：告警概要、应用与日志详情、资产/环境信息【证据溯源】、原因与影响分析、风险评估、处理参考。
3. 区分业务故障、性能异常、权限异常和安全风险；仅在告警证据实际表明安全风险时提出安全措施。
4. 保留原始日志或 Splunk 溯源链接（如有），不得泄露敏感参数。
5. 语言客观、可执行，说明模拟/非生产环境的实际影响范围。"""

APPLICATION_ANALYSIS_REPORT_USER = """请根据以下信息生成应用告警分析报告：

## 应用告警数据
{alert_json}

## CMDB/环境信息
{cmdb_json}

## 风险判定
{risk_json}

## 规则与异常特征分析
{attack_json}

## 相关运维知识库参考
{rag_context}

请开始生成报告。"""

# ==========================================
# 处理建议 Prompt
# ==========================================

SUGGESTION_SYSTEM = """你是一位经验丰富的安全运维工程师。请根据告警数据、CMDB 资产信息和风险判定，生成一份可执行的告警处理建议。

建议要求:
1. 使用 Markdown 格式
2. 包含以下章节:
   - 立即行动 (需要立即执行的操作清单)
   - 调查步骤 (如何进一步确认是否为真实攻击)
   - 处置建议 (根据告警严重程度给出差异化建议)
   - 后续加固 (WAF 规则优化、系统安全加固建议)
   - 升级路径 (什么情况下需要升级处理)
3. 建议必须具体、可执行，不要泛泛而谈
4. 区分生产和测试环境的不同处理策略
5. 对于高风险告警，强调紧急处置步骤
6. 对于低风险告警，给出快速确认即可的建议"""

SUGGESTION_USER = """请根据以下信息生成告警处理建议:

## 告警数据
{alert_json}

## CMDB 查询结果 (设备环境)
{cmdb_json}

## 风险判定
{risk_json}

## 攻击类型
{attack_json}

## 相关知识库参考（RAG 检索结果）
{rag_context}

请开始生成处理建议。"""

APPLICATION_SUGGESTION_SYSTEM = """你是一位应用运维工程师。请根据应用告警、资产环境、风险判定和知识库证据，生成可执行的应用告警处理建议。

这是应用日志/业务异常告警，不是 WAF 告警。不得建议无依据的封禁 IP、调整 WAF 规则或宣称发生攻击。优先给出应用日志核查、服务依赖、数据库/接口、权限审计、性能容量和业务负责人协同等建议；有明确安全证据时才补充安全处置。

使用 Markdown，包含：立即核查、排查步骤、按风险处置、修复与预防、升级条件。"""

APPLICATION_SUGGESTION_USER = """请根据以下信息生成应用告警处理建议：

## 应用告警数据
{alert_json}

## CMDB/环境信息
{cmdb_json}

## 风险判定
{risk_json}

## 异常特征
{attack_json}

## 相关运维知识库参考
{rag_context}

请开始生成处理建议。"""


async def generate_analysis_report(
    alert: EnrichedAlert,
    cmdb: CmdbLookupResult,
    risk: RiskAssessment,
    rag_context: str = "",
) -> tuple[str, TokenUsage]:
    """
    生成应用或 WAF 告警分析报告 (LLM)

    Returns:
        (Markdown 格式的分析报告, TokenUsage)
    """
    llm = get_report_llm()

    # 获取攻击类型详细分析
    first_result = alert.results[0] if alert.results else None
    request_uri = first_result.properties_requestUri if first_result else ""
    attack_summary = get_attack_type_summary(request_uri)

    # 构建输入
    # Keep raw query values locally, but send only the masked summary to
    # the external model.  Long callback URLs otherwise cause unstable calls.
    alert_json = json.dumps(_build_alert_prompt_data(alert), ensure_ascii=False, indent=2)
    cmdb_json = json.dumps(cmdb.model_dump(), ensure_ascii=False, indent=2)
    risk_json = json.dumps(risk.model_dump(), ensure_ascii=False, indent=2)
    attack_json = json.dumps(attack_summary, ensure_ascii=False, indent=2)

    is_application = _is_application_alert(alert)
    user_prompt = (APPLICATION_ANALYSIS_REPORT_USER if is_application else ANALYSIS_REPORT_USER).format(
        alert_json=alert_json,
        cmdb_json=cmdb_json,
        risk_json=risk_json,
        attack_json=attack_json,
        rag_context=rag_context or "（未检索到相关知识库内容）",
    )

    try:
        content, response = await call_llm_with_retry(llm, [
            {"role": "system", "content": APPLICATION_ANALYSIS_REPORT_SYSTEM if is_application else ANALYSIS_REPORT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ])
        usage = _extract_token_usage(response)
        content = _ensure_splunk_link(content, alert.splunk_url)
        content += f"\n\n---\n*🤖 AI 生成 ({get_settings().REPORT_MODEL}) · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        logger.info(f"[REPORT] Generated len={len(content)} tokens={usage.total_tokens}")
        return content, usage
    except Exception as e:
        logger.error(f"[REPORT] LLM failed after {LLM_MAX_RETRIES + 1} attempts: {e}")
        fallback = _generate_fallback_report(alert, cmdb, risk, attack_summary)
        est = _estimate_tokens(fallback)
        return fallback, TokenUsage(prompt_tokens=est, completion_tokens=est, total_tokens=est * 2)


async def generate_suggestion(
    alert: EnrichedAlert,
    cmdb: CmdbLookupResult,
    risk: RiskAssessment,
    rag_context: str = "",
) -> tuple[str, TokenUsage]:
    """
    生成告警处理建议 (LLM)

    Returns:
        (Markdown 格式的处理建议, TokenUsage)
    """
    llm = get_report_llm()

    first_result = alert.results[0] if alert.results else None
    request_uri = first_result.properties_requestUri if first_result else ""
    attack_summary = get_attack_type_summary(request_uri)

    alert_json = json.dumps(_build_alert_prompt_data(alert), ensure_ascii=False, indent=2)
    cmdb_json = json.dumps(cmdb.model_dump(), ensure_ascii=False, indent=2)
    risk_json = json.dumps(risk.model_dump(), ensure_ascii=False, indent=2)
    attack_json = json.dumps(attack_summary, ensure_ascii=False, indent=2)

    is_application = _is_application_alert(alert)
    user_prompt = (APPLICATION_SUGGESTION_USER if is_application else SUGGESTION_USER).format(
        alert_json=alert_json,
        cmdb_json=cmdb_json,
        risk_json=risk_json,
        attack_json=attack_json,
        rag_context=rag_context or "（未检索到相关知识库内容）",
    )

    try:
        content, response = await call_llm_with_retry(llm, [
            {"role": "system", "content": APPLICATION_SUGGESTION_SYSTEM if is_application else SUGGESTION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ])
        usage = _extract_token_usage(response)
        content += f"\n\n---\n*🤖 AI 生成 ({get_settings().REPORT_MODEL}) · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        logger.info(f"[SUGGEST] Generated len={len(content)} tokens={usage.total_tokens}")
        return content, usage
    except Exception as e:
        logger.error(f"[SUGGEST] LLM failed after {LLM_MAX_RETRIES + 1} attempts: {e}")
        fallback = _generate_fallback_suggestion(alert, cmdb, risk, attack_summary)
        est = _estimate_tokens(fallback)
        return fallback, TokenUsage(prompt_tokens=est, completion_tokens=est, total_tokens=est * 2)


# ==========================================
# 降级方案 (LLM 不可用时)
# ==========================================

def _generate_fallback_report(
    alert: EnrichedAlert,
    cmdb: CmdbLookupResult,
    risk: RiskAssessment,
    attack_summary: dict,
) -> str:
    """LLM 不可用时的模板化报告。"""
    results = alert.results[0] if alert.results else None
    if _is_application_alert(alert):
        return f"""# 应用告警分析报告：{alert.alert_name}

> **生成状态**：AI 服务暂不可用，以下为基于告警字段、环境信息和风险规则生成的降级报告；请在模型服务恢复后重新分析以获得更完整的原因研判。

## 1. 告警概要
- **所属应用**: {alert.application_code or '-'}
- **告警名称**: {alert.alert_name}
- **触发时间**: {alert.trigger_time}
- **事件数量**: {alert.event_count}
- **综合风险等级**: **{risk.overall_risk}**

## 2. 应用与日志详情
- **资源 ID**: {results.id if results else '-'}
- **应用主机**: {results.properties_hostname if results else '-'}
- **异常摘要**: {results.properties_requestUri[:500] if results and results.properties_requestUri else '-'}
- **告警动作**: {results.properties_action if results else '-'}
- **触发次数**: {results.count if results else '-'}

## 3. 资产与环境信息【证据溯源】
- **环境**: {cmdb.environment}
- **资产匹配方式**: {cmdb.match_type}
- **匹配来源**: {cmdb.source_sheet or '未匹配 CMDB 记录'}
- **资源类型**: {cmdb.resource_type or '-'}

## 4. 原因与影响初判
- **异常特征分类**: {", ".join(risk.attack_types) if risk.attack_types else '未分类'}
- **异常特征风险**: {risk.attack_type_risk}
- **影响范围**: 当前告警资源与对应应用服务；请结合应用日志、接口依赖和业务监控进一步确认。

## 5. 风险评估
| 维度 | 判定 | 详情 |
|------|------|------|
| 环境风险 | {risk.environment_risk} | {risk.environment} |
| 数量风险 | {risk.count_risk} | count={risk.count_value} |
| 异常特征风险 | {risk.attack_type_risk} | {', '.join(risk.attack_types[:5])} |
| **综合** | **{risk.overall_risk}** | - |

## 6. 溯源链接
{f'- [在 Splunk 中查看]({alert.splunk_url})' if alert.splunk_url else '- 原始模拟日志已保存在本地日志目录。'}

---
*📋 应用告警降级报告（AI 服务不可用）· {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    return f"""# WAF 告警分析报告

## 1. 告警概要
- **告警名称**: {alert.alert_name}
- **触发时间**: {alert.trigger_time}
- **事件数量**: {alert.event_count}
- **综合风险等级**: **{risk.overall_risk}**

## 2. 告警数据详情
- **资源 ID**: {results.id if results else '-'}
- **域名**: {results.properties_hostname if results else '-'}
- **攻击路径**: {results.properties_requestUri[:500] if results and results.properties_requestUri else '-'}
- **WAF 动作**: {results.properties_action if results else '-'}
- **触发次数**: {results.count if results else '-'}

## 3. CMDB 资产信息【证据溯源】
- **查询方式**: {"精确匹配 Resource Name: " + cmdb.resource_name if cmdb.match_type == "exact" else "模糊匹配域名"}
- **匹配来源**: {cmdb.source_sheet} (第{cmdb.source_row}行)
- **Environment**: {cmdb.environment}
- **订阅名称**: {cmdb.subscription}
- **资源类型**: {cmdb.resource_type}

## 4. 攻击分析
- **攻击类型**: {", ".join(risk.attack_types) if risk.attack_types else '未分类'}
- **最高攻击风险**: {risk.attack_type_risk}

{chr(10).join([f"- **{d.get('label', '')}** ({d.get('risk', '')}): {', '.join(d.get('matched', [])[:5])}" for d in attack_summary.get('details', [])])}

## 5. 综合风险评估
| 维度 | 判定 | 详情 |
|------|------|------|
| 环境风险 | {risk.environment_risk} | {risk.environment} |
| 数量风险 | {risk.count_risk} | count={risk.count_value} |
| 攻击类型风险 | {risk.attack_type_risk} | {', '.join(risk.attack_types[:5])} |
| **综合** | **{risk.overall_risk}** | - |

## 6. 溯源链接
- [在 Splunk 中查看]({alert.splunk_url})

---
*📋 模板自动填充 (LLM 不可用) · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""


def _generate_fallback_suggestion(
    alert: EnrichedAlert,
    cmdb: CmdbLookupResult,
    risk: RiskAssessment,
    attack_summary: dict,
) -> str:
    """LLM 不可用时的模板化建议。"""
    is_prod = cmdb.environment == "Production"
    risk_level = risk.overall_risk

    if _is_application_alert(alert):
        if risk_level in {"高", "特高"}:
            immediate = ["通知应用负责人和值班运维，确认业务影响范围", "检查同一时间段的应用错误日志、接口状态和依赖服务", "如涉及权限或敏感操作，核查操作者、审计记录和授权变更"]
        elif risk_level == "中":
            immediate = ["记录告警并在工作时间内完成初步排查", "检查应用日志中的异常字段、错误码和调用链", "确认是否存在同类告警持续增长"]
        else:
            immediate = ["记录告警并确认是否为模拟测试或预期业务操作", "核查应用日志，确认异常未影响用户或关键任务"]
        return f"""# 应用告警处理建议：{alert.alert_name}

> **生成状态**：AI 服务暂不可用；以下为基于本次告警字段生成的降级建议，请在模型恢复后重新分析。

## 1. 立即核查
{chr(10).join(f'- [ ] {item}' for item in immediate)}

## 2. 排查步骤
- [ ] 按告警时间检索 `{alert.application_code or '应用'}` 的日志，定位错误码、异常堆栈或失败请求。
- [ ] 检查相关接口、数据库、消息队列或第三方服务的可用性与延迟。
- [ ] 对照发布、配置变更和权限变更记录，确认是否存在关联操作。

## 3. 按风险处置
- **当前环境**: {cmdb.environment}
- **当前风险等级**: {risk.overall_risk}
- 非生产/模拟环境：优先复现、记录和修复，避免将测试异常当成生产安全事件。
- 生产环境：如确认影响业务，按应用故障流程升级并同步业务负责人。

## 4. 修复与预防
- [ ] 为该告警规则补充明确的业务阈值、错误码和排除条件。
- [ ] 完善应用日志字段、依赖监控和告警关联规则。
- [ ] 将本次根因与处置结果记录到应用运维知识库。

## 5. 升级条件
- 同类异常持续增加或影响核心业务功能。
- 发现数据完整性、权限越权或敏感数据风险证据。
- 在生产环境确认服务不可用、明显性能退化或用户受影响。

---
*📋 应用告警降级建议（AI 服务不可用）· {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    # 根据风险等级动态生成建议
    if risk_level == "高":
        urgent_actions = [
            "立即通知系统经理和应用负责人",
            "在 Splunk 中搜索域名相关日志，确认攻击范围",
            "检查 WAF 是否成功拦截所有恶意请求",
            "如果 WAF 未完全拦截，考虑临时封禁攻击源 IP",
        ]
        investigation = [
            "分析 Splunk 日志，确认攻击时间线和来源",
            "检查是否有成功绕过 WAF 的请求（返回码非 403）",
            "联系应用团队确认是否有异常访问记录",
        ]
    elif risk_level == "中":
        urgent_actions = [
            "标记此告警，在工作时间内完成调查",
            "在 Splunk 中快速确认攻击规模",
        ]
        investigation = [
            "分析攻击路径的威胁程度",
            "确认是否为自动化扫描工具行为",
        ]
    else:
        urgent_actions = ["记录告警信息，无需紧急响应"]
        investigation = ["定期审查类似告警模式，识别潜在趋势"]

    env_note = "**⚠️ 生产环境** - 所有变更需走 Change 流程，操作需在变更窗口内执行。" if is_prod else "**ℹ️ 测试环境** - 风险较低，可在工作时间内处理。"

    return f"""# WAF 告警处理建议

## 1. 立即行动
{chr(10).join([f'- [ ] {a}' for a in urgent_actions])}

## 2. 调查步骤
{chr(10).join([f'- [ ] {a}' for a in investigation])}

## 3. 环境说明
{env_note}

## 4. 处置建议
- **生产环境**: 所有操作需获得系统经理批准，按变更流程执行
- **测试环境**: 可灵活处置，建议记录处置过程供后续参考

## 5. 后续加固
- [ ] 评估是否需要调整 WAF 规则
- [ ] 检查同类域名是否有相同漏洞
- [ ] 更新运维手册中的告警处理记录

## 6. 升级条件
- 如 count 持续上升 → 升级为事件处理
- 如发现成功绕过 WAF 的请求 → 立即升级
- 如影响生产业务 → 触发应急响应流程

---
*📋 模板自动填充 (LLM 不可用) · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
