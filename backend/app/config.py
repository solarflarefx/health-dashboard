from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at backend/app/config.py → go up two levels to reach the project root.
_PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Token store is always at <project_root>/.secrets/garmin, regardless of cwd.
TOKEN_STORE_PATH: Path = _PROJECT_ROOT / ".secrets" / "garmin"


class Settings(BaseSettings):
    garmin_email: str
    garmin_password: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
