# Gym Coach v2 — Implementation Plan

Scope: Add daily habit tracking (stretch, balance, meal walks), cardio goal tracking
(low-intensity 150 min/week, high-intensity 75 min/week), rename legs_light→squat,
redesign home dashboard, and add weekly goals view.

Single user. No auth changes. No Alembic — raw SQL migrations.

---

## High-Level Design

### New activity model

The app now tracks two kinds of activity:

| Kind | Table | Frequency |
|------|-------|-----------|
| Strength / conditioning sessions | `workouts` (existing) | Per-session |
| Daily habits (stretch, balance, meal walks) | `daily_habits` (new) | Per day |

Weekly goals are aggregated from both tables on every page load.

### Weekly goals

| Goal | Target | Source |
|------|--------|--------|
| Low-intensity cardio | 150 min/week | meal walks (×10 min each) + `workouts.cardio_minutes_low` |
| High-intensity cardio | 75 min/week | `workouts.cardio_minutes_high` |
| Strength sessions | 3 days/week | `workouts` where type in (push, pull, squat) and status=done |
| Daily habits | 7 days/week | `daily_habits` where stretch_done OR balance_done |

### Navigation

Keep 3 bottom-nav tabs: **Today** | **Week** | **History**
(Session is accessed via the Start/Continue button on Today — no extra tab needed.)

### Page map

| Route | Template | Purpose |
|-------|----------|---------|
| GET / | home.html | Dashboard: today's session + habits + mini goals |
| GET /workout/{id} | workout/log.html | Set-by-set logging (existing) |
| GET /week | week.html | Calendar + full goals + commit |
| GET /history | history.html | Day-grouped all-activity history |
| POST /habit/stretch | partial | HTMX: log stretch |
| POST /habit/balance | partial | HTMX: log balance |
| POST /habit/walk/{meal} | partial | HTMX: log meal walk |

---

## Phase 1 — Database Layer

### 1a. New table: `daily_habits`

Add to `app/db/models.py`:

```python
from sqlalchemy import Boolean, UniqueConstraint

class DailyHabit(Base):
    __tablename__ = "daily_habits"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_habit_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    # Stretch (5-10 min, default 7)
    stretch_done: Mapped[bool] = mapped_column(Boolean, default=False)
    stretch_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stretch_logged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Balance (2-5 min, default 3)
    balance_done: Mapped[bool] = mapped_column(Boolean, default=False)
    balance_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    balance_logged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Meal walks (10 min each, logged by timestamp)
    walk_breakfast_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    walk_lunch_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    walk_dinner_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="daily_habits")
```

Add to `User` class:
```python
daily_habits: Mapped[list["DailyHabit"]] = relationship(
    back_populates="user", cascade="all, delete-orphan"
)
```

### 1b. Additions to `Workout` model

Add two columns to the `Workout` class (after `notes`, before `started_at`):
```python
cardio_minutes_low: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
cardio_minutes_high: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

Also update the inline comment on `type`:
```python
type: Mapped[str] = mapped_column(String(32))  # push|pull|squat|conditioning|rest
```

### 1c. Migration script

Create `scripts/migrate_v2.py`. Run once against the existing SQLite database.

```python
"""Run: python -m scripts.migrate_v2"""
import asyncio
from sqlalchemy import text
from app.db.engine import engine

