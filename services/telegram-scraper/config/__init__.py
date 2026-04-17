"""Configuration module for Telegram scraper."""

from .settings import Settings
from .chats import ChatConfig, CHAT_CONFIGS

__all__ = ["Settings", "ChatConfig", "CHAT_CONFIGS"]
