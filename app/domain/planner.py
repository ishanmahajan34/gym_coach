"""
Workout planner. Pure logic — takes history, produces a workout structure.

Design principles for this user:
- Weight loss focus: every session pairs lifting with 15-20 min cardio (or substantial cardio day)
- Intermediate lifter, basic gym, 45-60 min
- Light on legs: ONE squat day per week, max 25 min lift + cardio
- Variation: don't repeat the same exercise selection twice in a row
- Smart rotation: pick exercises to balance freshness across muscle groups
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
import random
from typing import Optional

from app.domain.exercises import (
    CATALOG,
    Exercise,
    all_compounds_for,
    all_isolations_for,
)


# How a typical week rotates. Sunday = index 6, Monday = 0.
# Pattern: Push, Pull, Conditioning, Legs-light, Push/Pull alt, plus 2 rest days.
DEFAULT_TYPE_ROTATION = ["push", "pull", "conditioning", "squat", "push", "pull"]


@dataclass
class PlannedExercise:
    slug: str
    name: str
    muscle_group: str
    sets: int
    reps: int
    target_weight: Optional[float] = None  # in lb (None = bodyweight or "feel it out")
    notes: str = ""


@dataclass
class CardioProtocol:
    machine: str          # "Treadmill" | "Elliptical" | "Bike"
    duration_min: int
    steps: list[str]      # ordered protocol steps shown to user
    goal_note: str        # why this helps with weight loss


@dataclass
class WorkoutPlan:
    type: str                       # push|pull|squat|conditioning|rest
    duration_minutes: int
    title: str                      # human title, e.g. "Pull + Cardio"
    summary: str                    # 1-2 sentence description
    warmup: list[str]
    exercises: list[PlannedExercise]
    cardio: Optional[str] = None    # kept for backwards compat, unused in new code


# ---------- Helpers ----------

def _recent_slugs(history: list[dict], days: int = 10) -> set[str]:
    """Slugs used in the last N days — to avoid repetition."""
    cutoff = date.today() - timedelta(days=days)
    slugs = set()
    for w in history:
        if w.get("date") and w["date"] >= cutoff:
            for s in w.get("sets", []):
                slugs.add(s["exercise_slug"])
    return slugs


def _pick_one(pool: list[Exercise], avoid: set[str], rng: random.Random) -> Exercise:
    """Pick an exercise from pool, preferring ones not in 'avoid'. Falls back if all stale."""
    fresh = [e for e in pool if e.slug not in avoid]
    chosen = rng.choice(fresh) if fresh else rng.choice(pool)
    return chosen


def _decide_workout_type(
    history: list[dict],
    committed_today: bool,
    rng: random.Random,
) -> str:
    """
    Decide today's workout type using:
      1) what's been done in the last 7 days
      2) freshness of muscle groups
      3) the rotation skeleton

    Rules:
    - Never two of the same type in a row (push/pull alternate)
    - Legs_light at most once per 7 days, but at least once per 8 days
    - One conditioning day per week
    - If they did 4 sessions already this week, return 'rest' as a hint
    """
    last_7 = [
        w for w in history
        if w.get("date") and (date.today() - w["date"]).days <= 7
        and w.get("type") != "rest"
    ]
    types_done = [w["type"] for w in last_7]
    last_type = history[0]["type"] if history else None

    # Force squat if 8+ days since last squat day — gentle nudge.
    last_legs = next((w for w in history if w.get("type") in ("squat", "legs_light")), None)
    days_since_legs = (date.today() - last_legs["date"]).days if last_legs else 99
    if days_since_legs >= 8:
        return "squat"

    # Need a conditioning day if none this week
    if "conditioning" not in types_done and len(last_7) >= 2:
        # 25% chance to drop in conditioning, otherwise continue rotation
        if rng.random() < 0.4:
            return "conditioning"

    # Avoid back-to-back same-type
    candidates = ["push", "pull"]
    if last_type in candidates:
        candidates.remove(last_type)

    # Add squat if not done in 5+ days
    if days_since_legs >= 5 and "squat" not in types_done and "legs_light" not in types_done:
        candidates.append("squat")

    return rng.choice(candidates)


# ---------- Plan builders per type ----------

def _build_push(history: list[dict], rng: random.Random) -> WorkoutPlan:
    avoid = _recent_slugs(history, days=10)

    chest_compound = _pick_one(all_compounds_for("chest"), avoid, rng)
    chest_iso = _pick_one(all_isolations_for("chest"), avoid, rng)
    shoulders_compound = _pick_one(all_compounds_for("shoulders"), avoid, rng)
    shoulders_iso = _pick_one(all_isolations_for("shoulders"), avoid, rng)
    triceps = _pick_one(all_isolations_for("triceps"), avoid, rng)

    exercises = [
        PlannedExercise(chest_compound.slug, chest_compound.name, "chest", 4, 8),
        PlannedExercise(shoulders_compound.slug, shoulders_compound.name, "shoulders", 3, 10),
        PlannedExercise(chest_iso.slug, chest_iso.name, "chest", 3, 12),
        PlannedExercise(shoulders_iso.slug, shoulders_iso.name, "shoulders", 3, 12),
        PlannedExercise(triceps.slug, triceps.name, "triceps", 3, 12),
    ]

    return WorkoutPlan(
        type="push",
        duration_minutes=55,
        title="Push + Cardio",
        summary="Chest, shoulders, triceps. Then 15 min incline walk.",
        warmup=["5 min easy bike or walk", "Arm circles, band pull-aparts"],
        exercises=exercises,
        cardio="15 min incline treadmill walk @ 3.0-3.3 mph, 10-12% grade",
    )


def _build_pull(history: list[dict], rng: random.Random) -> WorkoutPlan:
    avoid = _recent_slugs(history, days=10)

    back_compound_1 = _pick_one(all_compounds_for("back"), avoid, rng)
    avoid_2 = avoid | {back_compound_1.slug}
    back_compound_2 = _pick_one(all_compounds_for("back"), avoid_2, rng)
    rear_delts = CATALOG.get("rear_delt_fly") or CATALOG["face_pull"]
    back_iso = _pick_one(all_isolations_for("back"), avoid, rng)
    biceps = _pick_one(all_isolations_for("biceps"), avoid, rng)

    exercises = [
        PlannedExercise(back_compound_1.slug, back_compound_1.name, "back", 4, 8),
        PlannedExercise(back_compound_2.slug, back_compound_2.name, "back", 3, 10),
        PlannedExercise(back_iso.slug, back_iso.name, "back", 3, 12),
        PlannedExercise(rear_delts.slug, rear_delts.name, "shoulders", 3, 15),
        PlannedExercise(biceps.slug, biceps.name, "biceps", 3, 10),
    ]

    return WorkoutPlan(
        type="pull",
        duration_minutes=55,
        title="Pull + Cardio",
        summary="Back, rear delts, biceps. Then 15 min steady cardio.",
        warmup=["5 min row or bike", "Band pull-aparts, scap pulls"],
        exercises=exercises,
        cardio="15 min bike at conversational pace OR incline walk",
    )


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


def _build_conditioning(history: list[dict], rng: random.Random) -> WorkoutPlan:
    """Calorie-burn focused, full-body circuits + intervals."""
    options = [
        WorkoutPlan(
            type="conditioning",
            duration_minutes=50,
            title="Bike Intervals + Core",
            summary="Calorie crusher without trashing recovery.",
            warmup=["5 min easy bike"],
            exercises=[
                PlannedExercise("plank", "Plank", "core", 3, 0, notes="45-60 sec hold"),
                PlannedExercise("russian_twist", "Russian Twist", "core", 3, 20),
            ],
            cardio="Bike intervals: 30s hard / 90s easy x 10 rounds (~25 min)",
        ),
        WorkoutPlan(
            type="conditioning",
            duration_minutes=50,
            title="Incline Walk + Upper Circuit",
            summary="Long walk plus a light full-body finisher.",
            warmup=["3 min easy walk"],
            exercises=[
                PlannedExercise("pushups", "Push-ups", "chest", 3, 12),
                PlannedExercise("db_row", "Single-Arm DB Row", "back", 3, 10),
                PlannedExercise("plank", "Plank", "core", 3, 0, notes="45 sec"),
            ],
            cardio="25-30 min incline walk @ 3.0-3.3 mph, 10-12%",
        ),
        WorkoutPlan(
            type="conditioning",
            duration_minutes=50,
            title="Treadmill Intervals + Core",
            summary="Run/walk intervals — short, hard, effective.",
            warmup=["5 min easy walk"],
            exercises=[
                PlannedExercise("hanging_knee_raise", "Hanging Knee Raise", "core", 3, 12),
                PlannedExercise("plank", "Plank", "core", 3, 0, notes="45-60 sec"),
            ],
            cardio="Treadmill: 1 min run @ 6 mph / 2 min walk @ 3.5 mph, x 8 rounds",
        ),
    ]
    return rng.choice(options)


def _build_rest() -> WorkoutPlan:
    return WorkoutPlan(
        type="rest",
        duration_minutes=0,
        title="Rest day",
        summary="Recovery is part of the work. Walk if you feel like it. Sleep well.",
        warmup=[],
        exercises=[],
        cardio="Optional: 20-30 min easy walk, no incline",
    )


# ---------- Cardio protocol pools ----------

_PUSH_PULL_CARDIO: list[CardioProtocol] = [
    CardioProtocol(
        machine="Treadmill",
        duration_min=15,
        steps=[
            "2 min easy walk @ 3.0 mph — transition from weights",
            "3 min fast walk @ 4.5 mph — elevate heart rate",
            "4 min incline walk @ 3.3 mph, 10% grade — fat burn zone",
            "2 min fast walk @ 4.5 mph — push",
            "4 min incline walk @ 3.3 mph, 12% grade — finish strong",
        ],
        goal_note="Alternating pace and incline keeps heart rate elevated without joint stress from running.",
    ),
    CardioProtocol(
        machine="Elliptical",
        duration_min=16,
        steps=[
            "3 min easy @ resistance 4 — let heart rate settle",
            "2 min moderate @ resistance 7 — finding rhythm",
            "1 min hard sprint @ resistance 10, full effort",
            "Repeat moderate → sprint 3 more times (6 min)",
            "2 min easy cooldown @ resistance 3",
        ],
        goal_note="Low-impact intervals — burns calories, protects the joints after a heavy lift.",
    ),
    CardioProtocol(
        machine="Bike",
        duration_min=14,
        steps=[
            "2 min easy spin — legs loose",
            "30s hard sprint @ max effort",
            "90s easy recovery spin",
            "Repeat sprint/recovery 6 more times — 7 rounds total",
            "2 min easy spin to close",
        ],
        goal_note="HIIT spikes metabolism for hours after. Short, effective, efficient.",
    ),
    CardioProtocol(
        machine="Treadmill",
        duration_min=15,
        steps=[
            "2 min walk @ 3.5 mph — warm down from lifting",
            "1 min jog @ 5.0 mph",
            "2 min walk @ 3.5 mph",
            "Repeat jog/walk for 5 rounds total",
            "1 min easy walk cooldown",
        ],
        goal_note="Run/walk intervals are sustainable and build aerobic base without burning out recovery.",
    ),
    CardioProtocol(
        machine="Elliptical",
        duration_min=18,
        steps=[
            "5 min moderate pace @ resistance 5-6 — zone 2 warm-up",
            "8 min at a pace where talking is hard but not impossible @ resistance 7-8",
            "3 min hard push — resistance 9-10, arms driving",
            "2 min easy cooldown",
        ],
        goal_note="Zone 2 steady state maximizes fat oxidation. The 3-min push at the end adds a calorie spike.",
    ),
    CardioProtocol(
        machine="Treadmill",
        duration_min=15,
        steps=[
            "15 min incline walk @ 3.2 mph, 10-12% grade",
            "Don't hold the rails — engage your core and glutes",
            "Keep breathing steady; you should be able to speak short sentences",
        ],
        goal_note="Incline walking is one of the highest fat-burn-per-minute options. Deeply underrated.",
    ),
]

_SQUAT_CARDIO: list[CardioProtocol] = [
    CardioProtocol(
        machine="Treadmill",
        duration_min=20,
        steps=[
            "20 min incline walk @ 3.0-3.3 mph, 10% grade",
            "Keep it easy — this extends leg work gently",
            "Focus on posture, heel-to-toe strike, glutes engaged",
        ],
        goal_note="Incline walking after legs adds calorie burn while keeping load light on fatigued muscles.",
    ),
    CardioProtocol(
        machine="Elliptical",
        duration_min=20,
        steps=[
            "5 min easy @ resistance 4 — warm the knees",
            "12 min moderate steady state @ resistance 6-7",
            "3 min progressive push — increase resistance each minute: 8 → 9 → 10",
        ],
        goal_note="Zero impact — the elliptical is the right call when legs are already worked.",
    ),
    CardioProtocol(
        machine="Treadmill",
        duration_min=20,
        steps=[
            "20 min @ 3.0 mph, 8% grade — slow and deliberate",
            "Optional: raise incline to 10% after 10 min if legs feel okay",
        ],
        goal_note="Keep this genuinely easy. Legs had their session. The point is movement and calorie burn, not fatigue.",
    ),
]

_CONDITIONING_CARDIO: list[CardioProtocol] = [
    CardioProtocol(
        machine="Bike",
        duration_min=25,
        steps=[
            "3 min easy spin — warm up",
            "30s all-out sprint @ maximum resistance",
            "90s easy recovery spin",
            "Repeat for 10 rounds — 20 min of intervals",
            "2 min easy cooldown spin",
        ],
        goal_note="10 HIIT rounds on the bike torch more calories than 45 min of steady cardio. This is the workout.",
    ),
    CardioProtocol(
        machine="Treadmill",
        duration_min=26,
        steps=[
            "3 min easy walk @ 3.5 mph — warm up",
            "1 min run @ 6.0 mph",
            "2 min walk @ 3.5 mph",
            "Repeat run/walk for 8 rounds — 24 min total",
            "2 min easy walk cooldown",
        ],
        goal_note="Run/walk intervals build fitness without destroying recovery. 8 rounds is the right dose.",
    ),
    CardioProtocol(
        machine="Elliptical",
        duration_min=28,
        steps=[
            "5 min easy warm-up @ resistance 4-5",
            "45s high-resistance sprint @ resistance 10-12, full effort",
            "75s moderate recovery @ resistance 6",
            "Repeat sprint/recovery for 8 rounds — 16 min",
            "3 min easy cooldown",
        ],
        goal_note="High-resistance elliptical intervals are joint-friendly and brutal — best of both worlds.",
    ),
    CardioProtocol(
        machine="Treadmill",
        duration_min=26,
        steps=[
            "20 min incline walk @ 3.2 mph, 10% grade — long zone 2 block",
            "2 min flat fast walk @ 4.5 mph — shift gears",
            "2 min jog @ 5.5 mph — push",
            "2 min easy walk cooldown",
        ],
        goal_note="Incline walk followed by a run finish. Volume + intensity in one session.",
    ),
]


def get_cardio_protocol(workout_type: str, workout_id: int) -> Optional[CardioProtocol]:
    """Pick a cardio protocol. Deterministic per workout_id so it doesn't change on refresh."""
    pools: dict[str, list[CardioProtocol]] = {
        "push": _PUSH_PULL_CARDIO,
        "pull": _PUSH_PULL_CARDIO,
        "squat": _SQUAT_CARDIO,
        "legs_light": _SQUAT_CARDIO,  # legacy rows
        "conditioning": _CONDITIONING_CARDIO,
    }
    pool = pools.get(workout_type)
    if not pool:
        return None
    return random.Random(workout_id).choice(pool)


