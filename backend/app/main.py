import sys
from pathlib import Path

# Ensure project root is in sys.path so 'backend.app...' absolute imports always resolve regardless of cwd
_backend_dir = Path(__file__).resolve().parent.parent
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_backend_dir) not in sys.path:
    sys.path.insert(1, str(_backend_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from backend.app.core.config import settings
from backend.app.api.endpoints import router as api_router
from backend.app.data.scenarios import reset_all_scenarios

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinelgraph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize scenarios on startup
    logger.info("Initializing SentinelGraph synthetic scenario fixtures...")
    reset_all_scenarios()
    logger.info(
        f"SentinelGraph startup complete. Gemini configured: {settings.has_gemini_key}. "
        f"Model: {settings.gemini_model}"
    )
    yield
    logger.info("Shutting down SentinelGraph backend.")


app = FastAPI(
    title="SentinelGraph API",
    description="Agentic AI-powered cross-system workflow failure investigation and root-cause analysis platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
allowed_origins = [
    settings.frontend_origin,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safe exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred while processing the investigation."}
    )

# Include Router
app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "SentinelGraph API",
        "tagline": "A change happened here. Something broke there. SentinelGraph investigates why.",
        "status": "operational",
        "docs_url": "/docs"
    }
