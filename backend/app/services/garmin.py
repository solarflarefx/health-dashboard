"""
Garmin data-fetching service.

All functions are async (they run the blocking garminconnect calls in a
thread pool via asyncio.to_thread) and auto-retry once on authentication
errors before propagating the exception.

Thread safety
-------------
The Garmin client is a process-wide singleton backed by a requests.Session,
which is not thread-safe.  Every client method call runs under _client_lock
via _locked_client_call(), so concurrent asyncio.gather/to_thread tasks
cannot corrupt session state.

Concurrency style
-----------------
fetch_heart_health_metrics and fetch_movement_metrics keep asyncio.gather
for readability even though the lock serializes the underlying HTTP calls —
there is no throughput gain from gather once the lock is in place.

_fetch_stats_history uses gather for the same reason: equivalent throughput
to a sequential loop, but expresses the independent per-day fetches clearly.
"""

import asyncio
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, TypeVar

from garminconnect import GarminConnectAuthenticationError

from app.garmin_client import get_garmin_client, refresh_garmin_client
from app.models.metrics import (
    HeartHealthMetrics,
    HistoryDataPoint,
    MovementMetrics,
    TodayMetrics,
    VO2MaxPoint,
    VO2MaxTrend,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Serializes all blocking Garmin HTTP calls — the client singleton uses
# requests.Session, which must not be accessed concurrently from multiple threads.
_client_lock = threading.Lock()


def _locked_client_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    with _client_lock:
        return fn(*args, **kwargs)


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

    stats: dict = await asyncio.to_thread(_locked_client_call, client.get_stats, today_str)

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

    # gather kept for readability; _client_lock serializes the actual HTTP calls.
    hr_data, stats = await asyncio.gather(
        asyncio.to_thread(_locked_client_call, client.get_heart_rates, today_str),
        asyncio.to_thread(_locked_client_call, client.get_stats, today_str),
    )

    resting_hr: int = int(hr_data.get("restingHeartRate") or 0)
    min_hr: int = int(hr_data.get("minHeartRate") or 0)
    max_hr: int = int(hr_data.get("maxHeartRate") or 0)

    # get_stress_data() returns None for averageStressLevel during the day.
    # get_stats() provides averageStressLevel/maxStressLevel reliably instead.
    avg_stress = stats.get("averageStressLevel")
    max_stress = stats.get("maxStressLevel")
    raw_stress = avg_stress if avg_stress is not None else max_stress
    stress_score: int = max(0, int(raw_stress or 0))

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
    # Rolling 7-day window so activities are always included regardless of
    # where we are in the calendar week.
    window_start = today - timedelta(days=7)
    today_str = today.isoformat()
    window_start_str = window_start.isoformat()

    client = get_garmin_client()

    # gather kept for readability; _client_lock serializes the actual HTTP calls.
    activities, stats = await asyncio.gather(
        asyncio.to_thread(
            _locked_client_call, client.get_activities_by_date, window_start_str, today_str
        ),
        asyncio.to_thread(_locked_client_call, client.get_stats, today_str),
    )

    # If today's stats are all None (Garmin hasn't synced yet), use yesterday.
    if not any(stats.get(k) for k in ("totalSteps", "activeKilocalories", "moderateIntensityMinutes")):
        yesterday_str = (today - timedelta(days=1)).isoformat()
        stats = await asyncio.to_thread(_locked_client_call, client.get_stats, yesterday_str)

    weekly_activities: int = len(activities)

    # Intensity minutes come from the daily stats summary.
    moderate_min: int = int(stats.get("moderateIntensityMinutes") or 0)
    vigorous_min: int = int(stats.get("vigorousIntensityMinutes") or 0)
    # Garmin counts vigorous minutes double toward the weekly goal.
    intensity_minutes: int = moderate_min + vigorous_min * 2
    intensity_goal: int = 150

    # Sum distance (metres → km) and elevation across the rolling window's activities.
    total_distance_m: float = sum(float(a.get("distance") or 0) for a in activities)
    total_elevation_m: float = sum(float(a.get("elevationGain") or 0) for a in activities)

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
    client = get_garmin_client()

    # get_max_metrics() takes a single date string and returns a list.
    # A non-empty list has the VO2Max value at entry[0]['generic']['vo2MaxPreciseValue'].
    # Empty lists and None mean no data for that week — skip entirely; do not add a point.
    history: list[VO2MaxPoint] = []
    for week_offset in range(12):
        fetch_date = (today - timedelta(weeks=11 - week_offset)).isoformat()
        entry = await asyncio.to_thread(_locked_client_call, client.get_max_metrics, fetch_date)
        if not entry:
            continue
        try:
            value = float(entry[0]["generic"]["vo2MaxPreciseValue"])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        history.append(VO2MaxPoint(week=f"W{len(history) + 1}", value=round(value, 1)))

    current: float = history[-1].value if history else 0.0
    change_this_month: float = round(current - history[0].value, 1) if len(history) >= 2 else 0.0

    return VO2MaxTrend(
        current=current,
        change_this_month=change_this_month,
        history=history,
    )


# ─── Daily History ────────────────────────────────────────────────────────────


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


async def _fetch_stats_history(days: int) -> list[tuple[date, dict]]:
    """Fetch get_stats() for each of the last *days* days (oldest first)."""
    if days > 30:
        logger.warning(
            "Fetching %d days of history requires %d Garmin API calls",
            days,
            days,
        )
    today = _utc_today()
    dates = [today - timedelta(days=days - 1 - i) for i in range(days)]
    client = get_garmin_client()
    # gather kept for readability; _client_lock serializes the actual HTTP calls.
    stats_list = await asyncio.gather(
        *[
            asyncio.to_thread(_locked_client_call, client.get_stats, d.isoformat())
            for d in dates
        ]
    )
    return list(zip(dates, stats_list, strict=True))


@_with_auth_retry
async def get_steps_history(days: int) -> list[HistoryDataPoint]:
    history: list[HistoryDataPoint] = []
    for day, stats in await _fetch_stats_history(days):
        raw = stats.get("totalSteps")
        if raw is None:
            continue
        history.append(HistoryDataPoint(date=day, value=float(raw)))
    return history


@_with_auth_retry
async def get_resting_hr_history(days: int) -> list[HistoryDataPoint]:
    history: list[HistoryDataPoint] = []
    for day, stats in await _fetch_stats_history(days):
        raw = stats.get("restingHeartRate")
        if raw is None:
            continue
        history.append(HistoryDataPoint(date=day, value=float(raw)))
    return history


@_with_auth_retry
async def get_stress_history(days: int) -> list[HistoryDataPoint]:
    history: list[HistoryDataPoint] = []
    for day, stats in await _fetch_stats_history(days):
        avg_stress = stats.get("averageStressLevel")
        max_stress = stats.get("maxStressLevel")
        raw = avg_stress if avg_stress is not None else max_stress
        if raw is None:
            continue
        history.append(HistoryDataPoint(date=day, value=float(raw)))
    return history
