"""
DocuMind AI — Structured Logging
==================================
WHY LOGURU OVER STANDARD LOGGING:
    Python's built-in logging module requires 15+ lines of boilerplate
    just for basic setup. Loguru gives us:
    - Color-coded console output by level
    - Automatic log rotation (prevents disk from filling up)
    - Structured context binding (attach document_id to every log)
    - Zero configuration for the common case

WHY NOT PRINT():
    print() has no levels, no timestamps, no file output, no rotation.
    In production, logs go to centralized systems (Datadog, CloudWatch).
    Those systems parse log LEVELS to trigger alerts. print() bypasses all of this.

ENGINEERING STANDARD:
    Every function entry/exit in critical paths should be logged at DEBUG.
    Errors should always include the full exception (with exc_info=True equivalent).
    Never log raw user data or file contents (PII / security concern).
"""

import sys
from pathlib import Path
from loguru import logger

from backend.config.settings import settings


def _add_file_handler(log_path: Path, level: str, retention: str) -> None:
    """
    Add a file handler with a safe fallback when queued logging is unavailable.

    Some Windows sandboxed environments deny the named-pipe primitives used by
    Loguru's `enqueue=True`. In that case we fall back to direct file writes so
    the application still starts and remains observable.
    """
    common_kwargs = dict(
        sink=str(log_path),
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention=retention,
        compression="zip",
        backtrace=True,
        diagnose=False,
    )

    try:
        logger.add(enqueue=True, **common_kwargs)
    except PermissionError:
        logger.add(enqueue=False, **common_kwargs)
        logger.warning(
            "Queued logging unavailable; falling back to synchronous file logging for {}",
            log_path.name,
        )


def setup_logging() -> None:
    """
    Configure Loguru for the DocuMind AI application.

    Call this ONCE at application startup (inside main.py lifespan).
    After this, any module can just do:

        from loguru import logger
        logger.info("This works everywhere automatically")

    LEVELS:
        TRACE   — Extremely detailed (disabled in production)
        DEBUG   — Developer diagnostics (disabled in production)
        INFO    — Normal operations: "Document uploaded", "OCR complete"
        WARNING — Something unexpected but recoverable: "Low confidence OCR"
        ERROR   — Operation failed, needs attention, but app keeps running
        CRITICAL— App cannot continue; immediate human intervention needed
    """

    # Remove the default Loguru handler (plain stderr without format)
    logger.remove()

    # --- Console Handler ---
    # Shows colored, formatted logs during development.
    # In production, you'd typically suppress DEBUG and ship only INFO+.
    log_level = "DEBUG" if settings.is_development else "INFO"

    logger.add(
        sink=sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,          # Show full stack on errors
        diagnose=settings.is_development,  # Show variable values in tracebacks (dev only)
    )

    # --- File Handler: General Application Logs ---
    # Rotates at 10MB, keeps 30 days of history, compresses old logs.
    # This prevents the logs directory from consuming unbounded disk space.
    logs_path = settings.logs_path
    logs_path.mkdir(parents=True, exist_ok=True)

    _add_file_handler(
        logs_path / "documind_{time:YYYY-MM-DD}.log",
        level="INFO",
        retention="30 days",
    )

    # --- File Handler: Error Logs Only ---
    # Separate error log for quick incident investigation.
    # Ops teams watch this file in production for alerts.
    _add_file_handler(
        logs_path / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        retention="90 days",
    )

    logger.info(
        f"Logging initialized | environment={settings.environment} | level={log_level}"
    )


def get_logger(name: str):
    """
    Returns a contextualized logger bound to a specific module name.

    Usage:
        log = get_logger(__name__)
        log.info("Processing started", document_id="abc123")

    WHY BIND?
        When you bind context to a logger, every subsequent log from that
        logger automatically includes that context. This is invaluable for
        tracing a single request's journey through 10 different modules.
    """
    return logger.bind(module=name)
