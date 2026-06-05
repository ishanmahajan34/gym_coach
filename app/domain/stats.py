"""Stats: streaks, weekly counts, goal progress."""
from __future__ import annotations
from datetime import date, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Workout, DailyHabit
from app.domain.habits import get_week_habits, walk_minutes

CARDIO_LOW_TARGET = 150
CARDIO_HIGH_TARGET = 75
STRENGTH_TARGET = 3
HABIT_DAYS_TARGET = 7


async def workouts_this_week(session: AsyncSession, user_id: int) -> int:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    result = await session.execute(
        select(func.count(func.distinct(Workout.date)))
        .where(
            Workout.user_id == user_id,
            Workout.date >= monday,
            Workout.type != "rest",
            Workout.status == "done",
        )
    )
    return result.scalar_one() or 0


async def current_streak(session: AsyncSession, user_id: int) -> int:
    """Days since last skipped/missed planned workout. Rest days don't break it."""
    result = await session.execute(
        select(Workout.date, Workout.status)
        .where(Workout.user_id == user_id, Workout.type != "rest")
        .order_by(desc(Workout.date))
        .limit(60)
    )
    rows = result.all()
    streak = 0
    for d, status in rows:
        if status == "done":
            streak += 1
        elif status == "skipped":
            break
        # planned/in_progress: skip without breaking
    return streak


async def total_workouts(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(Workout.id))
        .where(Workout.user_id == user_id, Workout.status == "done")
    )
    return result.scalar_one() or 0


async def weekly_goals(
    session: AsyncSession, user_id: int, week_start: date
) -> dict:
    """
    Returns progress toward weekly goals with _min, _target, and _pct keys.
    """
    week_end = week_start + timedelta(days=6)

    result = await session.execute(
        select(Workout).where(
            Workout.user_id == user_id,
            Workout.date >= week_start,
            Workout.date <= week_end,
            Workout.status == "done",
        )
    )
    workouts = list(result.scalars().all())

    cardio_low = sum(w.cardio_minutes_low or 0 for w in workouts)
    cardio_high = sum(w.cardio_minutes_high or 0 for w in workouts)
    strength_days = sum(1 for w in workouts if w.type in ("push", "pull", "squat"))

    habits = await get_week_habits(session, user_id, week_start)
    cardio_low += sum(walk_minutes(h) for h in habits)
    habit_days = sum(1 for h in habits if h.stretch_done or h.balance_done)

    def pct(val, target):
        return min(100, round(val / target * 100)) if target else 0

    return {
        "cardio_low_min": cardio_low,
        "cardio_low_target": CARDIO_LOW_TARGET,
        "cardio_low_pct": pct(cardio_low, CARDIO_LOW_TARGET),
        "cardio_high_min": cardio_high,
        "cardio_high_target": CARDIO_HIGH_TARGET,
        "cardio_high_pct": pct(cardio_high, CARDIO_HIGH_TARGET),
        "strength_days": strength_days,
        "strength_target": STRENGTH_TARGET,
        "strength_pct": pct(strength_days, STRENGTH_TARGET),
        "habit_days": habit_days,
        "habit_days_target": HABIT_DAYS_TARGET,
        "habit_days_pct": pct(habit_days, HABIT_DAYS_TARGET),
    }
