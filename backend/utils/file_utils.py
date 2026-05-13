"""
DocuMind AI — Directory Bootstrap Utility
==========================================
WHY THIS EXISTS:
    When the app starts for the first time (fresh clone, new environment),
    none of the runtime directories (uploads/, processed/, logs/, chromadb/)
    exist. Rather than having each module defensively create its own directory,
    we centralize directory setup here and run it ONCE at startup.

ENGINEERING PRINCIPLE:
    "Make the pit of success easy to fall into."
    The app should work on a fresh checkout without any manual setup steps.
"""

from pathlib import Path
from loguru import logger

from backend.config.settings import settings


def ensure_directories() -> None:
    """
    Create all required runtime directories if they don't already exist.

    Called once during application lifespan startup. Idempotent — safe to
    call multiple times (mkdir with exist_ok=True never raises on re-runs).
    """
    directories = [
        settings.upload_path,
        settings.processed_path,
        settings.chromadb_path,
        settings.logs_path,
        # Subdirectories for organized file storage
        settings.upload_path / "raw",
        settings.processed_path / "images",
        settings.processed_path / "ocr",
        settings.processed_path / "structured",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ready: {directory}")

    logger.info(f"All runtime directories initialized ({len(directories)} paths)")
