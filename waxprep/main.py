from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import os
import sentry_sdk
from waxprep.app.core.config import settings
from waxprep.app.core.logging import setup_logging
from waxprep.app.api.routes import webhooks
from waxprep.app.api.routes import admin
from waxprep.app.api.routes import web_app
from waxprep.app.api.routes import school_api
from waxprep.app.database.client import get_db_client
from waxprep.app.jobs.scheduler import setup_scheduler, shutdown_scheduler

setup_logging()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=0.05,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting WaxPrep {settings.app_version} in {settings.app_env} mode")
    
    try:
        db = get_db_client()
        result = db.table("students").select("id").limit(1).execute()
        logger.info(f"Database connection verified. Students table accessible.")
    except Exception as e:
        logger.error(f"Database connection failed on startup: {e}")
    
    try:
        from waxprep.app.cache.redis_client import get_redis
        import asyncio
        redis = await get_redis()
        if redis:
            logger.info("Redis cache connected successfully")
        else:
            logger.warning("Redis unavailable — running without cache")
    except Exception as e:
        logger.warning(f"Redis startup check failed: {e}")
    
    try:
        setup_scheduler()
        logger.info("Background scheduler started with all jobs")
    except Exception as e:
        logger.error(f"Scheduler startup failed: {e}")
    
    logger.info("WaxPrep is ready — the tutor that actually knows you")
    yield
    shutdown_scheduler()
    logger.info("WaxPrep shut down cleanly")

app = FastAPI(
    title="WaxPrep",
    description="The tutor that actually knows you — AI teacher for Nigerian students",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )

app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(web_app.router, prefix="/api/v1")
app.include_router(school_api.router, prefix="/api/v1")

static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Static files mounted from {static_dir}")

@app.get("/health")
@app.head("/health")
async def health_check():
    db_ok = False
    try:
        db = get_db_client()
        db.table("students").select("id").limit(1).execute()
        db_ok = True
    except Exception:
        pass
    
    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "WaxPrep",
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": "connected" if db_ok else "error",
        "motto": "The tutor that actually knows you",
    }

@app.get("/")
@app.head("/")
async def root():
    return {
        "service": "WaxPrep",
        "motto": "The tutor that actually knows you",
        "version": settings.app_version,
        "web_app": "/static/web/index.html",
        "health": "/health",
    }

@app.get("/static/web")
async def serve_web_app():
    from fastapi.responses import FileResponse
    web_path = os.path.join(static_dir, "web", "index.html")
    if os.path.exists(web_path):
        return FileResponse(web_path)
    return {"error": "Web app not found"}
