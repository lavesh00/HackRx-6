"""
Database connection management.
"""

import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Database setup
settings = get_settings()

# Convert sqlite URL to async version
database_url = settings.DATABASE_URL
if database_url.startswith('sqlite:'):
    database_url = database_url.replace('sqlite:', 'sqlite+aiosqlite:', 1)

# Create async engine
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def init_database():
    """Initialize database tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

@asynccontextmanager
async def get_db_session():
    """Get database session context manager."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def close_database():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")
