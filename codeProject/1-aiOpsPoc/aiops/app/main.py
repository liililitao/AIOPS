"""
AIOps Alert Agent - FastAPI 应用入口
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.session_auth import (
    HandoffVerificationError,
    SQLiteNonceStore,
    create_session_token,
    read_session_token,
    verify_handoff,
)

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
HANDOFF_NONCE_STORE = SQLiteNonceStore(settings.handoff_nonce_db_path)
SESSION_COOKIE_NAME = "aiops_session"


def _auth_failure(message: str, code: str, status_code: int = 401) -> Response:
    return JSONResponse(
        {"success": False, "message": message, "code": code},
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


async def authenticate_request(request: Request, call_next):
    """Turn the signed Splunk handoff URL into a server-trusted user session."""
    if not settings.AIOPS_AUTH_ENABLED or request.url.path == "/api/v1/health":
        request.state.authenticated_user = None
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)

    signed_keys = {"v", "user", "exp", "nonce", "sig"}
    if request.url.path in {"", "/"} and signed_keys.intersection(request.query_params):
        missing = [key for key in signed_keys if not request.query_params.get(key)]
        if missing:
            return _auth_failure("安全跳转链接参数不完整", "missing")
        if len(settings.AIOPS_HANDOFF_SECRET.encode("utf-8")) < 32:
            return _auth_failure("AIOps 跳转密钥未配置", "configuration", 503)
        if len(settings.AIOPS_SESSION_SECRET.encode("utf-8")) < 32:
            return _auth_failure("AioPs 会话密钥未配置", "configuration", 503)
        try:
            identity = verify_handoff(
                secret=settings.AIOPS_HANDOFF_SECRET,
                version=request.query_params.get("v", ""),
                user=request.query_params.get("user", ""),
                exp=request.query_params.get("exp", ""),
                nonce=request.query_params.get("nonce", ""),
                signature=request.query_params.get("sig", ""),
                roles=request.query_params.get("roles", ""),
                max_ttl_seconds=settings.AIOPS_HANDOFF_MAX_TTL_SECONDS,
                clock_skew_seconds=settings.AIOPS_HANDOFF_CLOCK_SKEW_SECONDS,
                nonce_store=HANDOFF_NONCE_STORE,
            )
            session_token = create_session_token(
                settings.AIOPS_SESSION_SECRET,
                identity,
                settings.AIOPS_SESSION_HOURS,
            )
        except HandoffVerificationError as exc:
            return _auth_failure("安全跳转链接校验失败", exc.code)
        except ValueError:
            return _auth_failure("Aiops 会话密钥未配置", "configuration", 503)

        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            SESSION_COOKIE_NAME,
            session_token,
            httponly=True,
            secure=settings.AIOPS_COOKIE_SECURE,
            samesite="lax",
            max_age=max(1, settings.AIOPS_SESSION_HOURS) * 3600,
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    try:
        identity = read_session_token(
            settings.AIOPS_SESSION_SECRET,
            request.cookies.get(SESSION_COOKIE_NAME),
        )
    except ValueError:
        identity = None
    if identity is None:
        if request.url.path.startswith("/api/"):
            return _auth_failure("请从 Splunk Dashboard 重新进入 AIOps", "unauthorized")
        return _auth_failure("请从 Splunk Dashboard 重新进入 AIOps", "unauthorized")
    request.state.authenticated_user = identity.username
    request.state.authenticated_roles = identity.roles
    return await call_next(request)


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

app.middleware("http")(authenticate_request)

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