STATEMENTS = [
    # Workout additions
    "ALTER TABLE workouts ADD COLUMN cardio_minutes_low INTEGER",
    "ALTER TABLE workouts ADD COLUMN cardio_minutes_high INTEGER",

    # New daily_habits table
    """
    CREATE TABLE IF NOT EXISTS daily_habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        date DATE NOT NULL,
        stretch_done BOOLEAN NOT NULL DEFAULT 0,
        stretch_minutes INTEGER,
        stretch_logged_at DATETIME,
        balance_done BOOLEAN NOT NULL DEFAULT 0,
        balance_minutes INTEGER,
        balance_logged_at DATETIME,
        walk_breakfast_at DATETIME,
        walk_lunch_at DATETIME,
        walk_dinner_at DATETIME,
        CONSTRAINT uq_habit_user_date UNIQUE (user_id, date)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_daily_habits_user_id ON daily_habits(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_daily_habits_date ON daily_habits(date)",
]

async def main():
    async with engine.begin() as conn:
        for stmt in STATEMENTS:
            try:
                await conn.execute(text(stmt))
                print(f"OK: {stmt.strip()[:60]}")
            except Exception as e:
                print(f"SKIP (likely exists): {e}")

asyncio.run(main())
```

---

## Phase 2 — Domain Layer

### 2a. New file: `app/domain/habits.py`

```python
"""Daily habit tracking — stretch, balance, meal walks."""
from __future__ import annotations
from datetime import date, datetime, timezone
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
    from datetime import timedelta
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
    """How many meal walks logged today."""
    return sum(1 for t in [habit.walk_breakfast_at, habit.walk_lunch_at, habit.walk_dinner_at] if t)


def walk_minutes(habit: DailyHabit) -> int:
    return walk_count(habit) * WALK_MINUTES
```

### 2b. Update `app/domain/stats.py`

Add `weekly_goals()` function:

```python
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Workout, DailyHabit
from app.domain.habits import get_week_habits, walk_minutes

CARDIO_LOW_TARGET = 150   # min/week
CARDIO_HIGH_TARGET = 75   # min/week
STRENGTH_TARGET = 3       # sessions/week
HABIT_DAYS_TARGET = 7     # days/week

async def weekly_goals(
    session: AsyncSession, user_id: int, week_start: date
) -> dict:
    """
    Returns dict with keys:
      cardio_low_min, cardio_high_min, strength_days, habit_days
      + _target suffixed versions
      + _pct suffixed versions (0-100, capped at 100)
    """
    week_end = week_start + timedelta(days=6)

    # Workouts this week
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

    # Habits this week
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
```

### 2c. Update `app/domain/planner.py` — rename legs_light → squat

Make the following changes. Every change is a string replacement unless noted.

**Line 10 (comment):** Update inline doc to say `squat` not `legs_light`.

**Line 27:** Change `DEFAULT_TYPE_ROTATION`:
```python
DEFAULT_TYPE_ROTATION = ["push", "pull", "conditioning", "squat", "push", "pull"]
```

**Lines 107-109:** In `_decide_workout_type`, update legs reference:
```python
last_legs = next((w for w in history if w.get("type") == "squat"), None)
days_since_legs = (date.today() - last_legs["date"]).days if last_legs else 99
if days_since_legs >= 8:
    return "squat"
```

**Lines 124-126:** Update candidate check:
```python
if days_since_legs >= 5 and "squat" not in types_done:
    candidates.append("squat")
```

**Lines 188-217:** Rename `_build_legs_light` → `_build_squat` and update content:
```python
def _build_squat(history: list[dict], rng: random.Random) -> WorkoutPlan:
    """Squat-focused lower body. One compound, one accessory, core, then incline walk."""
    avoid = _recent_slugs(history, days=14)
    leg_options = ["leg_press", "goblet_squat", "leg_extension"]
    rng.shuffle(leg_options)
    primary = CATALOG[leg_options[0]]
    secondary_pool = ["leg_curl", "calf_raise", "db_lunges"]
    rng.shuffle(secondary_pool)
    secondary = CATALOG[secondary_pool[0]]
    core = _pick_one(
        [CATALOG[s] for s in ["plank", "hanging_knee_raise", "cable_crunch", "ab_wheel"]],
        avoid, rng
    )

    exercises = [
        PlannedExercise(primary.slug, primary.name, "legs", 3, 10,
                        notes="Moderate weight — controlled, full range of motion."),
        PlannedExercise(secondary.slug, secondary.name, "legs", 2, 12),
        PlannedExercise(core.slug, core.name, "core", 3, 12),
    ]

    return WorkoutPlan(
        type="squat",
        duration_minutes=45,
        title="Squat + Cardio",
        summary="Lower body compound, one accessory, core, then 20 min incline walk.",
        warmup=["5 min easy bike", "Bodyweight squats, hip circles, leg swings"],
        exercises=exercises,
        cardio="20 min incline walk — extends the leg work gently and adds calorie burn",
    )
```

**Lines 350-380:** Rename `_LEGS_CARDIO` → `_SQUAT_CARDIO` (same content, just rename the variable).

**Lines 436-444:** Update `get_cardio_protocol` dict:
```python
pools: dict[str, list[CardioProtocol]] = {
    "push": _PUSH_PULL_CARDIO,
    "pull": _PUSH_PULL_CARDIO,
    "squat": _SQUAT_CARDIO,
    "conditioning": _CONDITIONING_CARDIO,
}
```

**Lines 449-454:** Update `BUILDERS` dict:
```python
BUILDERS = {
    "push": _build_push,
    "pull": _build_pull,
    "squat": _build_squat,
    "conditioning": _build_conditioning,
}
```

Also add cardio intensity classification (used by finish form pre-fill):
```python
# Suggested cardio minutes by type, for pre-filling the finish form.
CARDIO_SUGGESTION: dict[str, dict] = {
    "push":         {"low": 0,  "high": 15},
    "pull":         {"low": 15, "high": 0},
    "squat":        {"low": 20, "high": 0},
    "conditioning": {"low": 0,  "high": 30},
    "rest":         {"low": 0,  "high": 0},
}
```

---

## Phase 3 — Routes Layer

### 3a. New file: `app/web/routes/habits.py`

```python
"""HTMX endpoints for daily habit quick-logging."""
from datetime import date, datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id, templates
from app.domain import habits as habit_domain

router = APIRouter()


def _render_habit_chip(request, name: str, done: bool, label: str,
                        logged_time: str | None) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/habit_chip.html",
        {"request": request, "name": name, "done": done,
         "label": label, "logged_time": logged_time},
    )


def _render_walk_chip(request, meal: str, done: bool,
                      logged_time: str | None) -> HTMLResponse:
    meal_labels = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner"}
    return templates.TemplateResponse(
        "partials/walk_chip.html",
        {"request": request, "meal": meal, "done": done,
         "meal_label": meal_labels[meal], "logged_time": logged_time},
    )


@router.post("/habit/stretch", response_class=HTMLResponse)
async def log_stretch(
    minutes: int = Form(default=7),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_user_id),
):
    from starlette.requests import Request
    habit = await habit_domain.log_stretch(session, user_id, date.today(), minutes)
    await session.commit()
    logged_time = habit.stretch_logged_at.strftime("%-I:%M %p") if habit.stretch_logged_at else None
    # NOTE: request is injected via dependency; see how existing routes handle it
    # Return updated chip partial


@router.post("/habit/balance", response_class=HTMLResponse)
async def log_balance(
    minutes: int = Form(default=3),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_user_id),
):
    habit = await habit_domain.log_balance(session, user_id, date.today(), minutes)
    await session.commit()
    # Return updated chip partial


@router.post("/habit/walk/{meal}", response_class=HTMLResponse)
async def log_walk(
    meal: Literal["breakfast", "lunch", "dinner"],
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_user_id),
):
    habit = await habit_domain.log_meal_walk(session, user_id, date.today(), meal)
    await session.commit()
    # Return updated walk chip partial
```

Note: Look at existing routes (e.g., `workout.py`) for the exact pattern used to get `request`
and call `templates.TemplateResponse`. Follow the same pattern here.

### 3b. Update `app/web/routes/home.py`

After existing stats fetching, add:
```python
from app.domain import habits as habit_domain
from app.domain.stats import weekly_goals
from datetime import date

today = date.today()
week_start = today - timedelta(days=today.weekday())

today_habit = await habit_domain.get_or_create_today(session, user_id, today)
await session.commit()  # persist the new blank row if just created

goals = await weekly_goals(session, user_id, week_start)
```

Pass `today_habit` and `goals` to the template context.

### 3c. Update `app/web/routes/workout.py`

In `POST /workout/{workout_id}/finish`, add two new form fields:
```python
cardio_minutes_low: Optional[int] = Form(default=None),
cardio_minutes_high: Optional[int] = Form(default=None),
```

Before marking the workout done, save these values:
```python
workout.cardio_minutes_low = cardio_minutes_low
workout.cardio_minutes_high = cardio_minutes_high
```

In `GET /workout/{workout_id}` (which renders the finish form), add suggested cardio pre-fill to context:
```python
from app.domain.planner import CARDIO_SUGGESTION
suggestion = CARDIO_SUGGESTION.get(workout.type, {"low": 0, "high": 0})
# Pass as: suggested_cardio_low, suggested_cardio_high
```

Pass `suggested_cardio_low` and `suggested_cardio_high` to `finish_form.html`.

### 3d. Create `app/web/routes/week.py` (replaces `plan.py`)

```python
"""Week view: calendar strip + goal progress + commit."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.deps import get_session, get_user_id, templates
from app.db.models import Workout, WeekPlan
from app.domain.stats import weekly_goals

router = APIRouter()

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TYPE_LABELS = {
    "push": "Push", "pull": "Pull", "squat": "Squat",
    "conditioning": "Cardio", "rest": "Rest",
}


@router.get("/week")
async def week_view(
    request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_user_id),
):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Workouts this week
    result = await session.execute(
        select(Workout).where(
            Workout.user_id == user_id,
            Workout.date >= week_start,
            Workout.date <= week_end,
        )
    )
    week_workouts = {w.date: w for w in result.scalars().all()}

    # Week plan (committed days)
    result2 = await session.execute(
        select(WeekPlan).where(
            WeekPlan.user_id == user_id,
            WeekPlan.week_start == week_start,
        )
    )
    week_plan = result2.scalar_one_or_none()
    committed = set(week_plan.committed_days) if week_plan else set()

    # Build 7-day calendar
    calendar_days = []
    for i, (key, label) in enumerate(zip(WEEKDAYS, WEEKDAY_LABELS)):
        day_date = week_start + timedelta(days=i)
        workout = week_workouts.get(day_date)
        calendar_days.append({
            "key": key,
            "label": label,
            "date": day_date.day,
            "is_today": day_date == today,
            "is_past": day_date < today,
            "workout": workout,
            "workout_type_label": TYPE_LABELS.get(workout.type, "") if workout else "",
            "committed": key in committed,
        })

    goals = await weekly_goals(session, user_id, week_start)

    return templates.TemplateResponse(
        "week.html",
        {
            "request": request,
            "calendar_days": calendar_days,
            "goals": goals,
            "committed_days": list(committed),
            "week_label": f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d')}",
            "active": "week",
        },
    )


