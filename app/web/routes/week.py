"""Week view: calendar strip + goal progress + commit."""
from datetime import date, timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.deps import SessionDep, CurrentUserDep
from app.db.models import Workout, WeekPlan
from app.domain.stats import weekly_goals

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

_WEEKDAYS = [
    ("mon", "Mon"),
    ("tue", "Tue"),
    ("wed", "Wed"),
    ("thu", "Thu"),
    ("fri", "Fri"),
    ("sat", "Sat"),
    ("sun", "Sun"),
]

TYPE_LABELS = {
    "push": "Push",
    "pull": "Pull",
    "squat": "Squat",
    "legs_light": "Squat",
    "conditioning": "Cardio",
    "rest": "Rest",
}


@router.get("/week", response_class=HTMLResponse)
async def week_view(request: Request, session: SessionDep, user: CurrentUserDep):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    result = await session.execute(
        select(Workout).where(
            Workout.user_id == user.id,
            Workout.date >= week_start,
            Workout.date <= week_end,
        )
    )
    week_workouts = {w.date: w for w in result.scalars().all()}

    result2 = await session.execute(
        select(WeekPlan).where(
            WeekPlan.user_id == user.id,
            WeekPlan.week_start == week_start,
        )
    )
    week_plan = result2.scalar_one_or_none()
    committed = set(week_plan.committed_days) if week_plan else set()

    calendar_days = []
    for i, (key, label) in enumerate(_WEEKDAYS):
        day_date = week_start + timedelta(days=i)
        workout = week_workouts.get(day_date)
        calendar_days.append({
            "key": key,
            "label": label,
            "date": day_date.day,
            "is_today": day_date == today,
            "is_past": day_date < today,
            "workout": workout,
            "workout_type_label": TYPE_LABELS.get(workout.type, workout.type) if workout else "",
            "committed": key in committed,
        })

    goals = await weekly_goals(session, user.id, week_start)

    return templates.TemplateResponse(
        request,
        "week.html",
        {
            "calendar_days": calendar_days,
            "commit_day_options": _WEEKDAYS,
            "goals": goals,
            "committed_days": list(committed),
            "week_label": f"{week_start.strftime('%b %-d')} – {week_end.strftime('%b %-d')}",
            "active_nav": "week",
        },
    )


@router.post("/plan/commit")
async def commit_week(
    session: SessionDep,
    user: CurrentUserDep,
    days: list[str] = Form(default=[]),
):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    result = await session.execute(
        select(WeekPlan).where(
            WeekPlan.user_id == user.id, WeekPlan.week_start == week_start
        )
    )
    plan = result.scalar_one_or_none()
    if plan:
        plan.committed_days = days
    else:
        session.add(WeekPlan(user_id=user.id, week_start=week_start, committed_days=days, plan={}))
    await session.commit()
    return RedirectResponse("/week", status_code=303)
