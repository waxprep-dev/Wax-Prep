from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger
import os
from waxprep.app.core.config import settings
from waxprep.app.core.logging import setup_logging
from waxprep.app.database.client import get_db_client

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting WaxPrep {settings.app_version} in {settings.app_env} mode")
    try:
        db = get_db_client()
        db.table("students").select("id").limit(1).execute()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    logger.info("WaxPrep is ready to teach")
    yield
    logger.info("WaxPrep shut down cleanly")

app = FastAPI(
    title="WaxPrep",
    description="The AI teacher built for Nigerian students",
    version=settings.app_version,
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error"})

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "WaxPrep", "version": settings.app_version}

@app.head("/health")
async def health_head():
    return {}

@app.get("/")
async def root():
    return {"service": "WaxPrep", "version": settings.app_version, "status": "running"}