@router.post("/plan/commit")
async def commit_week(
    days: list[str] = Form(default=[]),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_user_id),
):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    result = await session.execute(
        select(WeekPlan).where(
            WeekPlan.user_id == user_id, WeekPlan.week_start == week_start
        )
    )
    plan = result.scalar_one_or_none()
    if plan:
        plan.committed_days = days
    else:
        session.add(WeekPlan(user_id=user_id, week_start=week_start, committed_days=days))
    await session.commit()
    return RedirectResponse("/week", status_code=303)
```

### 3e. Update `app/web/routes/history.py`

Fetch both workouts and habits for 30 days, merge by date:

```python
from datetime import date, timedelta
from sqlalchemy import select
from app.db.models import Workout, DailyHabit
from app.domain.habits import walk_count

async def history_view(request, session, user_id):
    today = date.today()
    cutoff = today - timedelta(days=29)

    # Workouts
    result = await session.execute(
        select(Workout).where(
            Workout.user_id == user_id,
            Workout.date >= cutoff,
        ).order_by(Workout.date.desc())
    )
    workouts_by_date: dict[date, list] = {}
    for w in result.scalars().all():
        workouts_by_date.setdefault(w.date, []).append(w)

    # Habits
    result2 = await session.execute(
        select(DailyHabit).where(
            DailyHabit.user_id == user_id,
            DailyHabit.date >= cutoff,
        )
    )
    habits_by_date = {h.date: h for h in result2.scalars().all()}

    # Merge into day entries, most recent first
    all_dates = sorted(
        set(workouts_by_date.keys()) | set(habits_by_date.keys()),
        reverse=True,
    )
    days = []
    for d in all_dates:
        habit = habits_by_date.get(d)
        days.append({
            "date": d,
            "date_label": d.strftime("%a %b %-d"),
            "workouts": workouts_by_date.get(d, []),
            "habit": habit,
            "walk_count": walk_count(habit) if habit else 0,
        })

    return templates.TemplateResponse(
        "history.html",
        {"request": request, "days": days, "active": "history"},
    )
