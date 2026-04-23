# ============================================================
# models/db_session.py – Async DB Session Factory
# ============================================================

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from loguru import logger

from config import settings
from models.database import Base

# ── Engine ────────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.POSTGRES_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    poolclass=None,  # use default pool
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_async_session():
    """Async context manager for DB sessions with auto-rollback on error."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"DB session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables initialized")


async def drop_db():
    """Drop all tables. DANGER: only for dev."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("⚠️  All database tables dropped")
