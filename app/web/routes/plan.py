"""Week planner."""
from datetime import date, timedelta
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc

from app.deps import SessionDep, CurrentUserDep
from app.db.models import WeekPlan


router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


def this_week_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


@router.get("/plan/week", response_class=HTMLResponse)
async def week_view(request: Request, session: SessionDep, user: CurrentUserDep):
    week_start = this_week_monday()
    result = await session.execute(
        select(WeekPlan)
        .where(WeekPlan.user_id == user.id, WeekPlan.week_start == week_start)
        .order_by(desc(WeekPlan.created_at))
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    committed = plan.committed_days if plan else []

    days = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]

    return templates.TemplateResponse(
        request,
        "plan/week.html",
        {"week_start": week_start, "days": days, "committed": committed},
    )


@router.post("/plan/commit")
async def commit_week(
    session: SessionDep,
    user: CurrentUserDep,
    days: list[str] = Form(default=[]),
):
    week_start = this_week_monday()
    result = await session.execute(
        select(WeekPlan)
        .where(WeekPlan.user_id == user.id, WeekPlan.week_start == week_start)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        plan = WeekPlan(user_id=user.id, week_start=week_start, committed_days=days, plan={})
        session.add(plan)
    else:
        plan.committed_days = days
    await session.commit()
    return RedirectResponse(url="/", status_code=303)