```

### 3f. Update `app/main.py`

Add import and router registration for habits and week:
```python
from app.web.routes import habits, week

app.include_router(habits.router)
app.include_router(week.router)
```

Remove or keep the old plan router — `week.router` now handles both GET /week and POST /plan/commit.

---

## Phase 4 — Template Layer

### 4a. Update `app/web/templates/base.html`

Change the bottom nav from 3 items to 3 items with new labels/paths. Replace the existing
`<nav>` block:

```html
<nav class="bottom-nav">
  <a href="/" class="nav-item {% if active == 'today' %}is-active{% endif %}">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"
         fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
         stroke-linejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
      <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>
    <span>Today</span>
  </a>
  <a href="/week" class="nav-item {% if active == 'week' %}is-active{% endif %}">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"
         fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
         stroke-linejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
      <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>
      <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
    <span>Week</span>
  </a>
  <a href="/history" class="nav-item {% if active == 'history' %}is-active{% endif %}">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"
         fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
         stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
    <span>History</span>
  </a>
</nav>
```

### 4b. Redesign `app/web/templates/home.html`

Full replacement. Structure:

```
{% extends "base.html" %}
{% block content %}

<!-- Header -->
<header class="page-header">
  <div>
    <p class="eyebrow">{{ today_str }}</p>
    <h1 class="heading">Good [morning/afternoon/evening]</h1>
  </div>
  <div class="streak-badge">
    <span class="stat-num">{{ stats.current_streak }}</span>
    <span class="stat-label">streak</span>
  </div>
</header>

<!-- TODAY'S SESSION card -->
{% if workout %}
  <section class="section-block">
    <p class="eyebrow section-eyebrow">Today's session</p>
    <div class="card workout-card">
      <div class="workout-card-header">
        <span class="pill pill-{{ workout.type }}">{{ workout_type_label }}</span>
        <span class="workout-duration">{{ workout.planned_minutes }} min</span>
      </div>
      <h2 class="heading workout-title">{{ plan_title }}</h2>
      <p class="workout-summary">{{ plan_summary }}</p>
      {% if workout.status == 'planned' %}
        <form method="post" action="/workout/{{ workout.id }}/start">
          <button class="btn btn-primary btn-block">Start session</button>
        </form>
      {% elif workout.status == 'in_progress' %}
        <a href="/workout/{{ workout.id }}" class="btn btn-primary btn-block">Continue →</a>
      {% else %}
        <a href="/workout/{{ workout.id }}" class="btn btn-ghost btn-block">Review ✓</a>
      {% endif %}
    </div>
  </section>
{% else %}
  <section class="section-block">
    <p class="eyebrow section-eyebrow">Today's session</p>
    <div class="card no-session-card">
      <p class="muted-text">No session planned yet.</p>
      <form method="post" action="/workout/today/plan">
        <button class="btn btn-primary btn-block">Plan today's workout</button>
      </form>
    </div>
  </section>
{% endif %}

<!-- DAILY HABITS -->
<section class="section-block">
  <p class="eyebrow section-eyebrow">Daily habits</p>
  <div class="habit-row">
    {% include "partials/habit_chip.html" with name="stretch", label="Stretch",
       done=today_habit.stretch_done, logged_time=... %}
    {% include "partials/habit_chip.html" with name="balance", label="Balance",
       done=today_habit.balance_done, logged_time=... %}
  </div>
</section>

