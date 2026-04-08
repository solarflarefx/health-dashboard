"""
Garmin data-fetching service.

All functions are async (they run the blocking garminconnect calls in a
thread pool via asyncio.to_thread) and auto-retry once on authentication
errors before propagating the exception.
"""

import asyncio
import logging
from datetime import date, timedelta
from functools import wraps
from typing import Any, Callable, TypeVar

from garminconnect import GarminConnectAuthenticationError

from app.garmin_client import get_garmin_client, refresh_garmin_client
from app.models.metrics import (
    HeartHealthMetrics,
    MovementMetrics,
    TodayMetrics,
    VO2MaxPoint,
    VO2MaxTrend,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _with_auth_retry(fn: F) -> F:
    """Decorator: on GarminConnectAuthenticationError, refresh the client and retry once."""

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except GarminConnectAuthenticationError:
            logger.warning("Auth error in %s — refreshing session and retrying", fn.__name__)
            refresh_garmin_client()
            return await fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


# ─── Today ───────────────────────────────────────────────────────────────────


@_with_auth_retry
async def fetch_today_metrics() -> TodayMetrics:
    today_str = date.today().isoformat()
    client = get_garmin_client()

    stats: dict = await asyncio.to_thread(client.get_stats, today_str)

    steps: int = int(stats.get("totalSteps") or 0)
    steps_goal: int = int(stats.get("dailyStepGoal") or 10_000)
    active_calories: int = int(stats.get("activeKilocalories") or 0)

    # Garmin reports high + moderate intensity in seconds; sum → minutes.
    highly_active_s: int = int(stats.get("highlyActiveSeconds") or 0)
    moderately_active_s: int = int(stats.get("moderateIntensityMinutes") or 0) * 60
    activity_time_min: int = (highly_active_s + moderately_active_s) // 60

    return TodayMetrics(
        steps=steps,
        steps_goal=steps_goal,
        active_calories=active_calories,
        activity_time=activity_time_min,
    )


# ─── Heart Health ─────────────────────────────────────────────────────────────


@_with_auth_retry
async def fetch_heart_health_metrics() -> HeartHealthMetrics:
    today_str = date.today().isoformat()
    client = get_garmin_client()

    hr_data: dict = await asyncio.to_thread(client.get_heart_rates, today_str)
    stress_data: dict = await asyncio.to_thread(client.get_stress_data, today_str)

    resting_hr: int = int(hr_data.get("restingHeartRate") or 0)
    min_hr: int = int(hr_data.get("minHeartRate") or 0)
    max_hr: int = int(hr_data.get("maxHeartRate") or 0)

    # Garmin returns an "overallStressLevel" (-1 when not enough data).
    raw_stress = stress_data.get("overallStressLevel", -1)
    stress_score: int = max(0, int(raw_stress))

    return HeartHealthMetrics(
        resting_hr=resting_hr,
        min_hr=min_hr,
        max_hr=max_hr,
        stress_score=stress_score,
    )


# ─── Movement ────────────────────────────────────────────────────────────────


@_with_auth_retry
async def fetch_movement_metrics() -> MovementMetrics:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday of current week
    week_start_str = week_start.isoformat()
    today_str = today.isoformat()

    client = get_garmin_client()

    activities, stats = await asyncio.gather(
        asyncio.to_thread(client.get_activities_by_date, week_start_str, today_str),
        asyncio.to_thread(client.get_stats, today_str),
    )

    weekly_activities: int = len(activities)

    # Intensity minutes come from the daily stats summary.
    moderate_min: int = int(stats.get("moderateIntensityMinutes") or 0)
    vigorous_min: int = int(stats.get("vigorousIntensityMinutes") or 0)
    # Garmin counts vigorous minutes double toward the weekly goal.
    intensity_minutes: int = moderate_min + vigorous_min * 2
    intensity_goal: int = 150

    # Sum distance (metres → km) and elevation across this week's activities.
    total_distance_m: float = sum(
        float(a.get("distance") or 0) for a in activities
    )
    total_elevation_m: float = sum(
        float(a.get("elevationGain") or 0) for a in activities
    )

    return MovementMetrics(
        weekly_activities=weekly_activities,
        intensity_minutes=intensity_minutes,
        intensity_goal=intensity_goal,
        distance=round(total_distance_m / 1000, 1),
        elevation=round(total_elevation_m, 0),
    )


# ─── VO₂ Max Trend ───────────────────────────────────────────────────────────


@_with_auth_retry
async def fetch_vo2max_trend() -> VO2MaxTrend:
    today = date.today()
    # Go back 12 weeks from the most recent Monday.
    week_start = today - timedelta(days=today.weekday())
    start_date = week_start - timedelta(weeks=11)

    client = get_garmin_client()

    # get_max_metrics returns a list of dicts with 'generic' and 'running' VO2 values.
    raw: list[dict] = await asyncio.to_thread(
        client.get_max_metrics,
        start_date.isoformat(),
        today.isoformat(),
    )

    # Build a map of week_start_date → latest VO2Max value seen that week.
    weekly: dict[date, float] = {}
    for entry in raw:
        entry_date_str: str | None = entry.get("calendarDate") or entry.get("startTimestampLocal")
        if not entry_date_str:
            continue
        try:
            entry_date = date.fromisoformat(entry_date_str[:10])
        except ValueError:
            continue

        # Prefer the 'generic' VO2Max value; fall back to 'running'.
        value: float | None = (
            entry.get("generic", {}) or {}
        ).get("vo2MaxPreciseValue") or (
            entry.get("running", {}) or {}
        ).get("vo2MaxPreciseValue")
        if value is None:
            continue

        bucket = entry_date - timedelta(days=entry_date.weekday())
        weekly[bucket] = float(value)

    # Build exactly 12 ordered weekly points (None → carry forward last known value).
    history: list[VO2MaxPoint] = []
    last_value: float | None = None
    for i in range(12):
        bucket = start_date + timedelta(weeks=i)
        v = weekly.get(bucket, last_value)
        if v is not None:
            last_value = v
            history.append(VO2MaxPoint(week=f"W{i + 1}", value=round(v, 1)))

    current: float = history[-1].value if history else 0.0
    month_ago_value: float = history[-4].value if len(history) >= 4 else current
    change_this_month: float = round(current - month_ago_value, 1)

    return VO2MaxTrend(
        current=current,
        change_this_month=change_this_month,
        history=history,
    )
