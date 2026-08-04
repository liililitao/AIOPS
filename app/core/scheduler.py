"""
定时调度器 - 基于 APScheduler 的告警扫描调度
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings

logger = logging.getLogger("aiops.scheduler")

_scheduler: BackgroundScheduler | None = None
_last_scan_time: datetime | None = None
_paused: bool = False


def start_scheduler():
    """启动定时调度器"""
    global _scheduler, _last_scan_time
    settings = get_settings()

    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _scan_job,
        "interval",
        minutes=settings.SCAN_INTERVAL_MINUTES,
        id="scan_alerts",
        name="扫描告警目录",
        next_run_time=datetime.now() + timedelta(seconds=10),  # 启动10秒后首次执行
    )
    _scheduler.start()
    logger.info(f"[SCHEDULER] Started, interval={settings.SCAN_INTERVAL_MINUTES}min")


def stop_scheduler():
    """停止调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("调度器已停止")


def pause_scheduler():
    """暂停调度"""
    global _paused
    _paused = True
    if _scheduler:
        _scheduler.pause_job("scan_alerts")
    logger.info("调度器已暂停")


def resume_scheduler():
    """恢复调度"""
    global _paused
    _paused = False
    if _scheduler:
        _scheduler.resume_job("scan_alerts")
    logger.info("调度器已恢复")


def get_scheduler_status() -> dict:
    """获取调度器状态"""
    settings = get_settings()
    next_run = None
    if _scheduler:
        job = _scheduler.get_job("scan_alerts")
        if job and job.next_run_time:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")

    return {
        "running": not _paused if _scheduler else False,
        "interval_minutes": settings.SCAN_INTERVAL_MINUTES,
        "last_scan": _last_scan_time.strftime("%Y-%m-%d %H:%M:%S") if _last_scan_time else None,
        "next_scan": next_run,
    }


async def trigger_scan() -> dict:
    """手动触发一次扫描（同步等待完成）"""
    try:
        await _scan_job()
        return {"status": "ok", "message": "扫描已完成"}
    except Exception as e:
        logger.error(f"[SCHEDULER] Manual scan failed: {e}")
        return {"status": "error", "message": str(e)}


async def _scan_job():
    """扫描任务：检查告警目录，处理新告警"""
    global _last_scan_time
    _last_scan_time = datetime.now()

    try:
        from app.services.alert_service import process_new_alerts

        settings = get_settings()
        logger.info(f"[SCAN] Scanning alert dir: {settings.alert_input_path}")
        result = await process_new_alerts()
        logger.info(
            f"[SCAN] Complete - new: {result.get('new', 0)}, "
            f"已处理: {result.get('processed', 0)}, "
            f"错误: {result.get('errors', 0)}"
        )
    except Exception as e:
        logger.error(f"[SCHEDULER] Scan job error: {e}", exc_info=True)
