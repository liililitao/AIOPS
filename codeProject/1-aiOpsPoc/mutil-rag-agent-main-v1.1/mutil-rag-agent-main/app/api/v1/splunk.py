"""Splunk 告警接收端点 — 接收告警 → Agent 处理 → 写入 Splunk.

POST /api/v1/splunk/alert
  接收结构: {alert_type, severity, host_ip, description, timestamp, ...}
  返回: {risk_level, priority, report, ...} + 后台写入 Splunk

整个链路:
  1. 接收告警 JSON
  2. 查 CMDB 获取设备信息 (query_cmdb)
  3. 跑 Agent 诊断 (复用 LangGraph skill_router → planner → executor → replanner)
  4. 从诊断报告中提取 risk_level 和 priority
  5. 异步写入 Splunk HEC
  6. 返回诊断结果给调用方
"""

import asyncio
from typing import Dict, Any

from fastapi import APIRouter, Request
from loguru import logger

from app.schemas.common import ApiResponse
from app.services.splunk_forwarder import forward_to_splunk

router = APIRouter(prefix="/splunk", tags=["splunk"])


def _parse_diagnosis_report(report: str) -> Dict[str, Any]:
    """从诊断报告中提取结构化字段.

    Agent 输出的报告是 Markdown 格式, 这里用简单规则提取:
      - risk_level: 从 '风险等级' 行提取数字
      - priority: 根据 risk_level 映射
    """
    risk_level = 3  # 默认中等
    priority = "中"

    # 尝试从报告中提取风险等级
    for line in (report or "").split("\n"):
        line_stripped = line.strip()
        if "风险等级" in line_stripped or "risk" in line_stripped.lower():
            import re
            nums = re.findall(r'[1-5]', line_stripped)
            if nums:
                risk_level = int(nums[0])
                break

    if risk_level >= 5:
        priority = "紧急"
    elif risk_level >= 4:
        priority = "高"
    elif risk_level >= 3:
        priority = "中"
    else:
        priority = "低"

    return {
        "risk_level": risk_level,
        "priority": priority,
        "report": report,
    }


async def _run_diagnosis(alert: Dict[str, Any]) -> Dict[str, Any]:
    """运行 Agent 诊断流程.

    把告警信息拼成 query, 走完整的 LangGraph Agent 流程.
    """
    from app.agents import build_aiops_graph

    query = (
        f"收到一条告警, 请诊断:\n"
        f"- 告警类型: {alert.get('title', '')} ({alert.get('alert_type', '')})\n"
        f"- 严重程度: {alert.get('severity', '')}\n"
        f"- 设备 IP: {alert.get('host_ip', '')}\n"
        f"- 告警描述: {alert.get('description', '')}\n"
    )

    graph = build_aiops_graph()
    result = await graph.ainvoke(
        {"input": query, "permission_mode": "normal"},
        config={"recursion_limit": 21},
    )

    report = result.get("response", "") or ""
    diagnosis = _parse_diagnosis_report(report)

    # 把 CMDB 信息合并进去 (如果 Agent 没查到)
    if alert.get("host_ip"):
        try:
            from app.tools.cmdb_tool import _MOCK_CMDB, _UNKNOWN_TEMPLATE
            cmdb_info = _MOCK_CMDB.get(alert["host_ip"], _UNKNOWN_TEMPLATE)
            diagnosis["app_name"] = cmdb_info.get("app_name", "")
            diagnosis["owner"] = cmdb_info.get("owner", "")
            diagnosis["business_level"] = cmdb_info.get("business_level", "")
        except Exception:
            pass

    return diagnosis


@router.post("/alert", summary="接收 Splunk 告警并触发 AIOps 诊断")
async def receive_splunk_alert(request: Request) -> ApiResponse[Dict[str, Any]]:
    try:
        payload = await request.json()
    except Exception:
        body = await request.body()
        logger.warning(f"[SplunkAlert] JSON parse failed, raw: {body[:200]}")
        return ApiResponse.error(code="BAD_JSON", message="Request body must be valid JSON")

    logger.info(f"[SplunkAlert] 收到告警: type={payload.get('alert_type')} "
                f"ip={payload.get('host_ip')} severity={payload.get('severity')}")

    try:
        # 跑 Agent 诊断
        diagnosis = await _run_diagnosis(payload)
    except Exception as e:
        logger.exception(f"[SplunkAlert] Agent 诊断失败: {e}")
        diagnosis = {
            "risk_level": 5,
            "priority": "紧急",
            "report": f"# 诊断失败\n\nAgent 处理异常: {e}\n\n请人工介入排查。",
            "app_name": "未知",
            "owner": "未知",
            "business_level": "未知",
        }

    # 异步写 Splunk (fire-and-forget, 不影响响应)
    asyncio.create_task(
        _safe_forward(payload, diagnosis)
    )

    return ApiResponse.success(
        data={
            "alert_type": payload.get("alert_type", ""),
            "host_ip": payload.get("host_ip", ""),
            "risk_level": diagnosis.get("risk_level", 3),
            "priority": diagnosis.get("priority", "中"),
            "diagnosis_summary": (diagnosis.get("report", "") or "")[:300],
        },
        message=f"诊断完成, 风险等级: {diagnosis.get('risk_level', '?')}, "
                f"优先级: {diagnosis.get('priority', '?')}",
    )


async def _safe_forward(raw_alert: Dict[str, Any], diagnosis: Dict[str, Any]) -> None:
    """异步写入 Splunk, 失败不影响主流程."""
    try:
        ok = await forward_to_splunk(raw_alert, diagnosis)
        if ok:
            logger.info("[SplunkAlert] 已写入 Splunk")
        else:
            logger.warning("[SplunkAlert] 写入 Splunk 失败, 但诊断已完成")
    except Exception as e:
        logger.warning(f"[SplunkAlert] 写入 Splunk 异常: {e}")