CARDIO_SUGGESTION: dict[str, dict] = {
    "push":         {"low": 0,  "high": 15},
    "pull":         {"low": 15, "high": 0},
    "squat":        {"low": 20, "high": 0},
    "legs_light":   {"low": 20, "high": 0},  # legacy rows
    "conditioning": {"low": 0,  "high": 30},
    "rest":         {"low": 0,  "high": 0},
}


# ---------- Public API ----------

BUILDERS = {
    "push": _build_push,
    "pull": _build_pull,
    "squat": _build_squat,
    "legs_light": _build_squat,  # legacy alias
    "conditioning": _build_conditioning,
}


def generate_plan(
    history: list[dict],
    *,
    workout_type: Optional[str] = None,
    seed: Optional[int] = None,
) -> WorkoutPlan:
    """
    Generate a workout plan.

    Args:
        history: list of dicts with at least {date, type, sets:[{exercise_slug,...}]}
                 ordered most-recent first
        workout_type: force a specific type, or None to auto-decide
        seed: optional seed for deterministic testing
    """
    rng = random.Random(seed) if seed is not None else random.Random()

    if workout_type is None:
        workout_type = _decide_workout_type(history, committed_today=True, rng=rng)

    if workout_type == "rest":
        return _build_rest()

    builder = BUILDERS.get(workout_type)
    if builder is None:
        raise ValueError(f"Unknown workout type: {workout_type}")

    return builder(history, rng)