<!-- MEAL WALKS -->
<section class="section-block">
  <p class="eyebrow section-eyebrow">Meal walks · 10 min each</p>
  <div class="walk-row">
    {% include "partials/walk_chip.html" with meal="breakfast", meal_label="Breakfast",
       done=(today_habit.walk_breakfast_at is not none), logged_time=... %}
    {% include "partials/walk_chip.html" with meal="lunch", meal_label="Lunch",
       done=(today_habit.walk_lunch_at is not none), logged_time=... %}
    {% include "partials/walk_chip.html" with meal="dinner", meal_label="Dinner",
       done=(today_habit.walk_dinner_at is not none), logged_time=... %}
  </div>
</section>

<!-- THIS WEEK (mini goals) -->
<section class="section-block">
  <p class="eyebrow section-eyebrow">This week</p>
  <div class="card">
    {% include "partials/weekly_goals.html" %}
  </div>
</section>

<!-- Inspiration (keep existing) -->
{% if thought %}
<blockquote class="thought reveal">{{ thought }}</blockquote>
{% endif %}

{% endblock %}
```

Note: Jinja2 `{% include %}` doesn't support `with` clauses directly — pass variables via
the context or use a macro. Use a macro in a `macros.html` file or pass the full context.
See implementation note below.

**Implementation note for partials:** Rather than `{% include with %}`, define the habit and
walk chip contents inline in home.html using Jinja2 macros, OR use `{% set %}` before each
include to set the variables. The partials are also returned by HTMX routes so they need to
work standalone. Recommended approach: use Jinja2 macros defined in `partials/macros.html`,
import them in both `home.html` and the HTMX route templates.

### 4c. New: `app/web/templates/partials/habit_chip.html`

Standalone template (also returned by HTMX routes):

```html
<div class="habit-chip {% if done %}is-done{% endif %}" id="habit-{{ name }}">
  {% if done %}
    <svg class="chip-check-icon"><!-- checkmark --></svg>
    <span class="chip-label">{{ label }}</span>
    {% if logged_time %}
      <span class="chip-time">{{ logged_time }}</span>
    {% endif %}
  {% else %}
    <form hx-post="/habit/{{ name }}"
          hx-target="#habit-{{ name }}"
          hx-swap="outerHTML">
      <input type="hidden" name="minutes" value="{{ default_minutes }}">
      <button type="submit" class="chip-btn">
        <span class="chip-label">{{ label }}</span>
        <span class="chip-hint">tap to log</span>
      </button>
    </form>
  {% endif %}
</div>
```

Variables needed: `name`, `label`, `done`, `logged_time`, `default_minutes`

For stretch: `default_minutes=7`
For balance: `default_minutes=3`

### 4d. New: `app/web/templates/partials/walk_chip.html`

```html
<div class="walk-chip {% if done %}is-done{% endif %}" id="walk-{{ meal }}">
  <span class="walk-meal-label">{{ meal_label }}</span>
  {% if done %}
    <svg class="chip-check-icon"><!-- checkmark --></svg>
    {% if logged_time %}<span class="chip-time">{{ logged_time }}</span>{% endif %}
  {% else %}
    <form hx-post="/habit/walk/{{ meal }}"
          hx-target="#walk-{{ meal }}"
          hx-swap="outerHTML">
      <button type="submit" class="chip-btn-walk">Log walk</button>
    </form>
  {% endif %}
</div>
```

Variables needed: `meal`, `meal_label`, `done`, `logged_time`

### 4e. New: `app/web/templates/partials/weekly_goals.html`

```html
<div class="goals-list">
  <div class="goal-row">
    <span class="goal-label">Low cardio</span>
    <div class="goal-bar-track">
      <div class="goal-bar-fill {% if goals.cardio_low_pct >= 100 %}is-done{% endif %}"
           style="width: {{ goals.cardio_low_pct }}%"></div>
    </div>
    <span class="goal-value">{{ goals.cardio_low_min }}<span class="goal-target">/{{ goals.cardio_low_target }}</span> min</span>
  </div>
  <div class="goal-row">
    <span class="goal-label">High cardio</span>
    <div class="goal-bar-track">
      <div class="goal-bar-fill {% if goals.cardio_high_pct >= 100 %}is-done{% endif %}"
           style="width: {{ goals.cardio_high_pct }}%"></div>
    </div>
    <span class="goal-value">{{ goals.cardio_high_min }}<span class="goal-target">/{{ goals.cardio_high_target }}</span> min</span>
  </div>
  <div class="goal-row">
    <span class="goal-label">Strength</span>
    <div class="goal-bar-track">
      <div class="goal-bar-fill {% if goals.strength_pct >= 100 %}is-done{% endif %}"
           style="width: {{ goals.strength_pct }}%"></div>
    </div>
    <span class="goal-value">{{ goals.strength_days }}<span class="goal-target">/{{ goals.strength_target }}</span> days</span>
  </div>
  <div class="goal-row">
    <span class="goal-label">Daily habits</span>
    <div class="goal-bar-track">
      <div class="goal-bar-fill {% if goals.habit_days_pct >= 100 %}is-done{% endif %}"
           style="width: {{ goals.habit_days_pct }}%"></div>
    </div>
    <span class="goal-value">{{ goals.habit_days }}<span class="goal-target">/{{ goals.habit_days_target }}</span> days</span>
  </div>
