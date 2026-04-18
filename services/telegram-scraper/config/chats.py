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


# Chat configurations — Boss O's account
CHAT_CONFIGS: dict[str, ChatConfig] = {
    # RLA group/channels (all accessible)
    "RLA Markibel": ChatConfig(
        name="RLA Markibel",
        chat_type="channel",
        force_all_admin=True,
    ),
    "RLA INVESTOR GROUP": ChatConfig(
        name="RLA INVESTOR GROUP",
        chat_type="channel",
        force_all_admin=True,
    ),
    "RLA STOCKPICK Channel": ChatConfig(
        name="RLA STOCKPICK Channel",
        chat_type="channel",
        force_all_admin=True,
    ),
    "RLA INVESTOR CHANNEL": ChatConfig(
        name="RLA INVESTOR CHANNEL",
        chat_type="channel",
        force_all_admin=True,
    ),
    "RLA GUIDANCE CHANNEL": ChatConfig(
        name="RLA GUIDANCE CHANNEL",
        chat_type="channel",
        force_all_admin=True,
    ),
    # Independent stock channels
    "Ngecap saham": ChatConfig(
        name="Ngecap saham",
        chat_type="channel",
        force_all_admin=True,
    ),
    "Morfus' Trading Idea": ChatConfig(
        name="Morfus' Trading Idea",
        chat_type="channel",
        force_all_admin=True,
    ),
    "UntungStock Discussion": ChatConfig(
        name="UntungStock Discussion",
        chat_type="channel",
        force_all_admin=True,
    ),
    "indx stocks reborn": ChatConfig(
        name="indx stocks reborn",
        chat_type="channel",
        force_all_admin=True,
    ),
    "MY - SWING PLAN": ChatConfig(
        name="MY - SWING PLAN",
        chat_type="channel",
        force_all_admin=True,
    ),
    "MY - Daily TRADE": ChatConfig(
        name="MY - Daily TRADE",
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
