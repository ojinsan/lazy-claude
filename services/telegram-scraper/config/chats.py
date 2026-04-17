"""Chat configuration for Telegram scraper."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ChatConfig:
    """Configuration for a single Telegram chat to scrape."""

    name: str
    chat_type: Literal["group", "channel"]
    admin_keywords: list[str] = field(default_factory=list)
    force_all_admin: bool = False

    def is_admin(self, sender_name: str) -> bool:
        """Check if sender is an admin based on keywords or force flag."""
        if self.force_all_admin:
            return True
        if not sender_name:
            return False
        name_lower = sender_name.lower()
        return any(kw.lower() in name_lower for kw in self.admin_keywords)


# Default chat configurations
CHAT_CONFIGS: dict[str, ChatConfig] = {
    "RLA Markibel": ChatConfig(
        name="RLA Markibel",
        chat_type="group",
        admin_keywords=["illusix", "rivan t", "robby", "budi9696"],
    ),
    "RLA INVESTOR GROUP": ChatConfig(
        name="RLA INVESTOR GROUP",
        chat_type="group",
        admin_keywords=["illusix", "rivan t", "robby", "budi9696"],
    ),
    "RLA STOCKPICK CHANNEL": ChatConfig(
        name="RLA STOCKPICK CHANNEL",
        chat_type="channel",
        force_all_admin=True,
    ),
    "RLA INVESTOR CHANNEL": ChatConfig(
        name="RLA INVESTOR CHANNEL",
        chat_type="channel",
        force_all_admin=True,
    ),
}


def get_chat_config(name: str) -> ChatConfig | None:
    """Get chat config by name (case-insensitive partial match)."""
    name_lower = name.lower()
    for key, config in CHAT_CONFIGS.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return config
    return None
