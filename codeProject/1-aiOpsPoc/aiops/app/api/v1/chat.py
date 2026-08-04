"""
RAG 问答 API 路由
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.core.llm import get_rag_chat_llm
from app.services.alert_service import get_alert_detail

logger = logging.getLogger("aiops.api.chat")
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    alert_id: str = ""


CHAT_SYSTEM_PROMPT = """你是一个 AIOps 智能运维助手，专门帮助运维人员分析 WAF 告警。

你的职责：
1. 基于告警数据回答用户的问题
2. 提供运维相关的专业建议
3. 解释告警中的技术细节
4. 给出可执行的操作步骤

要求：
- 回答准确、专业、简洁
- 如果不确定，如实告知
- 涉及生产环境操作时，提醒用户注意变更流程
- 如果聊天记录包含分析报告和处理建议，可以参考引用"""


def _build_alert_context(alert, risk_details, analysis_report, suggestion) -> str:
    """从告警详情构建 LLM 上下文"""
    parts = ["## 当前告警上下文\n"]

    if alert:
        parts.append(f"- 告警名称: {alert.alert_name}")
        parts.append(f"- 触发时间: {alert.trigger_time}")
        parts.append(f"- 风险等级: {alert.risk_level}")

        if alert.results:
            r = alert.results[0]
            parts.append(f"- 域名: {r.properties_hostname}")
            parts.append(f"- 攻击路径: {r.properties_requestUri[:500]}")
            parts.append(f"- WAF 动作: {r.properties_action}")
            parts.append(f"- 触发次数: {r.count}")
            parts.append(f"- 资源 ID: {r.id}")

    if risk_details:
        parts.append(f"\n## 风险评估")
        parts.append(f"- 环境风险: {risk_details.environment_risk} ({risk_details.environment})")
        parts.append(f"- 数量风险: {risk_details.count_risk} (count={risk_details.count_value})")
        parts.append(f"- 攻击类型风险: {risk_details.attack_type_risk}")
        if risk_details.attack_types:
            parts.append(f"- 攻击类型: {', '.join(risk_details.attack_types)}")
        parts.append(f"- 综合风险等级: {risk_details.overall_risk}")

    if analysis_report:
        parts.append(f"\n## 分析报告摘要\n{analysis_report[:2000]}")

    if suggestion:
        parts.append(f"\n## 处理建议摘要\n{suggestion[:2000]}")

    return "\n".join(parts)


@router.post("")
async def chat(request: ChatRequest):
    """基于告警上下文的 RAG 问答"""
    settings = get_settings()

    # 构建告警上下文
    if request.alert_id:
        detail = get_alert_detail(request.alert_id)
        if detail:
            context = _build_alert_context(
                detail.alert,
                detail.risk_details,
                detail.analysis_report,
                detail.suggestion,
            )
        else:
            context = "（未找到该告警数据）"
    else:
        context = "（用户未选择告警）"

    user_msg = f"{context}\n\n用户提问: {request.question}"

    try:
        import asyncio
        llm = get_rag_chat_llm()
        response = await asyncio.wait_for(
            llm.ainvoke([
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ]),
            timeout=120.0,
        )
        answer = response.content if hasattr(response, "content") else str(response)
        return {"answer": answer, "alert_id": request.alert_id}
    except asyncio.TimeoutError:
        logger.error("[CHAT] LLM timeout")
        raise HTTPException(status_code=504, detail="AI 服务响应超时，请稍后重试")
    except Exception as e:
        logger.error(f"[CHAT] Request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI 服务暂时不可用: {str(e)}")
