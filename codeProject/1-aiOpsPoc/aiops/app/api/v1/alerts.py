"""
告警相关 API 路由
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from app.config import get_settings
from app.services.alert_service import (
    get_alert_list,
    get_alert_detail,
    process_remote_alert,
    process_single_alert,
)
from app.services.splunk_alert_service import (
    SplunkSyncError,
    get_cached_remote_alert_detail,
    sync_remote_alerts,
)
from app.services.alert_authorization_service import AlertAuthorizationStore
from app.services.application_alert_simulator import (
    analyze_application_alert,
    delete_application_alert,
    generate_application_alert,
    list_application_alert_rules,
)

logger = logging.getLogger("aiops.api.alerts")
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _filter_for_user(request: Request, alerts):
    """按已认证用户过滤告警；开发环境未启用认证时保持兼容。"""
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
    """立即从 Splunk 同步告警到本地缓存。"""
    try:
        return await sync_remote_alerts()
    except SplunkSyncError as exc:
        logger.warning("[ALERTS] Splunk sync failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/simulation/application-rules")
async def application_alert_rules():
    """返回可生成模拟日志的应用告警规则。"""
    try:
        return {"rules": list_application_alert_rules()}
    except Exception as exc:
        logger.exception("[SIMULATION] Failed to load application rules: %s", exc)
        raise HTTPException(status_code=500, detail="加载应用告警规则失败") from exc


@router.post("/simulation/application-alert")
async def create_application_alert_simulation(data: dict):
    """生成模拟日志后自动完成 AI 风险判定、报告和处理建议。"""
    try:
        rule_id = int(data.get("rule_id"))
        count = int(data.get("count", 10))
        result = generate_application_alert(rule_id, count)
        analyzed = await analyze_application_alert(result["alert_id"])
        if not analyzed:
            raise RuntimeError("模拟应用告警创建后无法进入 AI 分析流程")
        return {
            "status": "ok",
            "message": f"已生成 {count} 条模拟应用日志，并完成 AI 风险判定、分析报告和处理建议",
            "risk_level": analyzed["risk_level"],
            **result,
        }
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[SIMULATION] Failed to generate application alert: %s", exc)
        raise HTTPException(status_code=500, detail="生成模拟应用告警失败") from exc


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


@router.post("/{alert_id}/analyze")
async def analyze_alert(request: Request, alert_id: str):
    """调用 AI 为模拟应用告警或已同步 Splunk 告警生成分析。"""
    if alert_id.startswith("appsim_"):
        try:
            result = await analyze_application_alert(alert_id)
            if not result:
                raise HTTPException(status_code=404, detail="模拟应用告警未找到")
            return {
                "status": "ok", "message": "AI 风险判定、分析报告和处理建议已生成", "alert_id": alert_id,
                "risk_level": result["risk_level"],
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("[SIMULATION] AI risk analysis failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="AI 风险判定失败，请检查模型配置后重试") from exc

    remote_alert = get_cached_remote_alert_detail(alert_id)
    if not remote_alert:
        raise HTTPException(status_code=404, detail="仅支持对当前已同步的 Splunk 告警生成分析")

    settings = get_settings()
    if settings.AIOPS_AUTH_ENABLED:
        username = getattr(request.state, "authenticated_user", None)
        store = AlertAuthorizationStore(settings.authorization_db_path)
        try:
            if not username or not store.can_access_alert(username, remote_alert):
                raise HTTPException(status_code=404, detail="告警未找到")
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        result = await process_remote_alert(alert_id)
        if not result:
            raise HTTPException(status_code=500, detail="告警处理失败")
        return {
            "status": "ok",
            "message": "AI 分析报告和处理建议已生成",
            "alert_id": alert_id,
            "risk_level": result.risk_level,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[ALERTS] Splunk alert analysis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="AI 分析生成失败，请稍后重试") from exc


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """删除一条模拟应用告警及其独立 AI 输出。"""
    if not delete_application_alert(alert_id):
        raise HTTPException(status_code=404, detail="模拟应用告警未找到或不支持删除")
    return {"status": "ok", "message": "告警及其 AI 输出已删除"}


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
