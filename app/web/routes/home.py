"""Home page route."""
from datetime import date, timedelta, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.deps import SessionDep, CurrentUserDep
from app.domain import workouts as wo
from app.domain import stats as st
from app.domain import habits as habit_domain
from app.coach.inspiration import pick_thought


router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

TYPE_LABELS = {
    "push": "Push",
    "pull": "Pull",
    "squat": "Squat",
    "legs_light": "Squat",
    "conditioning": "Cardio",
    "rest": "Rest",
}


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _fmt_time(dt) -> str | None:
    return dt.strftime("%-I:%M %p") if dt else None


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, session: SessionDep, user: CurrentUserDep):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    workout = await wo.todays_workout(session, user.id)

    plan_title = ""
    plan_summary = ""
    if workout:
        plan_title = {
            "push": "Push + Cardio",
            "pull": "Pull + Cardio",
            "squat": "Squat + Cardio",
            "legs_light": "Squat + Cardio",
            "conditioning": "Conditioning",
            "rest": "Rest day",
        }.get(workout.type, workout.type)
        plan_summary = workout.notes or ""

    streak = await st.current_streak(session, user.id)
    week = await st.workouts_this_week(session, user.id)
    total = await st.total_workouts(session, user.id)

    today_habit = await habit_domain.get_or_create_today(session, user.id, today)
    await session.commit()

    goals = await st.weekly_goals(session, user.id, week_start)

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "today_str": today.strftime("%A · %B %-d").upper(),
            "greeting": _greeting(),
            "workout": workout,
            "workout_type_label": TYPE_LABELS.get(workout.type, workout.type) if workout else "",
            "plan_title": plan_title,
            "plan_summary": plan_summary,
            "stats": {"streak": streak, "this_week": week, "week_target": 4, "total": total},
            "today_habit": today_habit,
            "stretch_logged_time": _fmt_time(today_habit.stretch_logged_at),
            "balance_logged_time": _fmt_time(today_habit.balance_logged_at),
            "walk_breakfast_logged_time": _fmt_time(today_habit.walk_breakfast_at),
            "walk_lunch_logged_time": _fmt_time(today_habit.walk_lunch_at),
            "walk_dinner_logged_time": _fmt_time(today_habit.walk_dinner_at),
            "goals": goals,
            "thought": pick_thought(),
            "active_nav": "home",
        },
    )
