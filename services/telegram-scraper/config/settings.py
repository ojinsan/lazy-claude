"""Pydantic settings for Telegram scraper configuration."""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path | None:
    """Find .env file in hierarchy: telegram/ -> scrapper_client/ -> root."""
    current = Path(__file__).parent.parent  # telegram/
    candidates = [
        current / ".env",
        current.parent / ".env",  # scrapper_client/
        current.parent.parent / ".env",  # root
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


class Settings(BaseSettings):
    """Telegram scraper configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TG_",
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram API credentials
    api_id: int
    api_hash: str
    session_name: str = "telegram_session"
    phone: str
    password: str | None = None

    # OTP via bot (optional)
    bot_token: str | None = None
    bot_chat_id: int | None = None

    # Scraping settings
    lookback_minutes: int = 30
    max_reply_depth: int = 5
    poll_interval_minutes: int = 30

    # Backend API
    insight_api_url: str = "http://localhost:8787/feed/telegram/insight"
    upload_url: str = "http://localhost:8787/upload"
    api_timeout: int = 30
    api_token: str | None = None  # Bearer token for authenticated requests

    # Backfill settings
    backfill_batch_size: int = 5

    # Debug options
    dry_run: bool = False
    print_messages: bool = False

    @property
    def session_path(self) -> Path:
        """Get full path to session file."""
        return Path(__file__).parent.parent / self.session_name
