"""Unit tests for Pydantic response models."""
import pytest
from pydantic import ValidationError

from app.models.metrics import (
    HeartHealthMetrics,
    MovementMetrics,
    TodayMetrics,
    VO2MaxPoint,
    VO2MaxTrend,
)


class TestTodayMetrics:
    def test_valid_data(self) -> None:
        m = TodayMetrics(steps=5000, steps_goal=10000, active_calories=300, activity_time=45)
        assert m.steps == 5000
        assert m.steps_goal == 10000
        assert m.active_calories == 300
        assert m.activity_time == 45

    def test_zero_steps(self) -> None:
        """Steps can be zero at the start of the day."""
        m = TodayMetrics(steps=0, steps_goal=10000, active_calories=0, activity_time=0)
        assert m.steps == 0
        assert m.active_calories == 0
        assert m.activity_time == 0

    def test_very_active_day(self) -> None:
        m = TodayMetrics(steps=25000, steps_goal=10000, active_calories=1200, activity_time=180)
        assert m.steps == 25000

    def test_missing_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            TodayMetrics(steps=1000, steps_goal=10000, active_calories=200)  # type: ignore[call-arg]

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            TodayMetrics(
                steps="not-a-number",  # type: ignore[arg-type]
                steps_goal=10000,
                active_calories=200,
                activity_time=30,
            )

    def test_none_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            TodayMetrics(steps=None, steps_goal=10000, active_calories=200, activity_time=30)  # type: ignore[arg-type]


class TestHeartHealthMetrics:
    def test_valid_data(self) -> None:
        m = HeartHealthMetrics(resting_hr=60, min_hr=45, max_hr=155, stress_score=40)
        assert m.resting_hr == 60
        assert m.min_hr == 45
        assert m.max_hr == 155
        assert m.stress_score == 40

    def test_zero_stress_score(self) -> None:
        """Stress of 0 is valid (very relaxed day)."""
        m = HeartHealthMetrics(resting_hr=55, min_hr=42, max_hr=130, stress_score=0)
        assert m.stress_score == 0

    def test_max_stress_score(self) -> None:
        m = HeartHealthMetrics(resting_hr=80, min_hr=60, max_hr=190, stress_score=100)
        assert m.stress_score == 100

    def test_high_max_hr(self) -> None:
        """Typical max HR near 200 bpm during intense exercise."""
        m = HeartHealthMetrics(resting_hr=62, min_hr=50, max_hr=198, stress_score=55)
        assert m.max_hr == 198

    def test_missing_stress_score_raises(self) -> None:
        with pytest.raises(ValidationError):
            HeartHealthMetrics(resting_hr=60, min_hr=45, max_hr=155)  # type: ignore[call-arg]

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            HeartHealthMetrics(
                resting_hr="high",  # type: ignore[arg-type]
                min_hr=45,
                max_hr=155,
                stress_score=40,
            )


class TestMovementMetrics:
    def test_valid_data(self) -> None:
        m = MovementMetrics(
            weekly_activities=3,
            intensity_minutes=90,
            intensity_goal=150,
            distance=25.5,
            elevation=200.0,
        )
        assert m.weekly_activities == 3
        assert m.distance == 25.5
        assert m.elevation == 200.0

    def test_zero_activities(self) -> None:
        """No activities this week is a valid state."""
        m = MovementMetrics(
            weekly_activities=0,
            intensity_minutes=0,
            intensity_goal=150,
            distance=0.0,
            elevation=0.0,
        )
        assert m.weekly_activities == 0
        assert m.distance == 0.0

    def test_flat_terrain(self) -> None:
        """Zero elevation is valid for flat routes."""
        m = MovementMetrics(
            weekly_activities=2,
            intensity_minutes=60,
            intensity_goal=150,
            distance=10.0,
            elevation=0.0,
        )
        assert m.elevation == 0.0

    def test_intensity_exceeds_goal(self) -> None:
        """Intensity minutes can exceed the weekly goal."""
        m = MovementMetrics(
            weekly_activities=7,
            intensity_minutes=300,
            intensity_goal=150,
            distance=80.0,
            elevation=1200.0,
        )
        assert m.intensity_minutes > m.intensity_goal

    def test_missing_distance_raises(self) -> None:
        with pytest.raises(ValidationError):
            MovementMetrics(  # type: ignore[call-arg]
                weekly_activities=3,
                intensity_minutes=90,
                intensity_goal=150,
                elevation=0.0,
            )

    def test_wrong_distance_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            MovementMetrics(
                weekly_activities=3,
                intensity_minutes=90,
                intensity_goal=150,
                distance="far",  # type: ignore[arg-type]
                elevation=0.0,
            )


class TestVO2MaxPoint:
    def test_valid_data(self) -> None:
        p = VO2MaxPoint(week="W1", value=48.5)
        assert p.week == "W1"
        assert p.value == 48.5

    def test_week_label_formats(self) -> None:
        for i in range(1, 13):
            p = VO2MaxPoint(week=f"W{i}", value=45.0)
            assert p.week == f"W{i}"

    def test_missing_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            VO2MaxPoint(week="W1")  # type: ignore[call-arg]

    def test_missing_week_raises(self) -> None:
        with pytest.raises(ValidationError):
            VO2MaxPoint(value=48.5)  # type: ignore[call-arg]

    def test_non_numeric_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            VO2MaxPoint(week="W1", value="excellent")  # type: ignore[arg-type]


class TestVO2MaxTrend:
    def test_valid_data_with_full_history(self) -> None:
        history = [VO2MaxPoint(week=f"W{i + 1}", value=round(46.0 + i * 0.2, 1)) for i in range(12)]
        t = VO2MaxTrend(current=48.2, change_this_month=0.8, history=history)
        assert t.current == 48.2
        assert len(t.history) == 12

    def test_empty_history(self) -> None:
        """No history data yet (e.g. new user) is a valid state."""
        t = VO2MaxTrend(current=0.0, change_this_month=0.0, history=[])
        assert t.history == []
        assert t.current == 0.0

    def test_negative_monthly_change(self) -> None:
        """VO2max can decrease — negative change is valid."""
        history = [VO2MaxPoint(week="W1", value=50.0), VO2MaxPoint(week="W2", value=49.0)]
        t = VO2MaxTrend(current=49.0, change_this_month=-1.0, history=history)
        assert t.change_this_month == -1.0

    def test_positive_monthly_change(self) -> None:
        history = [VO2MaxPoint(week="W1", value=47.0), VO2MaxPoint(week="W2", value=48.0)]
        t = VO2MaxTrend(current=48.0, change_this_month=1.0, history=history)
        assert t.change_this_month == 1.0

    def test_missing_history_raises(self) -> None:
        with pytest.raises(ValidationError):
            VO2MaxTrend(current=48.0, change_this_month=0.5)  # type: ignore[call-arg]

    def test_invalid_history_item_raises(self) -> None:
        """A history point missing its value should fail validation."""
        with pytest.raises(ValidationError):
            VO2MaxTrend(
                current=48.0,
                change_this_month=0.5,
                history=[{"week": "W1"}],  # missing value
            )

    def test_history_point_wrong_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            VO2MaxTrend(
                current=48.0,
                change_this_month=0.5,
                history="not-a-list",  # type: ignore[arg-type]
            )
