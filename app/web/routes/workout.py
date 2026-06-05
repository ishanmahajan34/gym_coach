"""Workout routes: plan, start, log sets, finish."""
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.deps import SessionDep, CurrentUserDep
from app.domain import workouts as wo
from app.domain import planner as pl
from app.domain import progression
from app.domain.exercises import CATALOG
from app.domain.planner import get_cardio_protocol, CARDIO_SUGGESTION


router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.post("/workout/today/plan")
async def plan_today(session: SessionDep, user: CurrentUserDep):
    """Generate a workout for today and persist it."""
    existing = await wo.todays_workout(session, user.id)
    if existing:
        return RedirectResponse(url="/", status_code=303)

    history = await wo.history_for_planner(session, user.id, days=21)
    plan = pl.generate_plan(history)

    # Apply progressive overload from history to populate target_weight
    new_plan_exercises = []
    for ex in plan.exercises:
        last = await wo.last_performance_for(session, user.id, ex.slug)
        suggested = progression.suggest_weight(
            last.actual_weight if last else None,
            last.actual_reps if last else None,
            ex.reps,
            None,  # rating not in WorkoutSet — could pull workout.rating, future polish
        )
        ex.target_weight = suggested
        new_plan_exercises.append(ex)
    plan.exercises = new_plan_exercises

    await wo.create_planned_workout(session, user.id, plan)
    return RedirectResponse(url="/", status_code=303)


@router.post("/workout/{workout_id}/start")
async def start_workout(workout_id: int, session: SessionDep, user: CurrentUserDep):
    workout = await wo.get_workout(session, workout_id)
    if not workout or workout.user_id != user.id:
        raise HTTPException(404)
    await wo.start_workout(session, workout)
    return RedirectResponse(url=f"/workout/{workout_id}", status_code=303)


@router.get("/workout/{workout_id}", response_class=HTMLResponse)
async def view_workout(workout_id: int, request: Request, session: SessionDep, user: CurrentUserDep):
    workout = await wo.get_workout(session, workout_id)
    if not workout or workout.user_id != user.id:
        raise HTTPException(404)

    # Group sets by exercise (ordered)
    grouped: dict[int, dict] = defaultdict(lambda: {"sets": [], "first_set": None, "last_perf": None})
    for s in workout.sets:
        if grouped[s.order_index]["first_set"] is None:
            grouped[s.order_index]["first_set"] = s
        grouped[s.order_index]["sets"].append(s)

    # Pull last performance for header display
    for order, group in grouped.items():
        first = group["first_set"]
        if first:
            group["last_perf"] = await wo.last_performance_for(session, user.id, first.exercise_slug)

    exercises_grouped = [grouped[k] for k in sorted(grouped.keys())]

    plan_title = {
        "push": "Push + Cardio",
        "pull": "Pull + Cardio",
        "squat": "Squat + Cardio",
        "legs_light": "Squat + Cardio",
        "conditioning": "Conditioning",
    }.get(workout.type, workout.type.replace("_", " ").title())

    cardio = get_cardio_protocol(workout.type, workout.id)
    suggestion = CARDIO_SUGGESTION.get(workout.type, {"low": 0, "high": 0})

    return templates.TemplateResponse(
        request,
        "workout/log.html",
        {
            "workout": workout,
            "exercises_grouped": exercises_grouped,
            "plan_title": plan_title,
            "cardio": cardio,
            "catalog": CATALOG,
            "suggested_cardio_low": suggestion["low"],
            "suggested_cardio_high": suggestion["high"],
        },
    )


@router.post("/workout/set/{set_id}", response_class=HTMLResponse)
async def log_set(
    set_id: int,
    request: Request,
    session: SessionDep,
    user: CurrentUserDep,
    weight: Optional[float] = Form(None),
    reps: Optional[int] = Form(None),
):
    """HTMX endpoint - returns the updated row partial."""
    s = await wo.log_set(session, set_id, actual_reps=reps, actual_weight=weight)
    return templates.TemplateResponse(request, "partials/set_row.html", {"s": s})


@router.get("/workout/{workout_id}/finish-form", response_class=HTMLResponse)
async def finish_form(workout_id: int, request: Request, session: SessionDep, user: CurrentUserDep):
    workout = await wo.get_workout(session, workout_id)
    if not workout or workout.user_id != user.id:
        raise HTTPException(404)
    suggestion = CARDIO_SUGGESTION.get(workout.type, {"low": 0, "high": 0})
    return templates.TemplateResponse(
        request,
        "partials/finish_form.html",
        {
            "workout": workout,
            "suggested_cardio_low": suggestion["low"],
            "suggested_cardio_high": suggestion["high"],
        },
    )


@router.post("/workout/{workout_id}/finish")
async def finish_workout(
    workout_id: int,
    session: SessionDep,
    user: CurrentUserDep,
    rating: int = Form(...),
    notes: str = Form(""),
    cardio_minutes_low: Optional[int] = Form(default=None),
    cardio_minutes_high: Optional[int] = Form(default=None),
):
    workout = await wo.get_workout(session, workout_id)
    if not workout or workout.user_id != user.id:
        raise HTTPException(404)
    workout.cardio_minutes_low = cardio_minutes_low
    workout.cardio_minutes_high = cardio_minutes_high
    await wo.finish_workout(session, workout, rating=rating, notes=notes or None)
    return RedirectResponse(url="/", status_code=303)
