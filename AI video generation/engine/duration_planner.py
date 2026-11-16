"""Target-duration presets and scene allocation for long-form local videos.

This module plans a complete timeline from short scene clips. It does not claim
that the current single-clip generation endpoint can render those timelines yet.
"""
from __future__ import annotations

from dataclasses import dataclass

DURATION_PRESETS: dict[str, int] = {
    "15 seconds": 15,
    "30 seconds": 30,
    "45 seconds": 45,
    "60 seconds": 60,
    "90 seconds": 90,
    "2 minutes": 120,
    "5 minutes": 300,
}
MIN_CUSTOM_SECONDS = 5
MAX_CUSTOM_SECONDS = 1800
DEFAULT_SCENE_SECONDS = 4
MIN_SCENE_SECONDS = 2


@dataclass(frozen=True)
class SceneSlot:
    index: int
    duration_seconds: int
    start_seconds: int


def resolve_duration(preset: str = "60 seconds", custom_seconds: int | float | None = None) -> int:
    """Resolve a named preset or validate a custom whole-second target."""
    if preset == "Custom":
        if custom_seconds is None or isinstance(custom_seconds, bool):
            raise ValueError("Enter a custom duration in seconds.")
        try:
            value = float(custom_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("Custom duration must be a number of seconds.") from exc
        if not value.is_integer():
            raise ValueError("Custom duration must be a whole number of seconds.")
        seconds = int(value)
        if not MIN_CUSTOM_SECONDS <= seconds <= MAX_CUSTOM_SECONDS:
            raise ValueError(
                f"Custom duration must be between {MIN_CUSTOM_SECONDS} and {MAX_CUSTOM_SECONDS} seconds."
            )
        return seconds
    try:
        return DURATION_PRESETS[preset]
    except KeyError as exc:
        raise ValueError(f"Unknown duration preset: {preset!r}.") from exc


def plan_scene_slots(
    total_seconds: int,
    *,
    max_scene_seconds: int = DEFAULT_SCENE_SECONDS,
    min_scene_seconds: int = MIN_SCENE_SECONDS,
) -> list[SceneSlot]:
    """Split a target duration into contiguous short scene slots.

    Every slot is within the configured min/max bounds and the sum exactly
    equals the requested target. The planner balances the final remainder
    rather than creating a tiny trailing scene.
    """
    if isinstance(total_seconds, bool) or not isinstance(total_seconds, int):
        raise ValueError("Total duration must be a whole number of seconds.")
    if isinstance(max_scene_seconds, bool) or isinstance(min_scene_seconds, bool):
        raise ValueError("Scene duration limits must be whole numbers.")
    if not isinstance(max_scene_seconds, int) or not isinstance(min_scene_seconds, int):
        raise ValueError("Scene duration limits must be whole numbers.")
    if min_scene_seconds < 1 or max_scene_seconds < min_scene_seconds:
        raise ValueError("Scene duration limits are invalid.")
    if total_seconds < min_scene_seconds:
        raise ValueError(f"Total duration must be at least {min_scene_seconds} seconds.")

    count = (total_seconds + max_scene_seconds - 1) // max_scene_seconds
    if total_seconds < count * min_scene_seconds:
        raise ValueError("Target duration cannot be divided into valid scene lengths.")

    base, extra = divmod(total_seconds, count)
    durations = [base + (1 if i < extra else 0) for i in range(count)]
    if any(d < min_scene_seconds or d > max_scene_seconds for d in durations):
        raise ValueError("Scene planner produced a duration outside the configured bounds.")

    slots: list[SceneSlot] = []
    cursor = 0
    for index, seconds in enumerate(durations, start=1):
        slots.append(SceneSlot(index=index, duration_seconds=seconds, start_seconds=cursor))
        cursor += seconds
    return slots
