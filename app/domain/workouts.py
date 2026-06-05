"""
Workout repository: data access for workouts/sets.
The web routes and bot handlers both go through this layer.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Workout, WorkoutSet, User
from app.domain.planner import WorkoutPlan


async def get_or_create_user(session: AsyncSession, telegram_chat_id: str = "default") -> User:
    """For now, single user. telegram_chat_id='default' until bot is configured."""
    result = await session.execute(
        select(User).where(User.telegram_chat_id == telegram_chat_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_chat_id=telegram_chat_id, timezone="UTC")
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def todays_workout(session: AsyncSession, user_id: int) -> Optional[Workout]:
    result = await session.execute(
        select(Workout)
        .where(Workout.user_id == user_id, Workout.date == date.today())
        .options(selectinload(Workout.sets))
    )
    return result.scalar_one_or_none()


async def get_workout(session: AsyncSession, workout_id: int) -> Optional[Workout]:
    result = await session.execute(
        select(Workout)
        .where(Workout.id == workout_id)
        .options(selectinload(Workout.sets))
    )
    return result.scalar_one_or_none()


async def recent_workouts(
    session: AsyncSession, user_id: int, days: int = 14
) -> list[Workout]:
    cutoff = date.today() - timedelta(days=days)
    result = await session.execute(
        select(Workout)
        .where(Workout.user_id == user_id, Workout.date >= cutoff)
        .order_by(desc(Workout.date))
        .options(selectinload(Workout.sets))
    )
    return list(result.scalars().all())


async def history_for_planner(session: AsyncSession, user_id: int, days: int = 21) -> list[dict]:
    """Return history in the format the planner expects."""
    workouts = await recent_workouts(session, user_id, days=days)
    return [
        {
            "date": w.date,
            "type": w.type,
            "rating": w.rating,
            "sets": [
                {
                    "exercise_slug": s.exercise_slug,
                    "muscle_group": s.muscle_group,
                    "actual_reps": s.actual_reps,
                    "actual_weight": s.actual_weight,
                }
                for s in w.sets
            ],
        }
        for w in workouts
    ]


async def create_planned_workout(
    session: AsyncSession, user_id: int, plan: WorkoutPlan, on_date: Optional[date] = None
) -> Workout:
    on_date = on_date or date.today()
    workout = Workout(
        user_id=user_id,
        date=on_date,
        type=plan.type,
        planned_minutes=plan.duration_minutes,
        status="planned",
        notes=plan.summary,
    )
    session.add(workout)
    await session.flush()  # to get workout.id

    for order, ex in enumerate(plan.exercises):
        for set_num in range(1, ex.sets + 1):
            session.add(
                WorkoutSet(
                    workout_id=workout.id,
                    exercise_slug=ex.slug,
                    exercise_name=ex.name,
                    muscle_group=ex.muscle_group,
                    order_index=order,
                    set_number=set_num,
                    target_reps=ex.reps if ex.reps else None,
                    target_weight=ex.target_weight,
                )
            )

    await session.commit()
    await session.refresh(workout, ["sets"])
    return workout


async def start_workout(session: AsyncSession, workout: Workout) -> None:
    workout.status = "in_progress"
    workout.started_at = datetime.utcnow()
    await session.commit()


async def finish_workout(
    session: AsyncSession, workout: Workout, rating: Optional[int] = None, notes: Optional[str] = None
) -> None:
    workout.status = "done"
    workout.finished_at = datetime.utcnow()
    if workout.started_at:
        workout.actual_minutes = int(
            (workout.finished_at - workout.started_at).total_seconds() / 60
        )
    if rating is not None:
        workout.rating = rating
    if notes:
        workout.notes = (workout.notes + " | " + notes) if workout.notes else notes
    await session.commit()


async def log_set(
    session: AsyncSession,
    set_id: int,
    actual_reps: Optional[int],
    actual_weight: Optional[float],
    rpe: Optional[int] = None,
) -> WorkoutSet:
    s = await session.get(WorkoutSet, set_id)
    if s is None:
        raise ValueError(f"Set {set_id} not found")
    s.actual_reps = actual_reps
    s.actual_weight = actual_weight
    if rpe is not None:
        s.rpe = rpe
    await session.commit()
    return s


async def last_performance_for(
    session: AsyncSession, user_id: int, exercise_slug: str
) -> Optional[WorkoutSet]:
    result = await session.execute(
        select(WorkoutSet)
        .join(Workout)
        .where(
            Workout.user_id == user_id,
            WorkoutSet.exercise_slug == exercise_slug,
            WorkoutSet.actual_weight.is_not(None),
        )
        .order_by(desc(Workout.date), desc(WorkoutSet.set_number))
        .limit(1)
    )
    return result.scalar_one_or_none()
