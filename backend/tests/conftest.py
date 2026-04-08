"""Shared pytest fixtures for the FastAPI backend test suite."""
import os

# Must be set before any app imports so Settings() succeeds at module level.
os.environ.setdefault("GARMIN_EMAIL", "test@example.com")
os.environ.setdefault("GARMIN_PASSWORD", "testpassword")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.garmin_client as garmin_client_module
from app.main import app
from app.models.metrics import (
    HeartHealthMetrics,
    MovementMetrics,
    TodayMetrics,
    VO2MaxPoint,
    VO2MaxTrend,
)

# ─── Realistic mock data ──────────────────────────────────────────────────────

MOCK_TODAY = TodayMetrics(
    steps=8_543,
    steps_goal=10_000,
    active_calories=412,
    activity_time=47,
)

MOCK_HEART = HeartHealthMetrics(
    resting_hr=58,
    min_hr=48,
    max_hr=142,
    stress_score=32,
)

MOCK_MOVEMENT = MovementMetrics(
    weekly_activities=4,
    intensity_minutes=135,
    intensity_goal=150,
    distance=38.2,
    elevation=320.0,
)

MOCK_VO2MAX = VO2MaxTrend(
    current=48.5,
    change_this_month=0.5,
    history=[VO2MaxPoint(week=f"W{i + 1}", value=round(47.5 + i * 0.1, 1)) for i in range(12)],
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_services():
    """Patch all Garmin service functions with AsyncMocks returning realistic data."""
    with (
        patch(
            "app.routers.metrics.fetch_today_metrics",
            new=AsyncMock(return_value=MOCK_TODAY),
        ),
        patch(
            "app.routers.metrics.fetch_heart_health_metrics",
            new=AsyncMock(return_value=MOCK_HEART),
        ),
        patch(
            "app.routers.metrics.fetch_movement_metrics",
            new=AsyncMock(return_value=MOCK_MOVEMENT),
        ),
        patch(
            "app.routers.metrics.fetch_vo2max_trend",
            new=AsyncMock(return_value=MOCK_VO2MAX),
        ),
    ):
        yield


@pytest.fixture
def client(mock_services):
    """
    TestClient with Garmin auth simulated as successful.

    - Patches the startup initializer to a no-op so no real Garmin calls occur.
    - Sets the module-level auth flag directly so is_auth_ready() returns True.
    """
    with patch("app.main.initialize_garmin_client"):
        garmin_client_module._auth_ready = True
        garmin_client_module._client = MagicMock()
        try:
            with TestClient(app, raise_server_exceptions=True) as test_client:
                yield test_client
        finally:
            garmin_client_module._auth_ready = False
            garmin_client_module._client = None


@pytest.fixture
def unauthenticated_client():
    """
    TestClient where the Garmin session is unavailable.

    Metrics endpoints should return 503 in this state.
    """
    with patch("app.main.initialize_garmin_client"):
        garmin_client_module._auth_ready = False
        garmin_client_module._client = None
        with TestClient(app, raise_server_exceptions=True) as test_client:
            yield test_client
