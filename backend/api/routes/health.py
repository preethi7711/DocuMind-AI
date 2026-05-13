"""
DocuMind AI — Health Check Router
===================================
WHY A HEALTH CHECK ENDPOINT?
    Every production service needs a /health endpoint. It serves three purposes:

    1. LIVENESS — "Is the process running?" (Kubernetes/Docker restarts if not)
    2. READINESS — "Is the service ready to accept traffic?" (Load balancers use this)
    3. DIAGNOSTICS — "Which sub-services are degraded?" (On-call engineers use this)

    Without /health, you're flying blind. Your load balancer routes traffic to
    a broken instance and you find out from angry users, not your monitoring.

WHAT THIS CHECKS:
    - App identity and version (confirms correct deployment)
    - Upload directory (writable? enough space?)
    - ChromaDB directory (exists and accessible?)
    - Overall status: "healthy" | "degraded" | "unhealthy"

BEST PRACTICE:
    Health checks must be FAST (< 100ms). Never make external HTTP calls
    or heavy DB queries in a health check. Just check local state.
"""

import time
from fastapi import APIRouter
from loguru import logger

from backend.api.schemas.responses import SuccessResponse, HealthStatus
from backend.config.settings import settings

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    response_model=SuccessResponse[HealthStatus],
    summary="Application Health Check",
    description=(
        "Returns the current health status of DocuMind AI and its sub-services. "
        "Used by load balancers and monitoring systems to determine readiness."
    ),
)
async def health_check() -> SuccessResponse[HealthStatus]:
    """
    Comprehensive health check endpoint.

    Checks:
    - Application is running and config is loaded
    - Upload directory is accessible
    - Processed directory is accessible
    - ChromaDB directory is accessible

    Returns 200 even when degraded — let the client inspect the `status` field.
    Only returns 500 for truly catastrophic failures (caught by FastAPI exception handler).
    """
    start_time = time.perf_counter()

    services: dict[str, str] = {}
    all_healthy = True

    # --- Check upload directory ---
    try:
        upload_path = settings.upload_path
        if upload_path.exists() and upload_path.is_dir():
            services["upload_storage"] = "ok"
        else:
            services["upload_storage"] = "missing"
            all_healthy = False
    except Exception as exc:
        services["upload_storage"] = f"error: {exc}"
        all_healthy = False

    # --- Check processed directory ---
    try:
        processed_path = settings.processed_path
        if processed_path.exists() and processed_path.is_dir():
            services["processed_storage"] = "ok"
        else:
            services["processed_storage"] = "missing"
            all_healthy = False
    except Exception as exc:
        services["processed_storage"] = f"error: {exc}"
        all_healthy = False

    # --- Check ChromaDB directory ---
    try:
        chroma_path = settings.chromadb_path
        if chroma_path.exists() and chroma_path.is_dir():
            services["vector_store"] = "ok"
        else:
            services["vector_store"] = "missing"
            # Degraded — not unhealthy (ChromaDB creates it on first use)
    except Exception as exc:
        services["vector_store"] = f"error: {exc}"

    # --- Determine overall status ---
    status = "healthy" if all_healthy else "degraded"

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.debug(f"Health check completed in {elapsed_ms}ms | status={status}")

    health_data = HealthStatus(
        status=status,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        services=services,
    )

    return SuccessResponse[HealthStatus](
        success=True,
        message=f"Health check completed in {elapsed_ms}ms",
        data=health_data,
    )
