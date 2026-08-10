"""
告警相关 API 路由
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services.alert_service import (
    get_alert_list,
    get_alert_detail,
    process_single_alert,
)
from app.services.splunk_alert_service import SplunkSyncError, sync_remote_alerts
from app.services.alert_authorization_service import AlertAuthorizationStore

logger = logging.getLogger("aiops.api.alerts")
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _filter_for_user(request: Request, alerts):
    """Apply server-side application filtering; auth-disabled remains dev-compatible."""
    settings = get_settings()
    if not settings.AIOPS_AUTH_ENABLED:
        return alerts
    username = getattr(request.state, "authenticated_user", None)
    if not username:
        raise HTTPException(status_code=401, detail="未认证用户")
    store = AlertAuthorizationStore(settings.authorization_db_path)
    try:
        return [alert for alert in alerts if store.can_access_alert(username, alert)]
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("")
async def list_alerts(request: Request, risk: str = "all", search: str = ""):
    """获取已处理告警列表"""
    alerts = get_alert_list(risk_filter=risk, search=search)
    alerts = _filter_for_user(request, alerts)
    return {"alerts": [a.model_dump() for a in alerts], "total": len(alerts)}


@router.post("/sync")
async def sync_alerts_from_splunk():
    """立即从配置的 Splunk 服务器同步告警到页面缓存。"""
    try:
        return await sync_remote_alerts()
    except SplunkSyncError as exc:
        logger.warning("[ALERTS] Splunk sync failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{alert_id}")
async def alert_detail(request: Request, alert_id: str):
    """获取单个告警详情"""
    detail = get_alert_detail(alert_id)
    if not detail:
        raise HTTPException(status_code=404, detail="告警未找到")
    if get_settings().AIOPS_AUTH_ENABLED:
        username = getattr(request.state, "authenticated_user", None)
        store = AlertAuthorizationStore(get_settings().authorization_db_path)
        try:
            if not username or not detail.alert or not store.can_access_alert(username, detail.alert):
                raise HTTPException(status_code=404, detail="告警未找到")
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return detail.model_dump()


@router.post("/process")
async def process_alert_json(data: dict):
    """手动提交 JSON 告警数据并处理"""
    settings = get_settings()
    try:
        # 写入临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
            dir=str(settings.alert_input_path)
        ) as f:
            json.dump(data, f)
            tmp_path = Path(f.name)

        result = await process_single_alert(tmp_path)
        if result:
            return {"status": "ok", "risk_level": result.risk_level}
        else:
            raise HTTPException(status_code=500, detail="处理失败")
    except Exception as e:
        logger.error(f"[ALERTS] Manual process failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_alert(file: UploadFile = File(...)):
    """上传告警 JSON 文件并处理"""
    settings = get_settings()
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))

        # 保存到输入目录
        dest = settings.alert_input_path / file.filename
        dest.write_bytes(content)

        result = await process_single_alert(dest)
        if result:
            return {
                "status": "ok",
                "filename": file.filename,
                "risk_level": result.risk_level,
            }
        else:
            raise HTTPException(status_code=500, detail="处理失败")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析错误: {e}")
    except Exception as e:
        logger.error(f"[ALERTS] Upload process failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
