from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


engine: AsyncEngine = create_async_engine(
    url=str(settings.DATABASE_URL),
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with SessionLocal() as session:
        yield session


async def dispose_db() -> None:
    """Dispose the engine and release pooled connections."""
    await engine.dispose()
