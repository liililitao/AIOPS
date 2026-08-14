"""同事提供的受控 Splunk 日志调查服务。

本模块只允许固定的只读 SPL 模板；Agent 只能选择调查类型和固定时间窗，不能
传入任意 SPL、索引或字段。返回结果经过裁剪后才会交给模型和写入 Agent 运行记录。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

InvestigationName = Literal["temporal_pattern", "source_concentration", "target_distribution", "historical_baseline"]
ALLOWED_WINDOWS = {15, 30, 60, 180, 1440}
FORBIDDEN_COMMANDS = {"collect", "outputlookup", "delete", "rest", "sendemail", "script", "map", "loadjob"}
ALLOWED_COMMANDS = {"search", "bin", "stats", "sort", "head", "timechart", "fields", "table", "where", "dedup", "eval"}


class InvestigationRequest(BaseModel):
    alert_id: str = Field(min_length=1, max_length=512)
    investigations: list[InvestigationName] = Field(min_length=1, max_length=3)
    window_minutes: int = 30

    @model_validator(mode="after")
    def validate_boundaries(self):
        if self.window_minutes not in ALLOWED_WINDOWS:
            raise ValueError("window_minutes must be one of 15, 30, 60, 180, 1440")
        if len(set(self.investigations)) != len(self.investigations):
            raise ValueError("investigations must not contain duplicates")
        return self


@dataclass(frozen=True)
class AlertLogContext:
    alert_id: str
    alert_type: str
    trigger_time: datetime
    hostname: str
    resource_id: str = ""
    action: str = ""
    current_count: int = 0


@dataclass(frozen=True)
class SplunkSearchRequest:
    template_id: str
    spl: str
    earliest_time: datetime
    latest_time: datetime
    max_results: int


@dataclass(frozen=True)
class SplunkSearchResponse:
    rows: list[dict]
    search_id: str = ""
    duration_ms: int = 0


class AlertContextRepository(Protocol):
    def get(self, alert_id: str) -> AlertLogContext | None: ...


class SplunkSearchExecutor(Protocol):
    async def search(self, request: SplunkSearchRequest) -> SplunkSearchResponse: ...


class FileAlertContextRepository:
    """从已增强 WAF 告警或 Splunk 缓存解析调查上下文。"""

    _CASE_ID = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})/(?P<stem>[A-Za-z0-9_.-]+)$")

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    def get(self, alert_id: str) -> AlertLogContext | None:
        match = self._CASE_ID.fullmatch(str(alert_id or ""))
        if match:
            path = self.project_root / "output" / "enriched_alerts" / match.group("date") / f"{match.group('stem')}.json"
            return self._read(alert_id, path)
        if str(alert_id or "").startswith("splunk_"):
            cache = self.project_root / "data" / "splunk_alerts.json"
            try:
                for item in json.loads(cache.read_text(encoding="utf-8")).get("alerts", []):
                    if isinstance(item, dict) and item.get("id") == alert_id:
                        return _context_from_alert_data(alert_id, item)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
        return None

    @staticmethod
    def _read(alert_id: str, path: Path) -> AlertLogContext | None:
        try:
            return _context_from_alert_data(alert_id, json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None


class SplunkInvestigationService:
    def __init__(self, context_repository: AlertContextRepository, executor: SplunkSearchExecutor, *, index: str,
                 max_results: int = 200, max_items: int = 10, max_text_chars: int = 160,
                 item_budget_chars: int = 4000, total_budget_chars: int = 12000):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", str(index or "")):
            raise ValueError("invalid Splunk index")
        self.context_repository, self.executor, self.index = context_repository, executor, index
        self.max_results, self.max_items = max(1, min(int(max_results), 500)), max(1, min(int(max_items), 20))
        self.max_text_chars = max(32, min(int(max_text_chars), 500))
        self.item_budget_chars, self.total_budget_chars = max(1000, int(item_budget_chars)), max(int(item_budget_chars), int(total_budget_chars))

    async def investigate(self, request: InvestigationRequest) -> dict:
        context = self.context_repository.get(request.alert_id)
        if context is None:
            return _error(request.alert_id, "alert_not_found")
        # 同事给出的 SPL 模板面向 ApplicationGatewayFirewallLog。应用模拟告警
        # 会完整记录为本次 Tool 已调用但上下文不支持，而不会伪造 Splunk 证据。
        if context.alert_type != "waf" or not context.hostname:
            return _error(request.alert_id, "unsupported_alert_context")
        evidence, warnings = [], []
        for investigation in request.investigations:
            try:
                search = self._build_search(context, investigation, request.window_minutes)
                _validate_read_only_spl(search.spl)
                response = await self.executor.search(search)
                evidence.append(self._make_evidence(investigation, search, response, context))
            except Exception:
                warnings.append({"investigation": investigation, "error_code": "splunk_search_unavailable"})
        result = {"success": bool(evidence), "alert_id": request.alert_id, "evidence_type": "splunk_log",
                  "evidence": evidence, "warnings": warnings, "truncated": any(x.get("truncated") for x in evidence)}
        if not evidence:
            result["error_code"] = "splunk_search_unavailable"
        return self._fit_total_budget(result)

    def _base_search(self, context: AlertLogContext) -> str:
        aliases = " | eval aiops_hostname=coalesce('properties.hostname',properties_hostname), aiops_action=coalesce('properties.action',properties_action), aiops_client_ip=coalesce('properties.clientIp',properties_clientIp,clientIP,client_ip), aiops_request_uri=coalesce('properties.requestUri',properties_requestUri)"
        query = f"search index={self.index} category=ApplicationGatewayFirewallLog" + aliases
        query += f" | search aiops_hostname={_spl_literal(context.hostname)}"
        return query + (f" aiops_action={_spl_literal(context.action)}" if context.action else "")

    def _build_search(self, context: AlertLogContext, investigation: InvestigationName, window: int) -> SplunkSearchRequest:
        trigger = _as_utc(context.trigger_time)
        if investigation == "historical_baseline":
            return SplunkSearchRequest("waf.historical_baseline.v1", f"{self._base_search(context)} | timechart span=1h count", trigger - timedelta(days=7), trigger - timedelta(seconds=1), self.max_results)
        half = timedelta(minutes=window / 2)
        if investigation == "temporal_pattern":
            bucket = 5 if window <= 60 else 10 if window <= 180 else 60
            spl, template = f"{self._base_search(context)} | bin _time span={bucket}m | stats count by _time | sort 0 _time", "waf.temporal_pattern.v1"
        elif investigation == "source_concentration":
            spl, template = f"{self._base_search(context)} | stats count by aiops_client_ip | sort {self.max_items} - count", "waf.source_concentration.v1"
        else:
            spl, template = f"{self._base_search(context)} | stats count by aiops_request_uri | sort {self.max_items} - count", "waf.target_distribution.v1"
        return SplunkSearchRequest(template, spl, trigger - half, trigger + half, self.max_results)

    def _make_evidence(self, investigation: str, request: SplunkSearchRequest, response: SplunkSearchResponse, context: AlertLogContext) -> dict:
        rows = response.rows
        if investigation == "temporal_pattern":
            summary = {"total_events": sum(_number(x.get("count")) for x in rows), "peak_count": max((_number(x.get("count")) for x in rows), default=0), "buckets": [{"time": _clip(x.get("_time", ""), self.max_text_chars), "count": _number(x.get("count"))} for x in rows[:self.max_items]]}
        elif investigation == "source_concentration":
            items = [{"ip": _clip(x.get("aiops_client_ip", ""), self.max_text_chars), "count": _number(x.get("count"))} for x in rows[:self.max_items]]
            total = sum(_number(x.get("count")) for x in rows)
            summary = {"unique_source_ips": len(rows), "top_source_ratio": round(items[0]["count"] / total, 4) if items and total else 0, "top_sources": items}
        elif investigation == "target_distribution":
            summary = {"unique_uris": len(rows), "top_targets": [{"uri": _clip(x.get("aiops_request_uri", ""), self.max_text_chars), "count": _number(x.get("count"))} for x in rows[:self.max_items]]}
        else:
            values = [_number(x.get("count")) for x in rows]
            average = round(sum(values) / len(values), 2) if values else 0
            summary = {"sample_buckets": len(values), "baseline_average": average, "current_count": context.current_count, "increase_ratio": round(context.current_count / average, 4) if average else 0, "is_anomalous": bool(average and context.current_count / average >= 3)}
        item = {"investigation": investigation, "template_version": request.template_id, "summary": summary,
                "row_count": len(rows), "returned_item_count": min(len(rows), self.max_items), "truncated": len(rows) > self.max_items,
                "source": {"system": "splunk", "search_id": _clip(response.search_id, 128), "query_hash": "sha256:" + hashlib.sha256(request.spl.encode()).hexdigest(), "duration_ms": max(0, int(response.duration_ms))}}
        return self._fit_item_budget(item)

    def _fit_item_budget(self, item: dict) -> dict:
        while len(json.dumps(item, ensure_ascii=False)) > self.item_budget_chars:
            lists = [v for v in item.get("summary", {}).values() if isinstance(v, list) and v]
            if not lists:
                break
            lists[0].pop()
            item["truncated"] = True
        return item

    def _fit_total_budget(self, result: dict) -> dict:
        while len(json.dumps(result, ensure_ascii=False)) > self.total_budget_chars and result["evidence"]:
            result["evidence"].pop()
            result["truncated"] = True
        return result


def _validate_read_only_spl(spl: str) -> None:
    segments = [value.strip() for value in spl.split("|") if value.strip()]
    if not segments or not segments[0].lower().startswith("search "):
        raise ValueError("unsafe_query_blocked")
    for part in segments[1:]:
        command = part.split(maxsplit=1)[0].lower()
        if command in FORBIDDEN_COMMANDS or command not in ALLOWED_COMMANDS:
            raise ValueError("unsafe_query_blocked")


def _context_from_alert_data(alert_id: str, data: dict) -> AlertLogContext:
    first = (data.get("results") or [{}])[0]
    return AlertLogContext(alert_id, "waf", _parse_datetime(data.get("trigger_time_utc") or data.get("trigger_time")), str(first.get("properties_hostname", "")).strip(), str(first.get("id", "")).strip(), str(first.get("properties_action", "")).strip(), _number(first.get("count", data.get("event_count", 0))))


def _parse_datetime(value) -> datetime:
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        parsed = datetime.strptime(raw, "%Y/%m/%d %H:%M:%S")
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _spl_literal(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _number(value) -> int:
    try:
        return max(0, int(float(str(value))))
    except (TypeError, ValueError):
        return 0


def _clip(value, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _error(alert_id: str, code: str) -> dict:
    return {"success": False, "alert_id": str(alert_id or ""), "evidence_type": "splunk_log", "evidence": [], "warnings": [], "error_code": code, "truncated": False}
