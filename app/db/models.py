"""ORM models. Single-user for now, but built so multi-user is a config flip later."""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.engine import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    workouts: Mapped[list["Workout"]] = relationship(back_populates="user")
    week_plans: Mapped[list["WeekPlan"]] = relationship(back_populates="user")
    reflections: Mapped[list["Reflection"]] = relationship(back_populates="user")
    daily_habits: Mapped[list["DailyHabit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    type: Mapped[str] = mapped_column(String(32))  # push|pull|squat|conditioning|rest
    planned_minutes: Mapped[int] = mapped_column(Integer, default=50)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="planned")  # planned|in_progress|done|skipped
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    energy_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cardio_minutes_low: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cardio_minutes_high: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="workouts")
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.order_index",
    )


class WorkoutSet(Base):
    """One row per prescribed set. 'target_*' = plan, 'actual_*' = what you did."""
    __tablename__ = "sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), index=True)
    exercise_slug: Mapped[str] = mapped_column(String(64), index=True)
    exercise_name: Mapped[str] = mapped_column(String(128))  # denormalized for display
    muscle_group: Mapped[str] = mapped_column(String(32), index=True)
    order_index: Mapped[int] = mapped_column(Integer)         # ordering in workout
    set_number: Mapped[int] = mapped_column(Integer)          # 1, 2, 3...
    target_reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in lb
    actual_reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in lb
    rpe: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)             # 1-10
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workout: Mapped["Workout"] = relationship(back_populates="sets")


class WeekPlan(Base):
    __tablename__ = "week_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)  # always a Monday
    committed_days: Mapped[list] = mapped_column(JSON, default=list)  # ["mon","tue",...]
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="week_plans")


class Reflection(Base):
    __tablename__ = "reflections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    mood: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    energy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="reflections")


class AuthToken(Base):
    """Magic-link tokens, sent via Telegram."""
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DailyHabit(Base):
    __tablename__ = "daily_habits"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_habit_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    stretch_done: Mapped[bool] = mapped_column(Boolean, default=False)
    stretch_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stretch_logged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    balance_done: Mapped[bool] = mapped_column(Boolean, default=False)
    balance_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    balance_logged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    walk_breakfast_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    walk_lunch_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    walk_dinner_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="daily_habits")
