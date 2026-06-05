"""Daily habit tracking — stretch, balance, meal walks."""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DailyHabit

STRETCH_DEFAULT_MINUTES = 7
BALANCE_DEFAULT_MINUTES = 3
WALK_MINUTES = 10

MealName = Literal["breakfast", "lunch", "dinner"]


async def get_or_create_today(
    session: AsyncSession, user_id: int, today: date
) -> DailyHabit:
    """Fetch today's DailyHabit row, inserting a blank one if absent."""
    result = await session.execute(
        select(DailyHabit).where(
            DailyHabit.user_id == user_id, DailyHabit.date == today
        )
    )
    habit = result.scalar_one_or_none()
    if habit is None:
        habit = DailyHabit(user_id=user_id, date=today)
        session.add(habit)
        await session.flush()
    return habit


async def log_stretch(
    session: AsyncSession, user_id: int, today: date, minutes: int = STRETCH_DEFAULT_MINUTES
) -> DailyHabit:
    habit = await get_or_create_today(session, user_id, today)
    habit.stretch_done = True
    habit.stretch_minutes = minutes
    habit.stretch_logged_at = datetime.now(timezone.utc)
    await session.flush()
    return habit


async def log_balance(
    session: AsyncSession, user_id: int, today: date, minutes: int = BALANCE_DEFAULT_MINUTES
) -> DailyHabit:
    habit = await get_or_create_today(session, user_id, today)
    habit.balance_done = True
    habit.balance_minutes = minutes
    habit.balance_logged_at = datetime.now(timezone.utc)
    await session.flush()
    return habit


async def log_meal_walk(
    session: AsyncSession, user_id: int, today: date, meal: MealName
) -> DailyHabit:
    """Idempotent — re-logging updates the timestamp."""
    habit = await get_or_create_today(session, user_id, today)
    now = datetime.now(timezone.utc)
    if meal == "breakfast":
        habit.walk_breakfast_at = now
    elif meal == "lunch":
        habit.walk_lunch_at = now
    elif meal == "dinner":
        habit.walk_dinner_at = now
    await session.flush()
    return habit


async def get_week_habits(
    session: AsyncSession, user_id: int, week_start: date
) -> list[DailyHabit]:
    """Return DailyHabit rows for Mon–Sun of the given week (may be sparse)."""
    week_end = week_start + timedelta(days=6)
    result = await session.execute(
        select(DailyHabit).where(
            DailyHabit.user_id == user_id,
            DailyHabit.date >= week_start,
            DailyHabit.date <= week_end,
        )
    )
    return list(result.scalars().all())


def walk_count(habit: DailyHabit) -> int:
    return sum(1 for t in [habit.walk_breakfast_at, habit.walk_lunch_at, habit.walk_dinner_at] if t)


def walk_minutes(habit: DailyHabit) -> int:
    return walk_count(habit) * WALK_MINUTES
