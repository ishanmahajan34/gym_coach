"""Async SQLAlchemy engine + session factory."""
from __future__ import annotations
import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


if settings.DB_URL.startswith("sqlite"):
    db_path = settings.DB_URL.split("///")[-1]
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

engine = create_async_engine(settings.async_db_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables. We use create_all for now; switch to Alembic when schema stabilizes."""
    # Import models so they register with Base.metadata
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
