"""Splunk Result Forwarder — 把 Agent 诊断结果写入 Splunk HEC.

职责:
  1. 格式化诊断结果 (风险等级、优先级、报告摘要)
  2. 构造 HEC 兼容的 JSON payload
  3. HTTPS POST 到 Splunk HTTP Event Collector (:8088)

设计要点:
  - 写失败不阻塞诊断流程 (fire-and-forget + 日志告警)
  - sourcetype="_json" 让 Splunk 自动解析字段
  - index="aiops_results" 与告警原始数据隔离

用法:
  from app.services.splunk_forwarder import forward_to_splunk
  await forward_to_splunk(alert_input, diagnosis_result)
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from app.config import settings

# Splunk HEC 配置
SPLUNK_HOST = "localhost"
SPLUNK_HEC_PORT = 8088
SPLUNK_HEC_TOKEN = "09b8d03c-af42-4b25-9af6-174fa10f3ded"
SPLUNK_HEC_URL = f"https://{SPLUNK_HOST}:{SPLUNK_HEC_PORT}/services/collector"
SPLUNK_INDEX = "aiops_results"


def _build_index_time() -> str:
    """生成东八区 iso 时间戳."""
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _format_for_splunk(
    raw_alert: Dict[str, Any],
    diagnosis: Dict[str, Any],
) -> Dict[str, Any]:
    """把诊断结果格式化成 Splunk 友好的扁平结构.

    字段规划 (这些字段会出现在 Splunk Dashboard):
      - alert_type, severity, host_ip     → 来自原始告警
      - app_name, owner, business_level    → 来自 CMDB
      - risk_level, priority               → Agent 评估结果
      - diagnosis_summary                  → 诊断摘要 (200 字)
      - full_report                        → 完整诊断报告
      - timestamp                          → 索引时间
    """
    now = _build_index_time()
    risk = diagnosis.get("risk_level", 3) or 3

    # 优先级映射
    if risk >= 5:
        priority = "紧急"
    elif risk >= 4:
        priority = "高"
    elif risk >= 3:
        priority = "中"
    else:
        priority = "低"

    return {
        # 告警原始字段
        "alert_type": raw_alert.get("alert_type", "unknown"),
        "title": raw_alert.get("title", ""),
        "severity": raw_alert.get("severity", "medium"),
        "host_ip": raw_alert.get("host_ip", ""),
        "alert_description": raw_alert.get("description", ""),

        # CMDB 关联字段
        "app_name": diagnosis.get("app_name", ""),
        "owner": diagnosis.get("owner", ""),
        "business_level": diagnosis.get("business_level", ""),

        # Agent 诊断结果
        "risk_level": risk,
        "priority": priority,
        "diagnosis_summary": (diagnosis.get("report", "") or "")[:300],
        "full_report": diagnosis.get("report", ""),

        # 元数据
        "source": "aiops_agent",
        "sourcetype": "_json",
        "timestamp": now,
        "index_time": now,
    }


async def forward_to_splunk(
    raw_alert: Dict[str, Any],
    diagnosis: Dict[str, Any],
) -> bool:
    """把诊断结果写入 Splunk HEC.

    Args:
        raw_alert: 原始告警 JSON (来自 alert_simulator)
        diagnosis: Agent 诊断结果 (含 risk_level, report 等)

    Returns:
        True 写入成功, False 写入失败
    """
    event = _format_for_splunk(raw_alert, diagnosis)

    payload = {
        "event": event,
        "sourcetype": "_json",
        "index": "aiops_results",
    }

    headers = {
        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            resp = await client.post(SPLUNK_HEC_URL, json=payload, headers=headers)
            if resp.status_code == 200:
                logger.info(
                    f"[SplunkForwarder] 已写入: alert={event['alert_type']} "
                    f"risk={event['risk_level']} priority={event['priority']}"
                )
                return True
            else:
                logger.warning(
                    f"[SplunkForwarder] HEC 返回 {resp.status_code}: {resp.text[:200]}"
                )
                return False
    except Exception as e:
        logger.warning(f"[SplunkForwarder] 写入失败: {type(e).__name__}: {e}")
        return False
