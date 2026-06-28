"""Unit tests for daily metric history service functions."""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.garmin import (
    get_resting_hr_history,
    get_steps_history,
    get_stress_history,
)


def _date_strs(days: int) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]


@pytest.fixture
def mock_garmin_client():
    """Patch get_garmin_client with a MagicMock whose get_stats is sync (via to_thread)."""
    client = MagicMock()
    with patch("app.services.garmin.get_garmin_client", return_value=client):
        yield client


class TestStepsHistory:
    @pytest.mark.asyncio
    async def test_skips_days_with_none_values(self, mock_garmin_client: MagicMock) -> None:
        dates = _date_strs(3)
        mock_garmin_client.get_stats.side_effect = [
            {"totalSteps": 5000},
            {"totalSteps": None},
            {"totalSteps": 7000},
        ]

        history = await get_steps_history(3)

        assert len(history) == 2
        assert history[0].date == dates[0]
        assert history[0].value == 5000.0
        assert history[1].date == dates[2]
        assert history[1].value == 7000.0
        assert dates[1] not in [p.date for p in history]

    @pytest.mark.asyncio
    async def test_includes_zero_steps(self, mock_garmin_client: MagicMock) -> None:
        dates = _date_strs(1)
        mock_garmin_client.get_stats.return_value = {"totalSteps": 0}

        history = await get_steps_history(1)

        assert len(history) == 1
        assert history[0].date == dates[0]
        assert history[0].value == 0.0


class TestRestingHrHistory:
    @pytest.mark.asyncio
    async def test_skips_days_with_none_values(self, mock_garmin_client: MagicMock) -> None:
        dates = _date_strs(2)
        mock_garmin_client.get_stats.side_effect = [
            {"restingHeartRate": None},
            {"restingHeartRate": 58},
        ]

        history = await get_resting_hr_history(2)

        assert len(history) == 1
        assert history[0].date == dates[1]
        assert history[0].value == 58.0


class TestStressHistory:
    @pytest.mark.asyncio
    async def test_prefers_average_over_max(self, mock_garmin_client: MagicMock) -> None:
        dates = _date_strs(1)
        mock_garmin_client.get_stats.return_value = {
            "averageStressLevel": 30,
            "maxStressLevel": 80,
        }

        history = await get_stress_history(1)

        assert len(history) == 1
        assert history[0].date == dates[0]
        assert history[0].value == 30.0

    @pytest.mark.asyncio
    async def test_falls_back_to_max_when_average_is_none(self, mock_garmin_client: MagicMock) -> None:
        dates = _date_strs(1)
        mock_garmin_client.get_stats.return_value = {
            "averageStressLevel": None,
            "maxStressLevel": 45,
        }

        history = await get_stress_history(1)

        assert len(history) == 1
        assert history[0].date == dates[0]
        assert history[0].value == 45.0

    @pytest.mark.asyncio
    async def test_skips_days_with_both_stress_values_none(self, mock_garmin_client: MagicMock) -> None:
        mock_garmin_client.get_stats.return_value = {
            "averageStressLevel": None,
            "maxStressLevel": None,
        }

        history = await get_stress_history(2)

        assert history == []
