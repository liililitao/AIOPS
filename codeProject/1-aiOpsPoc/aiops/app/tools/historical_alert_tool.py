"""Agent 调用的历史相似告警检索 Tool。"""

from __future__ import annotations

import json
import logging
from functools import lru_cache

from langchain.tools import tool

from app.services.historical_alert_index import HistoricalAlertIndex

logger = logging.getLogger("aiops.historical_alert_tool")


@lru_cache(maxsize=1)
def _get_default_index() -> HistoricalAlertIndex:
    from app.config import get_settings
    settings = get_settings()
    return HistoricalAlertIndex(collection=settings.HISTORICAL_ALERT_COLLECTION,
                                dimension=settings.embedding_dimension)


def run_historical_alert_search(query: str, top_k: int = 3, *, index=None) -> dict:
    query = str(query or "").strip()
    if not query:
        return {"success": False, "query": query, "error_code": "query_required",
                "message": "历史告警检索词不能为空", "results": []}
    try:
        limit = max(1, min(int(top_k), 10))
    except (TypeError, ValueError):
        return {"success": False, "query": query, "error_code": "invalid_top_k",
                "message": "top_k 必须是 1 到 10 之间的整数", "results": []}
    try:
        return {"success": True, "query": query,
                "results": (index or _get_default_index()).search(query, limit)}
    except Exception as exc:
        logger.warning("Historical alert search failed: %s", exc)
        return {"success": False, "query": query, "error_code": "history_search_unavailable",
                "message": "历史告警检索暂不可用，请稍后重试", "results": []}


@tool
def search_historical_alerts(query: str, top_k: int = 3) -> str:
    """检索历史相似告警，返回风险、分析和建议的压缩摘要证据。"""
    return json.dumps(run_historical_alert_search(query, top_k), ensure_ascii=False)
