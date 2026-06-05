"""Sanity checks for the planner."""
from datetime import date, timedelta
from app.domain import planner as pl


def test_no_history_picks_a_type():
    plan = pl.generate_plan([], seed=42)
    assert plan.type in {"push", "pull", "legs_light", "conditioning"}
    assert len(plan.exercises) > 0


def test_legs_forced_after_8_days():
    history = [
        {"date": date.today() - timedelta(days=10), "type": "legs_light", "rating": 4, "sets": []},
        {"date": date.today() - timedelta(days=1), "type": "push", "rating": 4, "sets": []},
    ]
    plan = pl.generate_plan(history, seed=1)
    assert plan.type == "legs_light"


def test_legs_light_is_short():
    plan = pl.generate_plan([], workout_type="legs_light", seed=1)
    assert plan.duration_minutes <= 50
    leg_exercises = [e for e in plan.exercises if e.muscle_group == "legs"]
    # Legs day shouldn't have more than 2-3 leg exercises
    assert 1 <= len(leg_exercises) <= 3


def test_no_repeat_back_to_back():
    history = [
        {"date": date.today() - timedelta(days=1), "type": "push", "rating": 4, "sets": []},
    ]
    plan = pl.generate_plan(history, seed=42)
    assert plan.type != "push"


def test_push_includes_chest_and_shoulders():
    plan = pl.generate_plan([], workout_type="push", seed=1)
    groups = {e.muscle_group for e in plan.exercises}
    assert "chest" in groups
    assert "shoulders" in groups
    assert "triceps" in groups


def test_pull_includes_back_and_biceps():
    plan = pl.generate_plan([], workout_type="pull", seed=1)
    groups = {e.muscle_group for e in plan.exercises}
    assert "back" in groups
    assert "biceps" in groups
