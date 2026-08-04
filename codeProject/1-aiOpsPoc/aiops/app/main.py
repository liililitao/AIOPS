"""
AIOps Alert Agent - FastAPI 应用入口
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings

# Configure logging - use ASCII-safe format for Windows console
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("aiops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle"""
    logger.info(f"[START] {settings.APP_NAME} v{settings.APP_VERSION} starting...")

    # Validate config
    warnings = settings.validate_runtime()
    for w in warnings:
        logger.warning(f"[WARN] {w}")

    # Ensure output directories exist
    settings.reports_path.mkdir(parents=True, exist_ok=True)
    settings.suggestions_path.mkdir(parents=True, exist_ok=True)
    settings.alert_input_path.mkdir(parents=True, exist_ok=True)
    settings.alert_output_path.mkdir(parents=True, exist_ok=True)

    # Ensure data directory exists
    data_dir = settings.project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Ensure processed_alerts.json exists
    index_path = settings.processed_index_path
    if not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        index_path.write_text(
            json.dumps({"processed_files": {}, "last_scan_time": None}, indent=2),
            encoding="utf-8",
        )

    # Start scheduler
    if settings.SCAN_ENABLED:
        try:
            from app.core.scheduler import start_scheduler
            start_scheduler()
            logger.info(f"[SCHEDULER] Started, interval={settings.SCAN_INTERVAL_MINUTES}min")
        except Exception as e:
            logger.error(f"[SCHEDULER] Start failed: {e}")

    logger.info(f"[READY] {settings.APP_NAME} on port {settings.PORT}")
    yield

    # Shutdown
    if settings.SCAN_ENABLED:
        try:
            from app.core.scheduler import stop_scheduler
            stop_scheduler()
        except Exception:
            pass
    logger.info(f"[STOP] {settings.APP_NAME} shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
from app.api.v1.alerts import router as alerts_router
from app.api.v1.config import router as config_router
from app.api.v1.scheduler import router as scheduler_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.kb_chat import router as kb_chat_router

app.include_router(alerts_router)
app.include_router(config_router)
app.include_router(scheduler_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(kb_chat_router)


@app.get("/api/v1/health")
async def health_check():
    """Health check"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# Static files (frontend)
frontend_dir = settings.project_root / settings.FRONTEND_DIR
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    logger.info(f"[STATIC] Frontend: {frontend_dir}")


def run():
    """Dev server entry"""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    run()
