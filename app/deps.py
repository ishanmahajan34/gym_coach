"""Shared FastAPI dependencies."""
from __future__ import annotations
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.models import User
from app.domain.workouts import get_or_create_user


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(session: SessionDep) -> User:
    """Single-user mode for milestones 1-3. Magic-link auth comes in milestone 4."""
    return await get_or_create_user(session, telegram_chat_id="default")


CurrentUserDep = Annotated[User, Depends(get_current_user)]
