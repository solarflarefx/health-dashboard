"""Integration tests for all FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/health").status_code == 200

    def test_returns_ok_status(self, client: TestClient) -> None:
        assert client.get("/health").json() == {"status": "ok"}

    def test_available_when_unauthenticated(self, unauthenticated_client: TestClient) -> None:
        """Health check must succeed regardless of Garmin auth state."""
        assert unauthenticated_client.get("/health").status_code == 200


class TestTodayMetrics:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/api/metrics/today").status_code == 200

    def test_response_shape(self, client: TestClient) -> None:
        data = client.get("/api/metrics/today").json()
        assert "steps" in data
        assert "steps_goal" in data
        assert "active_calories" in data
        assert "activity_time" in data

    def test_field_types(self, client: TestClient) -> None:
        data = client.get("/api/metrics/today").json()
        assert isinstance(data["steps"], int)
        assert isinstance(data["steps_goal"], int)
        assert isinstance(data["active_calories"], int)
        assert isinstance(data["activity_time"], int)

    def test_503_when_unauthenticated(self, unauthenticated_client: TestClient) -> None:
        assert unauthenticated_client.get("/api/metrics/today").status_code == 503

    def test_503_detail_message(self, unauthenticated_client: TestClient) -> None:
        response = unauthenticated_client.get("/api/metrics/today")
        assert "detail" in response.json()


class TestHeartMetrics:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/api/metrics/heart").status_code == 200

    def test_response_shape(self, client: TestClient) -> None:
        data = client.get("/api/metrics/heart").json()
        assert "resting_hr" in data
        assert "min_hr" in data
        assert "max_hr" in data
        assert "stress_score" in data

    def test_field_types(self, client: TestClient) -> None:
        data = client.get("/api/metrics/heart").json()
        assert isinstance(data["resting_hr"], int)
        assert isinstance(data["stress_score"], int)

    def test_503_when_unauthenticated(self, unauthenticated_client: TestClient) -> None:
        assert unauthenticated_client.get("/api/metrics/heart").status_code == 503


class TestMovementMetrics:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/api/metrics/movement").status_code == 200

    def test_response_shape(self, client: TestClient) -> None:
        data = client.get("/api/metrics/movement").json()
        assert "weekly_activities" in data
        assert "intensity_minutes" in data
        assert "intensity_goal" in data
        assert "distance" in data
        assert "elevation" in data

    def test_field_types(self, client: TestClient) -> None:
        data = client.get("/api/metrics/movement").json()
        assert isinstance(data["weekly_activities"], int)
        assert isinstance(data["distance"], float)
        assert isinstance(data["elevation"], float)

    def test_503_when_unauthenticated(self, unauthenticated_client: TestClient) -> None:
        assert unauthenticated_client.get("/api/metrics/movement").status_code == 503


class TestVO2MaxEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/api/metrics/vo2max").status_code == 200

    def test_response_shape(self, client: TestClient) -> None:
        data = client.get("/api/metrics/vo2max").json()
        assert "current" in data
        assert "change_this_month" in data
        assert "history" in data

    def test_history_is_list(self, client: TestClient) -> None:
        data = client.get("/api/metrics/vo2max").json()
        assert isinstance(data["history"], list)

    def test_history_points_have_week_and_value(self, client: TestClient) -> None:
        data = client.get("/api/metrics/vo2max").json()
        assert len(data["history"]) > 0
        for point in data["history"]:
            assert "week" in point
            assert "value" in point
            assert isinstance(point["value"], float)

    def test_503_when_unauthenticated(self, unauthenticated_client: TestClient) -> None:
        assert unauthenticated_client.get("/api/metrics/vo2max").status_code == 503


class TestMetricHistoryEndpoint:
    @pytest.mark.parametrize(
        "metric_name",
        ["steps", "resting-hr", "stress"],
    )
    def test_valid_metric_returns_200(self, client: TestClient, metric_name: str) -> None:
        assert client.get(f"/api/metrics/history/{metric_name}").status_code == 200

    @pytest.mark.parametrize(
        "metric_name",
        ["steps", "resting-hr", "stress"],
    )
    def test_response_shape(self, client: TestClient, metric_name: str) -> None:
        data = client.get(f"/api/metrics/history/{metric_name}").json()
        assert data["metric"] == metric_name
        assert data["days"] == 7
        assert "history" in data
        assert isinstance(data["history"], list)
        assert len(data["history"]) > 0
        for point in data["history"]:
            assert "date" in point
            assert "value" in point
            assert isinstance(point["value"], float)

    def test_invalid_metric_returns_400(self, client: TestClient) -> None:
        response = client.get("/api/metrics/history/unknown")
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_custom_days_parameter(self, client: TestClient, mock_services: dict) -> None:
        data = client.get("/api/metrics/history/steps?days=14").json()
        assert data["days"] == 14
        mock_services["get_steps_history"].assert_awaited_once_with(14)

    def test_502_when_fetcher_fails(self, client: TestClient, mock_services: dict) -> None:
        mock_services["get_steps_history"].side_effect = RuntimeError("internal garmin failure")
        response = client.get("/api/metrics/history/steps")
        assert response.status_code == 502
        assert response.json()["detail"] == "Failed to fetch metric history from Garmin"

    def test_days_below_minimum_returns_422(self, client: TestClient) -> None:
        assert client.get("/api/metrics/history/steps?days=0").status_code == 422

    def test_days_above_maximum_returns_422(self, client: TestClient) -> None:
        assert client.get("/api/metrics/history/steps?days=91").status_code == 422

    def test_503_when_unauthenticated(self, unauthenticated_client: TestClient) -> None:
        assert unauthenticated_client.get("/api/metrics/history/steps").status_code == 503


class TestAuthEndpoints:
    def test_auth_status_returns_200(self, client: TestClient) -> None:
        assert client.get("/api/auth/status").status_code == 200

    def test_auth_status_shape(self, client: TestClient) -> None:
        data = client.get("/api/auth/status").json()
        assert "authenticated" in data
        assert "message" in data
        assert isinstance(data["authenticated"], bool)

    def test_auth_status_true_when_client_ready(self, client: TestClient) -> None:
        data = client.get("/api/auth/status").json()
        assert data["authenticated"] is True

    def test_auth_status_false_when_unauthenticated(self, unauthenticated_client: TestClient) -> None:
        data = unauthenticated_client.get("/api/auth/status").json()
        assert data["authenticated"] is False


class TestUnknownEndpoints:
    def test_unknown_route_returns_404(self, client: TestClient) -> None:
        assert client.get("/api/metrics/nonexistent").status_code == 404
