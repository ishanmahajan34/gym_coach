"""
Exercise catalog. Pure data — no logic.

Tagged with:
- equipment: what's needed
- muscle_group: primary muscle
- category: compound vs isolation (compounds rotated more frequently)
- intensity: light/moderate/heavy (used to balance a session)

Calibrated to a basic gym: dumbbells, machines, cables (assumed), treadmill, bike.
Excludes barbell-only lifts (no rack assumed).
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Exercise:
    slug: str
    name: str
    muscle_group: str           # chest, back, shoulders, biceps, triceps, legs, core, cardio
    category: str               # compound | isolation | cardio
    equipment: tuple[str, ...]
    default_sets: int = 3
    default_reps: int = 10
    notes: str = ""


CATALOG: dict[str, Exercise] = {
    # ---------- CHEST ----------
    "db_bench_press": Exercise("db_bench_press", "Dumbbell Bench Press", "chest", "compound",
                               ("dumbbells", "bench"), 3, 10),
    "db_incline_press": Exercise("db_incline_press", "Incline Dumbbell Press", "chest", "compound",
                                 ("dumbbells", "incline_bench"), 3, 10),
    "machine_chest_press": Exercise("machine_chest_press", "Machine Chest Press", "chest", "compound",
                                    ("machine",), 3, 10),
    "db_flyes": Exercise("db_flyes", "Dumbbell Flyes", "chest", "isolation",
                         ("dumbbells", "bench"), 3, 12),
    "cable_crossover": Exercise("cable_crossover", "Cable Crossover", "chest", "isolation",
                                ("cable",), 3, 12),
    "pushups": Exercise("pushups", "Push-ups", "chest", "compound",
                        ("bodyweight",), 3, 12),

    # ---------- BACK ----------
    "lat_pulldown": Exercise("lat_pulldown", "Lat Pulldown", "back", "compound",
                             ("cable",), 3, 10),
    "seated_row": Exercise("seated_row", "Seated Cable Row", "back", "compound",
                           ("cable",), 3, 10),
    "db_row": Exercise("db_row", "Single-Arm Dumbbell Row", "back", "compound",
                       ("dumbbells", "bench"), 3, 10, "Each arm"),
    "machine_row": Exercise("machine_row", "Machine Row", "back", "compound",
                            ("machine",), 3, 10),
    "face_pull": Exercise("face_pull", "Face Pull", "back", "isolation",
                          ("cable",), 3, 15, "Great for posture"),
    "pullover": Exercise("pullover", "Dumbbell Pullover", "back", "isolation",
                         ("dumbbells", "bench"), 3, 12),

    # ---------- SHOULDERS ----------
    "db_shoulder_press": Exercise("db_shoulder_press", "Dumbbell Shoulder Press", "shoulders", "compound",
                                  ("dumbbells",), 3, 10),
    "machine_shoulder_press": Exercise("machine_shoulder_press", "Machine Shoulder Press", "shoulders", "compound",
                                       ("machine",), 3, 10),
    "lateral_raise": Exercise("lateral_raise", "Lateral Raise", "shoulders", "isolation",
                              ("dumbbells",), 3, 12),
    "rear_delt_fly": Exercise("rear_delt_fly", "Rear Delt Fly", "shoulders", "isolation",
                              ("dumbbells",), 3, 12),
    "front_raise": Exercise("front_raise", "Front Raise", "shoulders", "isolation",
                            ("dumbbells",), 3, 12),

    # ---------- BICEPS ----------
    "db_curl": Exercise("db_curl", "Dumbbell Curl", "biceps", "isolation",
                        ("dumbbells",), 3, 10),
    "hammer_curl": Exercise("hammer_curl", "Hammer Curl", "biceps", "isolation",
                            ("dumbbells",), 3, 10),
    "incline_curl": Exercise("incline_curl", "Incline Dumbbell Curl", "biceps", "isolation",
                             ("dumbbells", "incline_bench"), 3, 10),
    "cable_curl": Exercise("cable_curl", "Cable Curl", "biceps", "isolation",
                           ("cable",), 3, 12),

    # ---------- TRICEPS ----------
    "tricep_pushdown": Exercise("tricep_pushdown", "Tricep Pushdown", "triceps", "isolation",
                                ("cable",), 3, 12),
    "overhead_extension": Exercise("overhead_extension", "Overhead Tricep Extension", "triceps", "isolation",
                                   ("dumbbells",), 3, 12),
    "skull_crusher_db": Exercise("skull_crusher_db", "Dumbbell Skull Crusher", "triceps", "isolation",
                                 ("dumbbells", "bench"), 3, 10),
    "tricep_kickback": Exercise("tricep_kickback", "Tricep Kickback", "triceps", "isolation",
                                ("dumbbells",), 3, 12),
    "dips_bench": Exercise("dips_bench", "Bench Dips", "triceps", "compound",
                           ("bench",), 3, 12),

    # ---------- LEGS (kept light, varied — your stated preference) ----------
    "leg_press": Exercise("leg_press", "Leg Press (light)", "legs", "compound",
                          ("machine",), 3, 12, "Keep the load moderate"),
    "leg_extension": Exercise("leg_extension", "Leg Extension", "legs", "isolation",
                              ("machine",), 2, 12),
    "leg_curl": Exercise("leg_curl", "Leg Curl", "legs", "isolation",
                         ("machine",), 2, 12),
    "goblet_squat": Exercise("goblet_squat", "Goblet Squat (light)", "legs", "compound",
                             ("dumbbells",), 3, 10),
    "db_lunges": Exercise("db_lunges", "Dumbbell Lunges (light)", "legs", "compound",
                          ("dumbbells",), 2, 10, "Each leg"),
    "incline_walk_legs": Exercise("incline_walk_legs", "Incline Treadmill Walk", "legs", "cardio",
                                  ("treadmill",), 1, 0,
                                  "20 min @ 3.0-3.5 mph, 10-12% incline. Doubles as cardio."),
    "calf_raise": Exercise("calf_raise", "Calf Raise", "legs", "isolation",
                           ("dumbbells",), 2, 15),

    # ---------- CORE ----------
    "plank": Exercise("plank", "Plank", "core", "isolation",
                      ("bodyweight",), 3, 0, "30-60 sec hold"),
    "hanging_knee_raise": Exercise("hanging_knee_raise", "Hanging Knee Raise", "core", "isolation",
                                   ("bar",), 3, 12),
    "cable_crunch": Exercise("cable_crunch", "Cable Crunch", "core", "isolation",
                             ("cable",), 3, 15),
    "russian_twist": Exercise("russian_twist", "Russian Twist", "core", "isolation",
                              ("dumbbells",), 3, 20, "10 each side"),
    "ab_wheel": Exercise("ab_wheel", "Ab Wheel Rollout", "core", "compound",
                         ("ab_wheel",), 3, 10),

    # ---------- CARDIO ----------
    "incline_walk": Exercise("incline_walk", "Incline Treadmill Walk", "cardio", "cardio",
                             ("treadmill",), 1, 0,
                             "Best fat-loss cardio. 15-25 min, 3.0-3.5 mph, 10-12% incline."),
    "bike_steady": Exercise("bike_steady", "Bike (steady state)", "cardio", "cardio",
                            ("bike",), 1, 0, "20-25 min at conversational pace"),
    "bike_intervals": Exercise("bike_intervals", "Bike Intervals", "cardio", "cardio",
                               ("bike",), 1, 0,
                               "30s hard / 90s easy x 8-10 rounds"),
    "treadmill_intervals": Exercise("treadmill_intervals", "Treadmill Intervals", "cardio", "cardio",
                                    ("treadmill",), 1, 0,
                                    "1 min run / 2 min walk x 6-8"),
}


def by_muscle_group(group: str) -> list[Exercise]:
    return [e for e in CATALOG.values() if e.muscle_group == group]


def by_slug(slug: str) -> Exercise:
    return CATALOG[slug]


def all_compounds_for(group: str) -> list[Exercise]:
    return [e for e in CATALOG.values() if e.muscle_group == group and e.category == "compound"]


def all_isolations_for(group: str) -> list[Exercise]:
    return [e for e in CATALOG.values() if e.muscle_group == group and e.category == "isolation"]
