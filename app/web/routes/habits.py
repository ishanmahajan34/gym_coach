"""HTMX endpoints for daily habit quick-logging."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.deps import SessionDep, CurrentUserDep
from app.domain import habits as habit_domain

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


def _fmt_time(dt) -> str | None:
    return dt.strftime("%-I:%M %p") if dt else None


@router.post("/habit/stretch", response_class=HTMLResponse)
async def log_stretch(
    request: Request,
    session: SessionDep,
    user: CurrentUserDep,
    minutes: int = Form(default=7),
):
    habit = await habit_domain.log_stretch(session, user.id, date.today(), minutes)
    await session.commit()
    return templates.TemplateResponse(
        request,
        "partials/habit_chip.html",
        {
            "name": "stretch",
            "label": "Stretch",
            "done": habit.stretch_done,
            "logged_time": _fmt_time(habit.stretch_logged_at),
            "default_minutes": 7,
        },
    )


@router.post("/habit/balance", response_class=HTMLResponse)
async def log_balance(
    request: Request,
    session: SessionDep,
    user: CurrentUserDep,
    minutes: int = Form(default=3),
):
    habit = await habit_domain.log_balance(session, user.id, date.today(), minutes)
    await session.commit()
    return templates.TemplateResponse(
        request,
        "partials/habit_chip.html",
        {
            "name": "balance",
            "label": "Balance",
            "done": habit.balance_done,
            "logged_time": _fmt_time(habit.balance_logged_at),
            "default_minutes": 3,
        },
    )


@router.post("/habit/walk/{meal}", response_class=HTMLResponse)
async def log_walk(
    meal: Literal["breakfast", "lunch", "dinner"],
    request: Request,
    session: SessionDep,
    user: CurrentUserDep,
):
    habit = await habit_domain.log_meal_walk(session, user.id, date.today(), meal)
    await session.commit()
    meal_walk_at = {
        "breakfast": habit.walk_breakfast_at,
        "lunch": habit.walk_lunch_at,
        "dinner": habit.walk_dinner_at,
    }[meal]
    meal_labels = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner"}
    return templates.TemplateResponse(
        request,
        "partials/walk_chip.html",
        {
            "meal": meal,
            "meal_label": meal_labels[meal],
            "done": meal_walk_at is not None,
            "logged_time": _fmt_time(meal_walk_at),
        },
    )
