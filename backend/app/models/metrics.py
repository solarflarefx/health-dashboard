"""Pydantic response models — mirrors the TypeScript types in types/dashboard.ts."""

from pydantic import BaseModel


class TodayMetrics(BaseModel):
    steps: int
    steps_goal: int
    active_calories: int
    activity_time: int  # minutes


class HeartHealthMetrics(BaseModel):
    resting_hr: int
    min_hr: int
    max_hr: int
    stress_score: int  # 0–100


class MovementMetrics(BaseModel):
    weekly_activities: int
    intensity_minutes: int
    intensity_goal: int
    distance: float  # km
    elevation: float  # metres


class VO2MaxPoint(BaseModel):
    week: str   # e.g. "W1"
    value: float


class VO2MaxTrend(BaseModel):
    current: float
    change_this_month: float
    history: list[VO2MaxPoint]


class HistoryDataPoint(BaseModel):
    date: str  # YYYY-MM-DD
    value: float | None


class MetricHistory(BaseModel):
    metric: str
    days: int
    history: list[HistoryDataPoint]
