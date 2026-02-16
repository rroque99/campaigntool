import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from campaign.config import settings
from campaign.routers import auth, campaigns, emails, recipients
from campaign.scheduler import start_reply_monitor, start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    try:
        start_reply_monitor()
    except Exception:
        logger.warning("Could not start reply monitor (Gmail may not be authenticated yet).")
    yield
    # Shutdown
    stop_scheduler()


app = FastAPI(
    title="Gmail Campaign Tool",
    version="0.1.0",
    description="Local web app for managing and sending email campaigns via Gmail API",
    lifespan=lifespan,
)

# In production, frontend is served from the same origin — no CORS needed.
if not settings.is_production:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(campaigns.router, prefix=settings.api_prefix)
app.include_router(recipients.router, prefix=settings.api_prefix)
app.include_router(emails.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health")
async def health_check():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler to prevent raw stack traces from reaching the client."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
    )


# ---------------------------------------------------------------------------
# Production static file serving
# ---------------------------------------------------------------------------

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    # Serve static assets (JS, CSS, images) under /assets
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="static-assets",
    )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback: serve index.html for all non-API, non-asset paths."""
        # Try to serve an exact file first (e.g. favicon.ico, vite.svg)
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
