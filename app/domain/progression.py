"""
Progressive overload suggester.

Rule of thumb (linear-ish, intermediate lifter, dumbbell-friendly):
- Last session at target reps with rating 4-5 → +5 lb (or +2.5 if available)
- Last session at target reps with rating 3 → repeat weight
- Last session under target reps OR rating 1-2 → repeat weight, focus on reps
- No history → conservative starting point
"""
from __future__ import annotations
from typing import Optional


def suggest_weight(
    last_weight: Optional[float],
    last_reps: Optional[int],
    target_reps: int,
    last_rating: Optional[int],
) -> Optional[float]:
    """
    Given last session's performance, suggest next session's weight.
    Returns lb (your unit), rounded to nearest 5 (dumbbell increments).
    """
    if last_weight is None or last_reps is None:
        return None  # no history → leave to user / "feel it out"

    # Hit reps and felt good → progress
    if last_reps >= target_reps and (last_rating is None or last_rating >= 4):
        return _round_to_dumbbell(last_weight + 5)

    # Hit reps but felt hard
    if last_reps >= target_reps and last_rating == 3:
        return _round_to_dumbbell(last_weight)

    # Missed reps or felt bad → repeat
    return _round_to_dumbbell(last_weight)


def _round_to_dumbbell(weight: float) -> float:
    """Most basic gyms have 5 lb dumbbell jumps."""
    return round(weight / 5) * 5
