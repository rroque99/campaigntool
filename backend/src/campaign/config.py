from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./campaign.db"
    credentials_dir: Path = Path("../credentials")
    cors_origins: list[str] = ["http://localhost:5173"]
    gmail_scopes: list[str] = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]
    send_backend: str = "gmail_api"
    playwright_session_dir: Path = Path("../credentials/playwright-session")
    playwright_send_delay_seconds: int = 30
    playwright_page_timeout_ms: int = 15000
    playwright_browser: str = "chromium"
    daily_send_limit: int = 500
    reply_check_interval_minutes: int = 2
    api_prefix: str = "/api/v1"
    environment: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