</div>
```

### 4f. New: `app/web/templates/week.html`

```html
{% extends "base.html" %}
{% block content %}

<header class="page-header">
  <h1 class="heading">This Week</h1>
  <p class="eyebrow">{{ week_label }}</p>
</header>

<!-- CALENDAR STRIP -->
<section class="section-block">
  <div class="cal-strip">
    {% for day in calendar_days %}
    <div class="cal-day {% if day.is_today %}is-today{% endif %} {% if day.is_past %}is-past{% endif %}">
      <span class="cal-weekday">{{ day.label }}</span>
      <span class="cal-date">{{ day.date }}</span>
      {% if day.workout %}
        <span class="cal-dot cal-dot-{{ day.workout.type }}" title="{{ day.workout_type_label }}"></span>
      {% elif day.committed %}
        <span class="cal-dot cal-dot-committed"></span>
      {% else %}
        <span class="cal-dot cal-dot-empty"></span>
      {% endif %}
    </div>
    {% endfor %}
  </div>
</section>

<!-- WEEKLY GOALS -->
<section class="section-block">
  <p class="eyebrow section-eyebrow">Goals</p>
  <div class="card">
    {% include "partials/weekly_goals.html" %}
  </div>
</section>

<!-- COMMIT YOUR WEEK -->
<section class="section-block">
  <p class="eyebrow section-eyebrow">Commit your week</p>
  <div class="card">
    <form method="post" action="/plan/commit">
      <div class="day-checkboxes">
        {% set day_keys = ["mon","tue","wed","thu","fri","sat","sun"] %}
        {% set day_labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"] %}
        {% for key, label in zip(day_keys, day_labels) %}
        <label class="day-checkbox {% if key in committed_days %}is-checked{% endif %}">
          <input type="checkbox" name="days" value="{{ key }}"
                 {% if key in committed_days %}checked{% endif %}>
          <span>{{ label }}</span>
        </label>
        {% endfor %}
      </div>
      <button class="btn btn-primary btn-block" style="margin-top:1.25rem">Lock it in</button>
    </form>
  </div>
</section>

{% endblock %}
```

### 4g. Update `app/web/templates/history.html`

Replace the current flat list with a day-grouped structure:

```html
{% extends "base.html" %}
{% block content %}

<header class="page-header">
  <h1 class="heading">History</h1>
</header>

<div class="history-list">
  {% for entry in days %}
  <div class="history-day reveal">
    <p class="history-date-label eyebrow">{{ entry.date_label }}</p>

    {% for workout in entry.workouts %}
    <a href="/workout/{{ workout.id }}" class="history-item history-item-workout">
      <span class="pill pill-{{ workout.type }}">{{ workout.type | title }}</span>
      {% if workout.actual_minutes %}
        <span class="history-duration">{{ workout.actual_minutes }} min</span>
      {% endif %}
      {% if workout.rating %}
        <span class="history-rating">★ {{ workout.rating }}</span>
      {% endif %}
    </a>
    {% endfor %}

    {% if entry.habit %}
    <div class="history-habits">
      {% if entry.habit.stretch_done %}
        <span class="habit-tag">Stretch · {{ entry.habit.stretch_minutes or 7 }}m</span>
      {% endif %}
      {% if entry.habit.balance_done %}
        <span class="habit-tag">Balance</span>
      {% endif %}
      {% if entry.walk_count > 0 %}
        <span class="habit-tag">{{ entry.walk_count }}× walk</span>
      {% endif %}
    </div>
    {% endif %}
  </div>
  {% else %}
  <p class="muted-text" style="padding:2rem 0; text-align:center">No history yet.</p>
  {% endfor %}
</div>

{% endblock %}
```

Update the route to pass `active="history"` and ensure `workout.type | title` renders
readable labels. Add a `type_label` filter or property if needed (squat → "Squat", etc.).

### 4h. Update `app/web/templates/partials/finish_form.html`

Add cardio tracking section before the rating inputs:

```html
<!-- CARDIO LOGGED (new section) -->
<div class="finish-section">
  <p class="eyebrow">Cardio logged</p>
  <div class="cardio-inputs">
    <label class="cardio-input-label">
      <span>Low-intensity (min)</span>
      <input type="number" name="cardio_minutes_low"
             value="{{ suggested_cardio_low }}" min="0" max="120"
             inputmode="numeric" class="cardio-input">
    </label>
    <label class="cardio-input-label">
      <span>High-intensity (min)</span>
      <input type="number" name="cardio_minutes_high"
             value="{{ suggested_cardio_high }}" min="0" max="120"
             inputmode="numeric" class="cardio-input">
    </label>
  </div>
  <p class="finish-hint">Meal walks count separately. These are gym cardio minutes.</p>
</div>
```

---

## Phase 5 — CSS Layer

Add to `app/web/static/app.css`. All additions, no removals.

```css
/* ── Section spacing ───────────────────────────────────── */
.section-block { margin-bottom: 1.75rem; }
.section-eyebrow { margin-bottom: 0.625rem; }

/* ── Progress bars (weekly goals) ──────────────────────── */
.goals-list { display: flex; flex-direction: column; gap: 0.875rem; }
.goal-row {
  display: grid;
  grid-template-columns: 6.5rem 1fr 4.5rem;
  align-items: center;
  gap: 0.625rem;
}
.goal-label { font-family: var(--mono); font-size: 0.7rem; text-transform: uppercase;
              letter-spacing: 0.08em; color: var(--muted); }
.goal-bar-track { height: 5px; background: var(--bg); border-radius: 3px; overflow: hidden; }
.goal-bar-fill { height: 100%; background: var(--accent); border-radius: 3px;
                  transition: width 0.5s ease; min-width: 2px; }
.goal-bar-fill.is-done { background: var(--good); }
.goal-value { font-family: var(--mono); font-size: 0.75rem; color: var(--text);
              text-align: right; white-space: nowrap; }
.goal-target { color: var(--faint); }

/* ── Habit chips ───────────────────────────────────────── */
.habit-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.habit-chip {
  background: var(--bg-elev);
  border: 1px solid var(--bg);
  border-radius: 0.75rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-height: 5rem;
  transition: border-color 0.2s;
}
.habit-chip.is-done {
  border-color: var(--good);
  background: color-mix(in srgb, var(--good) 8%, var(--bg-elev));
}
.habit-chip .chip-label { font-size: 0.9rem; font-weight: 500; color: var(--text); }
.habit-chip .chip-hint { font-size: 0.7rem; color: var(--faint); }
.habit-chip .chip-time { font-family: var(--mono); font-size: 0.7rem; color: var(--muted); }
.habit-chip .chip-btn {
  background: none; border: none; padding: 0; cursor: pointer;
  text-align: left; display: flex; flex-direction: column; gap: 0.2rem;
  width: 100%; height: 100%;
}
.chip-check-icon { color: var(--good); width: 1rem; height: 1rem; margin-bottom: 0.25rem; }

/* ── Walk chips ────────────────────────────────────────── */
.walk-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.625rem; }
.walk-chip {
  background: var(--bg-elev);
  border: 1px solid var(--bg);
  border-radius: 0.75rem;
  padding: 0.875rem 0.75rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  text-align: center;
  min-height: 4.5rem;
  transition: border-color 0.2s;
}
.walk-chip.is-done {
  border-color: var(--good);
  background: color-mix(in srgb, var(--good) 8%, var(--bg-elev));
}
.walk-meal-label { font-size: 0.75rem; text-transform: uppercase;
                    letter-spacing: 0.06em; color: var(--muted);
                    font-family: var(--mono); }
