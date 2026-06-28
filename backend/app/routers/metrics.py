from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.garmin_client import is_auth_ready
from app.models.metrics import (
    HeartHealthMetrics,
    MetricHistory,
    MovementMetrics,
    TodayMetrics,
    VO2MaxTrend,
)
from app.services.garmin import (
    fetch_heart_health_metrics,
    fetch_movement_metrics,
    fetch_today_metrics,
    fetch_vo2max_trend,
    get_resting_hr_history,
    get_steps_history,
    get_stress_history,
)

_HISTORY_FETCHERS = {
    "steps": get_steps_history,
    "resting-hr": get_resting_hr_history,
    "stress": get_stress_history,
}


def require_garmin_auth() -> None:
    """FastAPI dependency — raises 503 if the Garmin session is not yet established."""
    if not is_auth_ready():
        raise HTTPException(
            status_code=503,
            detail="Garmin authentication pending — please try again shortly",
        )


router = APIRouter(
    prefix="/api/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_garmin_auth)],
)


@router.get("/today", response_model=TodayMetrics)
async def get_today_metrics() -> TodayMetrics:
    try:
        return await fetch_today_metrics()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/heart", response_model=HeartHealthMetrics)
async def get_heart_health_metrics() -> HeartHealthMetrics:
    try:
        return await fetch_heart_health_metrics()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/movement", response_model=MovementMetrics)
async def get_movement_metrics() -> MovementMetrics:
    try:
        return await fetch_movement_metrics()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/vo2max", response_model=VO2MaxTrend)
async def get_vo2max_trend() -> VO2MaxTrend:
    try:
        return await fetch_vo2max_trend()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/history/{metric_name}", response_model=MetricHistory)
async def get_metric_history(
    metric_name: str,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> MetricHistory:
    fetcher = _HISTORY_FETCHERS.get(metric_name)
    if fetcher is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric '{metric_name}' — expected one of: steps, resting-hr, stress",
        )
    try:
        history = await fetcher(days)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return MetricHistory(metric=metric_name, days=days, history=history)
