"""
报告生成服务 - LLM 生成分析报告和处理建议
"""

import asyncio
import json
import logging
from datetime import datetime

from app.config import get_settings
from app.core.llm import get_report_llm, call_llm_with_retry, LLM_MAX_RETRIES
from app.schemas.alert import EnrichedAlert, TokenUsage
from app.schemas.cmdb import CmdbLookupResult
from app.schemas.risk import RiskAssessment
from app.core.attack_classifier import get_attack_type_summary

logger = logging.getLogger("aiops.report")


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
# 分析报告 Prompt
# ==========================================

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

请开始生成处理建议。"""


async def generate_analysis_report(
    alert: EnrichedAlert,
    cmdb: CmdbLookupResult,
    risk: RiskAssessment,
) -> tuple[str, TokenUsage]:
    """
    生成 WAF 告警分析报告 (LLM)

    Returns:
        (Markdown 格式的分析报告, TokenUsage)
    """
    llm = get_report_llm()

    # 获取攻击类型详细分析
    first_result = alert.results[0] if alert.results else None
    request_uri = first_result.properties_requestUri if first_result else ""
    attack_summary = get_attack_type_summary(request_uri)

    # 构建输入
    alert_json = json.dumps(alert.model_dump(), ensure_ascii=False, indent=2)
    cmdb_json = json.dumps(cmdb.model_dump(), ensure_ascii=False, indent=2)
    risk_json = json.dumps(risk.model_dump(), ensure_ascii=False, indent=2)
    attack_json = json.dumps(attack_summary, ensure_ascii=False, indent=2)

    user_prompt = ANALYSIS_REPORT_USER.format(
        alert_json=alert_json,
        cmdb_json=cmdb_json,
        risk_json=risk_json,
        attack_json=attack_json,
    )

    try:
        content, response = await call_llm_with_retry(llm, [
            {"role": "system", "content": ANALYSIS_REPORT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ])
        usage = _extract_token_usage(response)
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

    alert_json = json.dumps(alert.model_dump(), ensure_ascii=False, indent=2)
    cmdb_json = json.dumps(cmdb.model_dump(), ensure_ascii=False, indent=2)
    risk_json = json.dumps(risk.model_dump(), ensure_ascii=False, indent=2)
    attack_json = json.dumps(attack_summary, ensure_ascii=False, indent=2)

    user_prompt = SUGGESTION_USER.format(
        alert_json=alert_json,
        cmdb_json=cmdb_json,
        risk_json=risk_json,
        attack_json=attack_json,
    )

    try:
        content, response = await call_llm_with_retry(llm, [
            {"role": "system", "content": SUGGESTION_SYSTEM},
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
    """LLM 不可用时的模板化报告"""
    results = alert.results[0] if alert.results else None
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
    """LLM 不可用时的模板化建议"""
    is_prod = cmdb.environment == "Production"
    risk_level = risk.overall_risk

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
