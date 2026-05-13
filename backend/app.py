"""
DocuMind AI — FastAPI Application Factory
==========================================
WHY AN APPLICATION FACTORY PATTERN?
    Instead of defining the FastAPI app at module level and importing it
    everywhere, we use a factory function `create_app()`. This gives us:

    1. TESTABILITY — Tests can call create_app() with different configs
    2. MULTIPLE INSTANCES — Run dev + test server in same process if needed
    3. CLEAN SEPARATION — App setup is explicit, not magic module-level code

WHY LIFESPAN (not @app.on_event)?
    FastAPI deprecated @app.on_event("startup") in favor of the lifespan
    context manager. The lifespan pattern is safer because:
    - Startup AND shutdown are co-located (easier to reason about)
    - Resources created in startup are guaranteed to be cleaned up
    - It's standard Python async context manager pattern

REQUEST LIFECYCLE:
    HTTP Request
        → CORS Middleware (checks origin header)
        → Request Logging Middleware (logs method + path)
        → Router (matches URL to handler function)
        → Handler Function (business logic)
        → Response (wrapped in standard envelope)
        → Back through middleware stack
    HTTP Response
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from backend.config.settings import settings
from backend.utils.logger import setup_logging
from backend.utils.file_utils import ensure_directories
from backend.api.routes import health, documents, ocr, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Everything BEFORE `yield` runs at startup.
    Everything AFTER `yield` runs at shutdown.

    Startup order matters:
        1. Logging first — so all subsequent steps are logged
        2. Directories — so file operations won't fail
        3. Future: Database connection pool
        4. Future: ChromaDB client initialization
        5. Future: Embedding model preload
    """
    # ── STARTUP ──────────────────────────────────────────────
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment} | Debug: {settings.debug}")

    # Initialize Database Tables
    from backend.database.session import engine, Base
    from backend.database import models # Ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized.")

    ensure_directories()
    logger.info("Application startup complete. Ready to serve requests.")

    yield  # Application runs here

    # ── SHUTDOWN ─────────────────────────────────────────────
    logger.info(f"Shutting down {settings.app_name}...")
    # Future: close DB connections, flush caches, etc.
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """
    FastAPI application factory.

    Creates and configures the FastAPI application with:
    - Metadata (for auto-generated OpenAPI docs at /docs)
    - Lifespan manager (startup/shutdown)
    - CORS middleware
    - Exception handlers
    - All API routers
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "DocuMind AI — Intelligent Document Understanding Platform. "
            "Upload PDFs, extract structured content via OCR, and query "
            "documents conversationally using RAG + local LLMs."
        ),
        docs_url="/docs" if not settings.is_production else None,   # Hide docs in prod
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── MIDDLEWARE ────────────────────────────────────────────
    _register_middleware(app)

    # ── EXCEPTION HANDLERS ───────────────────────────────────
    _register_exception_handlers(app)

    # ── ROUTERS ──────────────────────────────────────────────
    _register_routers(app)

    return app


def _register_middleware(app: FastAPI) -> None:
    """
    Register all middleware.

    MIDDLEWARE ORDER MATTERS — they execute in reverse registration order.
    The last registered middleware is the outermost (runs first on request).

    WHY CORS MIDDLEWARE?
        Browsers block frontend JavaScript from calling a different domain/port
        without explicit CORS headers. Since our frontend (port 5500) calls our
        backend (port 8000), CORS is required for the browser to allow it.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],        # GET, POST, PUT, DELETE, PATCH
        allow_headers=["*"],        # Content-Type, Authorization, etc.
    )


def _register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers.

    WHY GLOBAL HANDLERS?
        Without this, unhandled exceptions return FastAPI's default 500 response
        which leaks internal error details. Our handler catches all unhandled
        exceptions, logs them properly, and returns our standard error envelope.
    """

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "details": None,
            },
        )


def _register_routers(app: FastAPI) -> None:
    """
    Mount all API routers under the /api/v1 prefix.

    WHY VERSIONED URLS (/api/v1/...)?
        Versioning lets you ship breaking API changes as /api/v2/... while
        existing clients on /api/v1/... keep working. This is non-negotiable
        in any API that external clients consume.

    ROUTER STRUCTURE:
        /api/v1/health      → Health checks
        /api/v1/documents   → Document CRUD (Phase 2)
        /api/v1/ocr         → OCR processing (Phase 4)
        /api/v1/chat        → RAG chat interface (Phase 7)
    """
    api_prefix = "/api/v1"

    app.include_router(health.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(ocr.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    
    @app.get("/")
    async def root():
        """Root endpoint providing basic API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "operational",
            "docs_url": "/docs",
            "api_v1_prefix": api_prefix
        }

    logger.debug(f"Registered routers under prefix: {api_prefix}")


# Module-level app instance — used by uvicorn
# uvicorn main:app --reload
application = create_app()
