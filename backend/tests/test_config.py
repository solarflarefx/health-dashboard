"""Tests for application configuration and Settings validation."""
import pytest
from pydantic import ValidationError

from app.config import Settings


class TestSettingsValidation:
    def test_loads_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GARMIN_EMAIL", "athlete@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "s3cr3tP@ss")
        s = Settings(_env_file=None)
        assert s.garmin_email == "athlete@example.com"
        assert s.garmin_password == "s3cr3tP@ss"

    def test_missing_email_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GARMIN_EMAIL", raising=False)
        monkeypatch.delenv("GARMIN_PASSWORD", raising=False)
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        field_names = {e["loc"][0] for e in exc_info.value.errors()}
        assert "garmin_email" in field_names

    def test_missing_password_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GARMIN_EMAIL", "athlete@example.com")
        monkeypatch.delenv("GARMIN_PASSWORD", raising=False)
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        field_names = {e["loc"][0] for e in exc_info.value.errors()}
        assert "garmin_password" in field_names

    def test_missing_both_fields_raises_two_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GARMIN_EMAIL", raising=False)
        monkeypatch.delenv("GARMIN_PASSWORD", raising=False)
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        field_names = {e["loc"][0] for e in exc_info.value.errors()}
        assert field_names == {"garmin_email", "garmin_password"}

    def test_extra_env_vars_are_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GARMIN_EMAIL", "athlete@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "s3cr3tP@ss")
        monkeypatch.setenv("TOTALLY_UNKNOWN_VAR", "ignored")
        s = Settings(_env_file=None)
        assert not hasattr(s, "totally_unknown_var")

    def test_credentials_are_strings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GARMIN_EMAIL", "athlete@example.com")
        monkeypatch.setenv("GARMIN_PASSWORD", "s3cr3tP@ss")
        s = Settings(_env_file=None)
        assert isinstance(s.garmin_email, str)
        assert isinstance(s.garmin_password, str)