.chip-btn-walk {
  background: none; border: none; cursor: pointer;
  font-size: 0.8rem; color: var(--accent); padding: 0.25rem;
}
.walk-chip .chip-time { font-family: var(--mono); font-size: 0.65rem; color: var(--muted); }

/* ── Calendar strip ────────────────────────────────────── */
.cal-strip {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.375rem;
}
.cal-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.25rem 0.625rem;
  border-radius: 0.625rem;
  border: 1px solid transparent;
  transition: background 0.15s;
}
.cal-day.is-today {
  background: var(--bg-elev);
  border-color: var(--accent);
}
.cal-day.is-past { opacity: 0.65; }
.cal-weekday { font-family: var(--mono); font-size: 0.6rem;
               text-transform: uppercase; color: var(--muted); }
.cal-date { font-family: var(--mono); font-size: 0.85rem; color: var(--text); }
.cal-dot {
  width: 7px; height: 7px; border-radius: 50%; margin-top: 0.125rem;
}
.cal-dot-push        { background: var(--accent); }
.cal-dot-pull        { background: var(--good); }
.cal-dot-squat       { background: var(--warn); }
.cal-dot-conditioning { background: #e4846b; }
.cal-dot-committed   { background: transparent; border: 1.5px dashed var(--faint); }
.cal-dot-empty       { background: transparent; }

/* ── History ───────────────────────────────────────────── */
.history-list { display: flex; flex-direction: column; gap: 0; }
.history-day { padding: 0.875rem 0; border-bottom: 1px solid var(--bg-elev); }
.history-day:last-child { border-bottom: none; }
.history-date-label { margin-bottom: 0.5rem; }
.history-item-workout {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.5rem 0; color: var(--text); text-decoration: none;
}
.history-duration { font-family: var(--mono); font-size: 0.8rem; color: var(--muted); }
.history-rating { font-size: 0.8rem; color: var(--warn); margin-left: auto; }
.history-habits { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.375rem; }
.habit-tag {
  font-family: var(--mono); font-size: 0.65rem; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--muted);
  background: var(--bg-elev); border-radius: 0.375rem;
  padding: 0.2rem 0.5rem;
}

/* ── Finish form — cardio section ──────────────────────── */
.finish-section { margin-bottom: 1.25rem; }
.cardio-inputs { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;
                  margin-top: 0.625rem; }
