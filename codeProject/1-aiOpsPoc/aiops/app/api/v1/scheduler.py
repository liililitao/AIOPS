"""
调度器控制 API 路由
"""

import logging

from fastapi import APIRouter

from app.core.scheduler import trigger_scan, pause_scheduler, resume_scheduler

logger = logging.getLogger("aiops.api.scheduler")
router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


@router.post("/scan")
async def scan_now():
    """手动触发一次立即扫描"""
    result = await trigger_scan()
    return result


@router.post("/pause")
async def pause():
    """暂停定时扫描"""
    pause_scheduler()
    return {"status": "ok", "message": "调度器已暂停"}


@router.post("/resume")
async def resume():
    """恢复定时扫描"""
    resume_scheduler()
    return {"status": "ok", "message": "调度器已恢复"}
