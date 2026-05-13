"""
DocuMind AI — Standardized API Response Schemas
================================================
WHY STANDARDIZED RESPONSES?
    Without a consistent response envelope, your API becomes unpredictable.
    Clients (frontend, mobile, third-party) have to handle each endpoint
    differently. This creates fragile integrations.

    With a standard envelope:
        {"success": true, "data": {...}, "message": "OK"}
        {"success": false, "error": "NOT_FOUND", "message": "Document not found"}

    Clients can write ONE error-handling function for your entire API.

ENGINEERING STANDARD:
    This pattern is used at Google, Stripe, GitHub. It's called the
    "API Response Envelope" pattern. Never return raw data without context.
"""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard success response envelope.

    Every successful API response wraps its data in this structure.
    The Generic[T] allows type-safe responses:
        SuccessResponse[DocumentSchema]  — tells clients exactly what's in .data
    """
    success: bool = True
    message: str = "OK"
    data: T | None = None


class ErrorResponse(BaseModel):
    """
    Standard error response envelope.

    Every error response uses this structure. The `error` field contains
    a machine-readable error code (for programmatic handling).
    The `message` field contains a human-readable explanation.

    Example:
        {"success": false, "error": "VALIDATION_ERROR", "message": "File too large"}
    """
    success: bool = False
    error: str                   # Machine-readable code: "NOT_FOUND", "INVALID_FILE"
    message: str                 # Human-readable explanation
    details: dict[str, Any] | None = None  # Optional extra context for debugging


class HealthStatus(BaseModel):
    """Schema for the health check endpoint response."""
    status: str               # "healthy" | "degraded" | "unhealthy"
    app_name: str
    version: str
    environment: str
    services: dict[str, str]  # e.g. {"database": "ok", "chromadb": "ok"}
