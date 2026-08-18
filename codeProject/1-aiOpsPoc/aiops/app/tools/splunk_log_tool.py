"""Agent-facing bounded Splunk log investigation Tool (同事提供实现的项目适配版)。"""

from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import Literal

from langchain.tools import ToolRuntime, tool
from pydantic import ValidationError

from app.core.alert_tool_runtime import AlertToolContext
from app.services.splunk_investigation import FileAlertContextRepository, InvestigationRequest, SplunkInvestigationService

logger = logging.getLogger("aiops.splunk_log_tool")
InvestigationArgument = Literal["temporal_pattern", "source_concentration", "target_distribution", "historical_baseline"]


@lru_cache(maxsize=1)
def _get_default_service() -> SplunkInvestigationService:
    from app.config import get_settings
    from app.services.splunk_alert_service import SplunkRestExecutor
    settings = get_settings()
    return SplunkInvestigationService(
        FileAlertContextRepository(settings.project_root),
        SplunkRestExecutor(base_url=settings.SPLUNK_BASE_URL, token=settings.SPLUNK_TOKEN,
                           timeout_seconds=settings.SPLUNK_TIMEOUT_SECONDS, verify_tls=settings.SPLUNK_VERIFY_TLS),
        index=settings.SPLUNK_LOG_INDEX, max_results=settings.SPLUNK_INVESTIGATION_MAX_RESULTS,
        max_items=settings.SPLUNK_INVESTIGATION_MAX_ITEMS, max_text_chars=settings.SPLUNK_INVESTIGATION_MAX_TEXT_CHARS,
        item_budget_chars=settings.SPLUNK_INVESTIGATION_ITEM_BUDGET_CHARS, total_budget_chars=settings.SPLUNK_INVESTIGATION_TOTAL_BUDGET_CHARS,
    )


def run_splunk_investigation(alert_id: str, investigations: list[InvestigationArgument], window_minutes: int = 30, *, service: SplunkInvestigationService | None = None) -> dict:
    try:
        request = InvestigationRequest(alert_id=alert_id, investigations=investigations, window_minutes=window_minutes)
        return asyncio.run((service or _get_default_service()).investigate(request))
    except ValidationError:
        return _error(alert_id, "invalid_request")
    except ValueError as exc:
        return _error(alert_id, "splunk_not_configured" if str(exc) == "splunk_not_configured" else "invalid_request")
    except Exception as exc:
        logger.warning("Splunk investigation unavailable: %s", exc)
        return _error(alert_id, "splunk_search_unavailable")


@tool
def investigate_splunk_logs(
    investigations: list[InvestigationArgument],
    runtime: ToolRuntime[AlertToolContext],
    window_minutes: int = 30,
) -> str:
    """获取当前告警的受控 Splunk 日志证据；不接受 SPL、索引或自定义过滤条件。"""
    context = runtime.context
    return json.dumps(
        run_splunk_investigation(
            context.alert_id,
            investigations,
            window_minutes,
            service=context.splunk_service,
        ),
        ensure_ascii=False,
    )


def _error(alert_id: str, code: str) -> dict:
    return {"success": False, "alert_id": str(alert_id or ""), "evidence_type": "splunk_log", "evidence": [], "warnings": [], "error_code": code, "truncated": False}
