"""Unit tests for daily metric history service functions."""
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.services.garmin import (
    _fetch_stats_history,
    get_resting_hr_history,
    get_steps_history,
    get_stress_history,
)

FIXED_TODAY = date(2026, 6, 22)


def _dates(days: int, anchor: date = FIXED_TODAY) -> list[date]:
    return [anchor - timedelta(days=days - 1 - i) for i in range(days)]


def _stats_by_date(stats_map: dict[date, dict]) -> AsyncMock:
    async def fetch_stats_history(days: int) -> list[tuple[date, dict]]:
        return [(d, stats_map[d]) for d in _dates(days)]

    return AsyncMock(side_effect=fetch_stats_history)


class TestFetchStatsHistory:
    @pytest.mark.asyncio
    async def test_builds_utc_date_window_oldest_first(self) -> None:
        expected_dates = _dates(3)
        mock_client = MagicMock()
        mock_client.get_stats.return_value = {}
        with (
            patch("app.services.garmin._utc_today", return_value=FIXED_TODAY),
            patch("app.services.garmin.get_garmin_client", return_value=mock_client),
            patch(
                "app.services.garmin._locked_client_call",
                side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs),
            ),
        ):
            result = await _fetch_stats_history(3)

        assert [d for d, _ in result] == expected_dates
        mock_client.get_stats.assert_has_calls(
            [call(d.isoformat()) for d in expected_dates],
            any_order=False,
        )


class TestStepsHistory:
    @pytest.mark.asyncio
    async def test_skips_days_with_none_values(self) -> None:
        dates = _dates(3)
        stats_map = {
            dates[0]: {"totalSteps": 5000},
            dates[1]: {"totalSteps": None},
            dates[2]: {"totalSteps": 7000},
        }
        with patch("app.services.garmin._fetch_stats_history", new=_stats_by_date(stats_map)):
            history = await get_steps_history(3)

        assert len(history) == 2
        assert history[0].date == dates[0]
        assert history[0].value == 5000.0
        assert history[1].date == dates[2]
        assert history[1].value == 7000.0
        assert dates[1] not in [p.date for p in history]

    @pytest.mark.asyncio
    async def test_includes_zero_steps(self) -> None:
        dates = _dates(1)
        stats_map = {dates[0]: {"totalSteps": 0}}
        with patch("app.services.garmin._fetch_stats_history", new=_stats_by_date(stats_map)):
            history = await get_steps_history(1)

        assert len(history) == 1
        assert history[0].date == dates[0]
        assert history[0].value == 0.0


class TestRestingHrHistory:
    @pytest.mark.asyncio
    async def test_skips_days_with_none_values(self) -> None:
        dates = _dates(2)
        stats_map = {
            dates[0]: {"restingHeartRate": None},
            dates[1]: {"restingHeartRate": 58},
        }
        with patch("app.services.garmin._fetch_stats_history", new=_stats_by_date(stats_map)):
            history = await get_resting_hr_history(2)

        assert len(history) == 1
        assert history[0].date == dates[1]
        assert history[0].value == 58.0


class TestStressHistory:
    @pytest.mark.asyncio
    async def test_prefers_average_over_max(self) -> None:
        dates = _dates(1)
        stats_map = {
            dates[0]: {"averageStressLevel": 30, "maxStressLevel": 80},
        }
        with patch("app.services.garmin._fetch_stats_history", new=_stats_by_date(stats_map)):
            history = await get_stress_history(1)

        assert len(history) == 1
        assert history[0].date == dates[0]
        assert history[0].value == 30.0

    @pytest.mark.asyncio
    async def test_falls_back_to_max_when_average_is_none(self) -> None:
        dates = _dates(1)
        stats_map = {
            dates[0]: {"averageStressLevel": None, "maxStressLevel": 45},
        }
        with patch("app.services.garmin._fetch_stats_history", new=_stats_by_date(stats_map)):
            history = await get_stress_history(1)

        assert len(history) == 1
        assert history[0].date == dates[0]
        assert history[0].value == 45.0

    @pytest.mark.asyncio
    async def test_skips_days_with_both_stress_values_none(self) -> None:
        dates = _dates(2)
        stats_map = {
            dates[0]: {"averageStressLevel": None, "maxStressLevel": None},
            dates[1]: {"averageStressLevel": None, "maxStressLevel": None},
        }
        with patch("app.services.garmin._fetch_stats_history", new=_stats_by_date(stats_map)):
            history = await get_stress_history(2)

        assert history == []
