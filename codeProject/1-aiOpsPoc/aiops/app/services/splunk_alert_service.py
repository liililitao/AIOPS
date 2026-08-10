"""Splunk REST 告警同步服务。

该模块通过 Splunk 管理端口的 search API 读取告警。同步结果会缓存到本地，
因此 Splunk 暂时不可用时，页面仍可展示上一次成功同步的数据。
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger("aiops.splunk_alert_service")


class SplunkSyncError(RuntimeError):
    """Splunk 告警同步失败。"""


def _cache_path() -> Path:
    return get_settings().project_root / "data" / "splunk_alerts.json"


def get_cached_remote_alerts() -> list[dict[str, Any]]:
    """读取最近一次成功同步的告警，不会访问网络。"""
    path = _cache_path()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        alerts = payload.get("alerts", [])
        return alerts if isinstance(alerts, list) else []
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[SPLUNK] Cannot read alert cache: %s", exc)
        return []


async def sync_remote_alerts() -> dict[str, Any]:
    """从 Splunk 拉取告警并更新本地缓存。"""
    settings = get_settings()
    if not settings.SPLUNK_ENABLED:
        return {
            "status": "disabled",
            "message": "Splunk 数据源未启用，页面展示本地已处理告警",
            "total": len(get_cached_remote_alerts()),
        }
    if not settings.SPLUNK_BASE_URL or not settings.SPLUNK_TOKEN:
        raise SplunkSyncError(
            "Splunk 数据源未配置完整，请设置 SPLUNK_BASE_URL 和 SPLUNK_TOKEN"
        )

    query = _build_query(
        settings.SPLUNK_ALERT_QUERY,
        settings.SPLUNK_ALERT_INDEX,
        settings.SPLUNK_ALERT_MAX_RESULTS,
    )
    records = await _export_search_results(
        base_url=settings.SPLUNK_BASE_URL,
        token=settings.SPLUNK_TOKEN,
        query=query,
        earliest_time=settings.SPLUNK_ALERT_EARLIEST_TIME,
        latest_time=settings.SPLUNK_ALERT_LATEST_TIME,
        timeout_seconds=settings.SPLUNK_TIMEOUT_SECONDS,
        verify_tls=settings.SPLUNK_VERIFY_TLS,
    )
    synced_at = datetime.now(timezone.utc).isoformat()
    alerts = [_normalise_alert(record, synced_at) for record in records]
    alerts.sort(key=lambda item: item.get("trigger_time", ""), reverse=True)
    _write_cache({
        "source": "splunk",
        "synced_at": synced_at,
        "query": query,
        "alerts": alerts,
    })
    logger.info("[SPLUNK] Synced %s alerts", len(alerts))
    return {
        "status": "ok",
        "message": f"已从 Splunk 同步 {len(alerts)} 条告警",
        "total": len(alerts),
        "synced_at": synced_at,
    }


def get_cached_remote_alert_detail(alert_id: str) -> dict[str, Any] | None:
    """按页面 ID 查找一条已缓存的 Splunk 告警详情。"""
    for alert in get_cached_remote_alerts():
        if alert.get("id") == alert_id:
            return alert
    return None


def _build_query(configured_query: str, index: str, limit: int) -> str:
    if configured_query.strip():
        return configured_query.strip()
    safe_index = index.strip()
    if not safe_index or any(char.isspace() for char in safe_index):
        raise SplunkSyncError("SPLUNK_ALERT_INDEX 必须是一个有效的索引名")
    max_results = max(1, min(int(limit), 5000))
    return f"search index={safe_index} | sort 0 - _time | head {max_results}"


async def _export_search_results(
    *,
    base_url: str,
    token: str,
    query: str,
    earliest_time: str,
    latest_time: str,
    timeout_seconds: int,
    verify_tls: bool,
) -> list[dict[str, Any]]:
    endpoint = base_url.rstrip("/") + "/services/search/jobs/export"
    request_data = {
        "search": query,
        "output_mode": "json",
        "earliest_time": earliest_time,
        "latest_time": latest_time,
    }
    headers = {"Authorization": f"Splunk {token}"}
    timeout = httpx.Timeout(max(1, timeout_seconds))
    records: list[dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(
            verify=verify_tls,
            timeout=timeout,
        ) as client:
            async with client.stream(
                "POST", endpoint, data=request_data, headers=headers
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    raise SplunkSyncError(
                        f"Splunk 查询失败（HTTP {response.status_code}）：{body[:300]}"
                    )
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug("[SPLUNK] Ignoring non-JSON export line")
                        continue
                    result = payload.get("result")
                    if isinstance(result, dict):
                        records.append(result)
    except httpx.HTTPError as exc:
        raise SplunkSyncError(f"无法连接 Splunk：{exc}") from exc

    return records


def _normalise_alert(record: dict[str, Any], synced_at: str) -> dict[str, Any]:
    """将 Splunk 字段和 _raw JSON 统一为页面可展示的告警结构。"""
    raw_payload = _read_raw_json(record.get("_raw"))
    data = {**raw_payload, **record}
    raw_results = raw_payload.get("results", data.get("results", []))
    results = _normalise_results(raw_results, data)
    alert_name = _text(
        data.get("alert_name") or data.get("savedsearch_name")
        or data.get("rule_name") or "Splunk 告警"
    )
    trigger_time = _text(data.get("trigger_time") or data.get("_time") or synced_at)
    risk_level = _normalise_risk(data.get("risk_level"))
    event_count = _number(data.get("event_count") or data.get("count"))
    hostname = _text(data.get("properties_hostname") or data.get("hostname"))
    fingerprint = "|".join((
        _text(data.get("_cd")), _text(data.get("_time")), alert_name,
        trigger_time, hostname, _text(data.get("_raw")),
    ))
    alert_id = "splunk_" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:24]

    return {
        "id": alert_id,
        "source": "splunk",
        "alert_name": alert_name,
        "application_code": _text(
            data.get("application_code") or data.get("application") or data.get("app_code")
        ),
        "trigger_time": trigger_time,
        "trigger_time_utc": _text(data.get("trigger_time_utc")),
        "event_count": event_count,
        "trigger_reason": _text(data.get("trigger_reason") or data.get("reason")),
        "splunk_url": _text(data.get("splunk_url")),
        "search_terms": _text(data.get("search_terms")),
        "full_spl": _text(data.get("full_spl")),
        "risk_level": risk_level,
        "results": results,
        "risk_details": {
            "environment_risk": "未知",
            "environment": "Unknown",
            "count_risk": "未知",
            "count_value": event_count,
            "attack_type_risk": "未知",
            "attack_types": [],
            "overall_risk": risk_level,
            "assessed_at": synced_at,
        },
        "processed_at": synced_at,
    }


def _normalise_results(value: Any, data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = []
    if isinstance(value, dict):
        value = [value]
    if isinstance(value, list):
        items = [item for item in value if isinstance(item, dict)]
        if items:
            return items
    return [{
        "id": _text(data.get("id") or data.get("resource_id")),
        "properties_hostname": _text(
            data.get("properties_hostname") or data.get("hostname")
        ),
        "properties_requestUri": _text(
            data.get("properties_requestUri") or data.get("request_uri")
        ),
        "properties_action": _text(
            data.get("properties_action") or data.get("action")
        ),
        "count": str(_number(data.get("count") or data.get("event_count"))),
    }]


def _read_raw_json(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalise_risk(value: Any) -> str:
    raw = _text(value).strip().lower()
    if raw in {"high", "critical", "高"}:
        return "高"
    if raw in {"medium", "moderate", "中"}:
        return "中"
    if raw in {"low", "info", "低"}:
        return "低"
    return "未知"


def _number(value: Any) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _write_cache(payload: dict[str, Any]) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
