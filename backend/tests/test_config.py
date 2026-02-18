"""Tests for configuration and conditional sender behavior."""

from pathlib import Path
from unittest.mock import patch

from campaign.config import Settings


class TestDefaultSettings:
    def test_default_send_backend(self):
        s = Settings(
            _env_file=None,
        )
        assert s.send_backend == "gmail_api"

    def test_default_daily_send_limit(self):
        s = Settings(_env_file=None)
        assert s.daily_send_limit == 500

    def test_default_reply_check_interval(self):
        s = Settings(_env_file=None)
        assert s.reply_check_interval_minutes == 2


class TestPlaywrightSettings:
    def test_playwright_defaults(self):
        s = Settings(_env_file=None)
        assert s.playwright_send_delay_seconds == 30
        assert s.playwright_page_timeout_ms == 15000
        assert s.playwright_browser == "chromium"
        assert isinstance(s.playwright_session_dir, Path)

    @patch.dict(
        "os.environ",
        {
            "SEND_BACKEND": "playwright",
            "PLAYWRIGHT_SEND_DELAY_SECONDS": "10",
            "PLAYWRIGHT_PAGE_TIMEOUT_MS": "20000",
            "PLAYWRIGHT_BROWSER": "firefox",
        },
    )
    def test_playwright_env_override(self):
        s = Settings(_env_file=None)
        assert s.send_backend == "playwright"
        assert s.playwright_send_delay_seconds == 10
        assert s.playwright_page_timeout_ms == 20000
        assert s.playwright_browser == "firefox"


class TestEnvironment:
    def test_default_is_development(self):
        s = Settings(_env_file=None)
        assert s.environment == "development"
        assert s.is_production is False

    @patch.dict("os.environ", {"ENVIRONMENT": "production"})
    def test_production(self):
        s = Settings(_env_file=None)
        assert s.is_production is True
