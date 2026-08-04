"""
配置相关 API 路由
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.core.scheduler import get_scheduler_status, pause_scheduler, resume_scheduler
from app.core.risk_assessor import assess_risk

logger = logging.getLogger("aiops.api.config")
router = APIRouter(prefix="/api/v1/config", tags=["config"])


class ConfigUpdate(BaseModel):
    """可更新的配置项"""
    scan_interval_minutes: int | None = None
    risk_count_high: int | None = None
    risk_count_medium: int | None = None


@router.get("")
async def get_config():
    """获取当前配置"""
    s = get_settings()
    return {
        "scan_interval_minutes": s.SCAN_INTERVAL_MINUTES,
        "scan_enabled": s.SCAN_ENABLED,
        "risk_count_high": s.RISK_COUNT_HIGH_THRESHOLD,
        "risk_count_medium": s.RISK_COUNT_MEDIUM_THRESHOLD,
        "cmdb_type": s.CMDB_TYPE,
        "cmdb_xlsx_path": str(s.cmdb_xlsx_path) if s.cmdb_xlsx_path else "",
        "alert_input_dir": str(s.alert_input_path),
        "alert_output_dir": str(s.alert_output_path),
    }


@router.put("")
async def update_config(update: ConfigUpdate):
    """更新配置（运行时生效，重启后恢复为 .env 值）"""
    s = get_settings()

    if update.scan_interval_minutes is not None:
        if update.scan_interval_minutes < 1 or update.scan_interval_minutes > 60:
            raise HTTPException(400, "扫描间隔必须在 1-60 分钟之间")
        # 运行时修改（注意：pydantic-settings 的 frozen 特性，这里修改对象属性）
        from app.core.scheduler import _scheduler
        if _scheduler:
            _scheduler.reschedule_job(
                "scan_alerts",
                trigger="interval",
                minutes=update.scan_interval_minutes,
            )
        s.SCAN_INTERVAL_MINUTES = update.scan_interval_minutes

    if update.risk_count_high is not None:
        s.RISK_COUNT_HIGH_THRESHOLD = update.risk_count_high

    if update.risk_count_medium is not None:
        s.RISK_COUNT_MEDIUM_THRESHOLD = update.risk_count_medium

    return {"status": "ok", "message": "配置已更新"}


@router.get("/scheduler/status")
async def scheduler_status():
    """获取调度器运行状态"""
    return get_scheduler_status()
