"""
DocuMind AI — Database Session Management
==========================================
WHY ASYNC?
    FastAPI is an async framework. If we used synchronous SQLAlchemy (psycopg2/sqlite3), 
    each database query would block the entire server thread. By using `aiosqlite` 
    and SQLAlchemy's `AsyncSession`, the database doesn't block the event loop.

PATTERN:
    We use the "Dependency Injection" pattern recommended by FastAPI.
    `get_db` provides a fresh session for every request and ensures it's 
    closed/cleaned up even if an error occurs.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config.settings import settings

# 1. Create Async Engine
db_url = settings.database_url
if db_url.startswith("sqlite:///") and "+aiosqlite" not in db_url:
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

print(f"DEBUG: Using Database URL: {db_url}")

engine = create_async_engine(
    db_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False}
)

# 2. Create Session Factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 3. Base class for models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

# 4. Dependency for FastAPI routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.
    Ensures the session is closed after the request is finished.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
