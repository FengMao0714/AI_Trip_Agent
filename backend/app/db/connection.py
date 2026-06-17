"""Async database connection management."""

from collections.abc import AsyncIterator

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def build_database_url(settings: Settings) -> URL:
    """Build the PostgreSQL async database URL from settings.

    Args:
        settings: Runtime application settings.

    Returns:
        SQLAlchemy URL configured for asyncpg.
    """
    return URL.create(
        drivername="postgresql+asyncpg",
        username=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


async def init_db(settings: Settings | None = None) -> None:
    """Initialize the async SQLAlchemy engine and session factory.

    Args:
        settings: Optional runtime settings. Uses dependency settings when omitted.
    """
    global async_session_factory, engine

    if engine is not None and async_session_factory is not None:
        return

    resolved_settings = settings or get_settings()
    engine = create_async_engine(
        build_database_url(resolved_settings),
        pool_pre_ping=True,
    )
    async_session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


async def close_db() -> None:
    """Dispose the async database engine."""
    global async_session_factory, engine

    if engine is not None:
        await engine.dispose()

    engine = None
    async_session_factory = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session for FastAPI dependencies.

    Yields:
        An async SQLAlchemy session.

    Raises:
        RuntimeError: If the database engine has not been initialized.
    """
    if async_session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")

    async with async_session_factory() as session:
        yield session
