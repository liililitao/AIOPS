"""
定时调度器 - 基于 APScheduler 的告警扫描调度
修复：BackgroundScheduler 同步线程无法直接执行async协程
"""

import logging
import asyncio
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
    # 包装：同步外壳内部使用asyncio.run执行异步扫描函数
    _scheduler.add_job(
        _sync_scan_wrapper,
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
    """手动触发一次扫描（同步等待完成，API调用入口）"""
    try:
        sync_warning = None
        try:
            from app.services.splunk_alert_service import sync_remote_alerts
            await sync_remote_alerts()
        except Exception as exc:
            logger.warning("[SCHEDULER] Splunk sync failed before scan: %s", exc)
            sync_warning = f"Splunk 同步失败：{exc}"
        await _scan_job()
        result = {"status": "ok", "message": "扫描已完成"}
        if sync_warning:
            result["sync_warning"] = sync_warning
        return result
    except Exception as e:
        logger.error(f"[SCHEDULER] Manual scan failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def _sync_scan_wrapper():
    """
    给APScheduler使用的同步包装函数
    在独立线程新建事件循环运行异步扫描任务
    """
    asyncio.run(_scan_job())


async def _scan_job():
    """扫描任务：检查告警目录，处理新告警（保留原有async实现不变）"""
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
