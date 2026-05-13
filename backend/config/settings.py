"""
DocuMind AI — Centralized Configuration
========================================
WHY THIS EXISTS:
    Every production system has a single source of truth for configuration.
    Instead of reading os.environ manually across 20 files (a maintenance
    nightmare), we define one Settings class. Every module imports from here.

HOW IT WORKS:
    pydantic-settings reads the .env file, validates all values with type
    hints, and provides them as typed Python attributes. If a required field
    is missing, the app fails FAST at startup — not silently in production.

ENGINEERING PRINCIPLE:
    Fail fast, fail loudly. Configuration errors should surface immediately,
    not when a user triggers an obscure code path hours after deployment.
"""

from functools import lru_cache
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from the .env file.

    All fields are typed — pydantic validates them at startup.
    If a required field is missing or the wrong type, the app won't start.
    This is intentional: configuration errors are caught before serving traffic.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,       # APP_NAME and app_name are the same
        extra="ignore",             # Silently ignore unknown env vars
    )

    # --- App Identity ---
    app_name: str = "DocuMind AI"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Directory Paths ---
    # Stored as strings in .env, converted to Path objects here.
    # Always use Path objects in code — never raw strings for file paths.
    upload_dir: str = "uploads"
    processed_dir: str = "processed"
    chromadb_dir: str = "chromadb"
    logs_dir: str = "logs"

    # --- File Upload Limits ---
    max_upload_size_mb: int = 50
    allowed_extensions: str = "pdf"

    # --- OCR Configuration ---
    ocr_language: str = "en"
    ocr_use_gpu: bool = False
    enable_handwriting_ocr: bool = False

    # --- Embeddings ---
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 32

    # --- ChromaDB ---
    chroma_collection_name: str = "documind_docs"

    # --- LLM (Ollama) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_num_gpu: int = 1         # Set to 0 to force CPU, or -1 for auto (if supported)

    # --- RAG Pipeline ---
    rag_top_k: int = 5
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50

    # --- Database ---
    database_url: str = "sqlite:///./documind.db"

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://localhost:5500"

    # -------------------------------------------------------
    # Computed properties (derived from raw settings)
    # -------------------------------------------------------

    @property
    def upload_path(self) -> Path:
        """Absolute Path object for the upload directory."""
        return Path(self.upload_dir).resolve()

    @property
    def processed_path(self) -> Path:
        """Absolute Path object for the processed output directory."""
        return Path(self.processed_dir).resolve()

    @property
    def chromadb_path(self) -> Path:
        """Absolute Path object for the ChromaDB persistence directory."""
        return Path(self.chromadb_dir).resolve()

    @property
    def logs_path(self) -> Path:
        """Absolute Path object for log file storage."""
        return Path(self.logs_dir).resolve()

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB limit to bytes for direct comparison with file sizes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Return allowed extensions as a clean list."""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list for FastAPI middleware."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v.lower() not in allowed:
            raise ValueError(f"environment must be one of: {allowed}")
        return v.lower()

    @field_validator("debug", mode="before")
    @classmethod
    def validate_debug(cls, v):
        """
        Accept common deployment-style strings for DEBUG.

        Some shells or hosting setups expose values like "release" rather than
        strict booleans. We treat known "non-debug" values as False so the app
        can still start predictably.
        """
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached singleton Settings instance.

    WHY lru_cache?
        Reading and parsing the .env file on every request is wasteful.
        lru_cache(maxsize=1) means this function runs ONCE per process,
        caches the result, and returns the same object on every subsequent call.

    USAGE in FastAPI (Dependency Injection):
        from backend.config.settings import get_settings
        from fastapi import Depends

        @router.get("/example")
        def example(settings: Settings = Depends(get_settings)):
            return {"model": settings.ollama_model}
    """
    return Settings()


# Module-level singleton for direct imports (non-DI usage)
# Usage: from backend.config.settings import settings
settings = get_settings()
