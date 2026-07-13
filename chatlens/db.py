"""Async SQLAlchemy engine/session configuration."""

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from chatlens import config

engine: AsyncEngine = create_async_engine(config.DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def init_db():
    from chatlens.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
