"""History list — day-grouped with workouts and habits."""
from datetime import date, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.deps import SessionDep, CurrentUserDep
from app.db.models import Workout, DailyHabit
from app.domain.habits import walk_count

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request, session: SessionDep, user: CurrentUserDep):
    today = date.today()
    cutoff = today - timedelta(days=29)

    result = await session.execute(
        select(Workout).where(
            Workout.user_id == user.id,
            Workout.date >= cutoff,
        ).order_by(Workout.date.desc())
    )
    workouts_by_date: dict[date, list] = {}
    for w in result.scalars().all():
        workouts_by_date.setdefault(w.date, []).append(w)

    result2 = await session.execute(
        select(DailyHabit).where(
            DailyHabit.user_id == user.id,
            DailyHabit.date >= cutoff,
        )
    )
    habits_by_date = {h.date: h for h in result2.scalars().all()}

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
        request,
        "history.html",
        {"days": days, "active_nav": "history"},
    )