.cardio-input-label { display: flex; flex-direction: column; gap: 0.375rem;
                       font-size: 0.8rem; color: var(--muted); }
.cardio-input { background: var(--bg); border: 1px solid var(--bg-elev); border-radius: 0.5rem;
                 padding: 0.5rem 0.625rem; font-family: var(--mono); font-size: 1rem;
                 color: var(--text); width: 100%; }
.finish-hint { font-size: 0.72rem; color: var(--faint); margin-top: 0.375rem;
                font-style: italic; }

/* ── Pill: squat type ──────────────────────────────────── */
.pill-squat { background: color-mix(in srgb, var(--warn) 15%, transparent);
               color: var(--warn); border: 1px solid color-mix(in srgb, var(--warn) 30%, transparent); }

/* ── Streak badge (home header) ────────────────────────── */
.streak-badge { display: flex; flex-direction: column; align-items: center;
                 background: var(--bg-elev); border-radius: 0.75rem;
                 padding: 0.5rem 0.875rem; }
.streak-badge .stat-num { font-family: var(--mono); font-size: 1.75rem;
                            color: var(--accent); line-height: 1; }
.streak-badge .stat-label { font-family: var(--mono); font-size: 0.6rem;
                              text-transform: uppercase; color: var(--muted); }
```

---

## Implementation Order & Checklist

Work in phases. Each phase should be independently testable before moving on.

### Phase 1 — Database (foundation)
- [ ] Add `DailyHabit` model to `app/db/models.py`
- [ ] Add `DailyHabit` relationship to `User` in `app/db/models.py`
- [ ] Add `cardio_minutes_low`, `cardio_minutes_high` to `Workout` in `app/db/models.py`
- [ ] Update type comment on `Workout.type` (legs_light → squat)
- [ ] Ensure `engine.py` / `create_all` picks up `DailyHabit` (import the model)
- [ ] Write and test `scripts/migrate_v2.py`

### Phase 2 — Domain
- [ ] Create `app/domain/habits.py` with all 5 functions + helpers
- [ ] Add `weekly_goals()` to `app/domain/stats.py`
- [ ] In `app/domain/planner.py`:
  - [ ] Rename `_build_legs_light` → `_build_squat`, update type string and content
  - [ ] Rename `_LEGS_CARDIO` → `_SQUAT_CARDIO`
  - [ ] Update `DEFAULT_TYPE_ROTATION`
  - [ ] Update `_decide_workout_type` (all `legs_light` refs → `squat`)
  - [ ] Update `get_cardio_protocol` dict
  - [ ] Update `BUILDERS` dict
  - [ ] Add `CARDIO_SUGGESTION` dict

### Phase 3 — Routes
- [ ] Create `app/web/routes/habits.py`
- [ ] Update `app/web/routes/home.py` (fetch today_habit + goals)
- [ ] Update `app/web/routes/workout.py` (finish: accept cardio fields; log view: pass suggestions)
- [ ] Create `app/web/routes/week.py`
- [ ] Update `app/web/routes/history.py` (day-grouped + habits)
- [ ] Register habits + week routers in `app/main.py`

### Phase 4 — Templates
- [ ] Update `base.html` (nav: Today/Week/History with new icons)
- [ ] Redesign `home.html` (4 sections: session, habits, walks, goals)
- [ ] Create `partials/habit_chip.html`
- [ ] Create `partials/walk_chip.html`
- [ ] Create `partials/weekly_goals.html`
- [ ] Create `week.html` (calendar + goals + commit)
- [ ] Update `history.html` (day-grouped, habits shown)
- [ ] Update `partials/finish_form.html` (cardio inputs)
- [ ] Update `workout/log.html` if any `legs_light` label references exist

### Phase 5 — CSS
- [ ] Add all new CSS to `app/web/static/app.css`
- [ ] Verify no visual regressions on existing set-row, exercise card, pill components

---

## Key constraints to respect

1. **Existing workout logging is untouched** — set-by-set entry, HTMX swap, progression logic
   all stay exactly as-is. The only change to the session page is the finish form.

2. **HTMX pattern** — habit and walk chips must follow the same pattern as `set_row.html`:
   the POST endpoint returns the full updated chip HTML (outerHTML swap). No page reloads.

3. **Single user** — `get_user_id` dependency returns the default user ID (1). No auth changes.

4. **No Alembic** — use `scripts/migrate_v2.py` for schema changes on existing DBs. The
   `engine.py` `create_all` covers new installs.

5. **legs_light data in existing DB** — existing `workouts` rows with `type='legs_light'` will
   still exist. History and stats queries must handle both `squat` and `legs_light` as
   valid strength types (or add a migration to UPDATE existing rows).
   Recommended: add to migration script:
   ```sql
   UPDATE workouts SET type = 'squat' WHERE type = 'legs_light';
   ```

6. **Jinja2 includes** — partial templates need all their variables in the template context
   when included via `{% include %}`. Use `{% set %}` blocks before each include, or pass
   the structured data as a dict in the context.
