"""从 Splunk 导出 CMDB CSV，并以原子方式替换本地快照。"""

import csv
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import get_settings

logger = logging.getLogger("aiops.cmdb_sync")


def _state_path() -> Path:
    return get_settings().project_root / "data" / "cmdb_sync_state.json"


def get_cmdb_sync_status() -> dict:
    path = _state_path()
    if not path.exists():
        return {"status": "never", "message": "尚未同步", "rows": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "unknown", "message": "同步状态文件不可读", "rows": 0}


def _write_status(payload: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _csv_path() -> Path:
    settings = get_settings()
    path = Path(settings.CMDB_CSV_PATH)
    if not path.is_absolute():
        path = settings.project_root / path
    return path.resolve()


def _validate_csv(content: bytes) -> int:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    headers = {str(header or "").strip() for header in (reader.fieldnames or [])}
    expected = {
        "Resource Name", "Server Name", "Environment", "SUBSCRIPTION",
        "Subscription Name", "域名和证书", "系统名称 (System Name)",
    }
    if not headers or not headers.intersection(expected):
        raise ValueError(
            "Splunk 导出的 CSV 缺少可识别的 CMDB 字段，至少需要 Resource Name、"
            "Server Name、Environment 或域名和证书之一"
        )
    rows = list(reader)
    if not rows:
        raise ValueError("Splunk 导出的 CMDB CSV 没有数据行")
    return len(rows)


def sync_cmdb_from_splunk() -> dict:
    """同步一次 Splunk CMDB CSV；失败时保留上一份成功快照。"""
    settings = get_settings()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        if not settings.SPLUNK_ENABLED:
            raise RuntimeError("SPLUNK_ENABLED 未开启")
        if settings.CMDB_TYPE != "splunk_csv":
            raise RuntimeError("CMDB_TYPE 必须设置为 splunk_csv")
        if not settings.SPLUNK_BASE_URL or not settings.SPLUNK_TOKEN:
            raise RuntimeError("Splunk 地址或 Token 未配置")
        if not settings.CMDB_SPLUNK_QUERY.strip():
            raise RuntimeError("CMDB_SPLUNK_QUERY 未配置")

        endpoint = settings.SPLUNK_BASE_URL.rstrip("/") + "/services/search/jobs/export"
        response = httpx.post(
            endpoint,
            data={
                "search": settings.CMDB_SPLUNK_QUERY.strip(),
                "output_mode": "csv",
                "earliest_time": "0",
                "latest_time": "now",
            },
            headers={"Authorization": f"Splunk {settings.SPLUNK_TOKEN}"},
            verify=settings.SPLUNK_VERIFY_TLS,
            timeout=max(1, settings.SPLUNK_TIMEOUT_SECONDS),
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Splunk CSV 导出失败（HTTP {response.status_code}）：{response.text[:300]}")

        rows = _validate_csv(response.content)
        destination = _csv_path()
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f"{destination.stem}_", suffix=".tmp", dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as temp_file:
                temp_file.write(response.content)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_name, destination)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

        from app.tools.cmdb_tool import invalidate_cache
        invalidate_cache()
        result = {
            "status": "ok",
            "message": f"已从 Splunk 导入 {rows} 条 CMDB 记录",
            "rows": rows,
            "synced_at": started_at,
            "path": str(destination),
        }
        _write_status(result)
        logger.info("[CMDB] Splunk CSV sync complete: rows=%s", rows)
        return result
    except (httpx.HTTPError, OSError, ValueError, RuntimeError) as exc:
        result = {
            "status": "error",
            "message": str(exc),
            "rows": get_cmdb_sync_status().get("rows", 0),
            "failed_at": started_at,
        }
        _write_status(result)
        logger.error("[CMDB] Splunk CSV sync failed: %s", exc)
        return result
