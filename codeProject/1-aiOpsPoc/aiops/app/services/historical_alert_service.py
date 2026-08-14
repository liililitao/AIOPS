"""将本地权威文件组装为可检索的历史告警案例。"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("aiops.historical_alert")


class HistoricalCaseIncompleteError(ValueError):
    """历史案例缺少原始告警、增强告警、报告或建议时抛出。"""


@dataclass(frozen=True)
class HistoricalAlertCase:
    case_id: str
    alert_name: str
    trigger_time: str
    hostname: str
    resource_id: str
    risk_level: str
    alert_summary: str
    analysis_summary: str
    suggestion_summary: str
    case_summary: str
    content_hash: str
    raw_alert_path: Path
    enriched_alert_path: Path
    report_path: Path
    suggestion_path: Path

    def to_index_record(self) -> dict:
        return {
            "case_id": self.case_id,
            "case_summary": self.case_summary,
            "alert_name": self.alert_name,
            "trigger_time": self.trigger_time,
            "hostname": self.hostname,
            "resource_id": self.resource_id,
            "risk_level": self.risk_level,
            "alert_summary": self.alert_summary,
            "analysis_summary": self.analysis_summary,
            "suggestion_summary": self.suggestion_summary,
            "raw_alert_path": str(self.raw_alert_path),
            "alert_path": str(self.enriched_alert_path),
            "report_path": str(self.report_path),
            "suggestion_path": str(self.suggestion_path),
            "content_hash": self.content_hash,
        }


class HistoricalCaseRepository:
    """历史告警库的权威来源：本地 JSON 和 Markdown 文件。"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    def load_case(self, date: str, stem: str) -> HistoricalAlertCase:
        paths = {
            "raw_alert": self.project_root / "data" / "alerts" / f"{stem}.json",
            "enriched_alert": self.project_root / "output" / "enriched_alerts" / date / f"{stem}.json",
            "report": self.project_root / "output" / "reports" / date / f"{stem}_analysis.md",
            "suggestion": self.project_root / "output" / "suggestions" / date / f"{stem}_suggestion.md",
        }
        missing = [name for name, path in paths.items() if not path.is_file()]
        if missing:
            raise HistoricalCaseIncompleteError(
                f"historical case {date}/{stem} missing: {', '.join(missing)}"
            )

        raw = json.loads(paths["raw_alert"].read_text(encoding="utf-8"))
        enriched = json.loads(paths["enriched_alert"].read_text(encoding="utf-8"))
        report = paths["report"].read_text(encoding="utf-8")
        suggestion = paths["suggestion"].read_text(encoding="utf-8")
        first = (enriched.get("results") or raw.get("results") or [{}])[0]
        hostname = str(first.get("properties_hostname", ""))
        resource_id = str(first.get("id", ""))
        risk = str(enriched.get("risk_level", "未知"))
        alert_summary = _compact(
            f"{enriched.get('alert_name', raw.get('alert_name', ''))}；资源 {resource_id}；"
            f"域名 {hostname}；请求 {first.get('properties_requestUri', '')}；"
            f"动作 {first.get('properties_action', '')}；次数 {first.get('count', '')}；风险 {risk}",
            500,
        )
        analysis_summary = _markdown_summary(report)
        suggestion_summary = _markdown_summary(suggestion)
        digest = hashlib.sha256()
        for path in paths.values():
            digest.update(path.read_bytes())
        return HistoricalAlertCase(
            case_id=f"{date}/{stem}",
            alert_name=str(enriched.get("alert_name", raw.get("alert_name", ""))),
            trigger_time=str(enriched.get("trigger_time", raw.get("trigger_time", ""))),
            hostname=hostname,
            resource_id=resource_id,
            risk_level=risk,
            alert_summary=alert_summary,
            analysis_summary=analysis_summary,
            suggestion_summary=suggestion_summary,
            case_summary=(
                f"原始告警：{alert_summary}\n"
                f"分析结论：{analysis_summary}\n"
                f"处理建议：{suggestion_summary}"
            ),
            content_hash=digest.hexdigest(),
            raw_alert_path=paths["raw_alert"],
            enriched_alert_path=paths["enriched_alert"],
            report_path=paths["report"],
            suggestion_path=paths["suggestion"],
        )

    def discover_complete_cases(self) -> list[HistoricalAlertCase]:
        base = self.project_root / "output" / "enriched_alerts"
        cases = []
        for path in sorted(base.glob("*/*.json")) if base.exists() else []:
            try:
                cases.append(self.load_case(path.parent.name, path.stem))
            except (HistoricalCaseIncompleteError, OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("Skip historical case %s: %s", path, exc)
        return cases


def archive_raw_alert(source: Path, target_dir: Path) -> Path:
    """将输入告警复制到历史告警库的原始告警归档；内容冲突不静默覆盖。"""
    source = Path(source)
    target = Path(target_dir) / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != source.read_bytes():
            raise FileExistsError(f"raw alert archive conflict: {target}")
        return target
    shutil.copy2(source, target)
    return target


def best_effort_index_case(
    date: str, stem: str, repository, index, failure_path: Path | None = None
) -> dict:
    """索引失败不能影响本地告警结果、报告或建议的写入。"""
    try:
        return {"success": True, "status": index.upsert(repository.load_case(date, stem))}
    except Exception as exc:
        if failure_path:
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"failures": {}}
            if failure_path.exists():
                try:
                    payload = json.loads(failure_path.read_text(encoding="utf-8"))
                except (OSError, ValueError, json.JSONDecodeError):
                    pass
            payload.setdefault("failures", {})[f"{date}/{stem}"] = {"message": str(exc)}
            failure_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.warning("Historical index skipped for %s/%s: %s", date, stem, exc)
        return {"success": False, "error_code": "history_index_failed", "message": str(exc)}


def _markdown_summary(text: str, limit: int = 600) -> str:
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    return _compact(re.sub(r"[`*_>|\[\]]", "", text), limit)


def _compact(text: str, limit: int) -> str:
    value = " ".join(text.split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"
