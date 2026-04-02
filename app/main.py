"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.profiles import router as profiles_router
from app.api.jobs import router as jobs_router
from app.scheduler import start_scheduler, shutdown_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Path to built React frontend (populated by Docker build or `npm run build`)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Prospector starting up")
    scheduler = start_scheduler()
    yield
    shutdown_scheduler(scheduler)
    logger.info("Prospector shutting down")


app = FastAPI(
    title="Prospector",
    description="AI-powered job search pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(profiles_router)
app.include_router(jobs_router)




@app.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok"}


# Serve React frontend in production (when built)
if FRONTEND_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the React SPA for all non-API routes."""
        # Try to serve the exact file first (e.g. favicon.ico)
        file_path = FRONTEND_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(FRONTEND_DIR / "index.html")
