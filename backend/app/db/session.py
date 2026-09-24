import logging
from typing import Any, AsyncGenerator, Dict, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

# Singletons for connection pooling
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine() -> AsyncEngine:
    """
    Get or create the singleton SQLAlchemy AsyncEngine for PostgreSQL with connection pooling.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.async_database_url
        logger.info(
            f"Configuring PostgreSQL async engine targeting {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )
        _engine = create_async_engine(
            db_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the singleton async sessionmaker factory.
    """
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_async_engine()
        _async_session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session per request.
    Rolls back automatically on unhandled exception and closes session on completion.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> Dict[str, Any]:
    """
    Probes database connectivity by executing a lightweight ping query.
    Returns status dictionary without throwing exceptions if PostgreSQL is unreachable.
    """
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                return {
                    "status": "connected",
                    "engine": "postgresql+asyncpg",
                    "reachable": True,
                }
            return {
                "status": "degraded",
                "engine": "postgresql+asyncpg",
                "reachable": True,
            }
    except Exception as exc:
        logger.debug(f"Database health probe connection issue: {exc}")
        return {
            "status": "disconnected",
            "engine": "postgresql+asyncpg",
            "reachable": False,
            "message": "PostgreSQL service is currently unreachable or offline",
        }
