"""Message and Snapshot dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """Represents a Telegram message."""

    id: int
    chat_id: int
    sender_name: str
    sender_id: int | None
    text: str
    timestamp: datetime
    reply_to_msg_id: int | None = None
    is_admin: bool = False
    media_path: str | None = None

    def to_content_line(self) -> str:
        """Format message as a content line for the API."""
        ts = self.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        admin_tag = " [admin]" if self.is_admin else ""
        line = f"[{ts}] {self.sender_name}{admin_tag}: {self.text}"
        if self.media_path:
            line += f"\n[image: {self.media_path}]"
        return line


@dataclass
class Snapshot:
    """Represents a 30-minute snapshot of messages from a chat."""

    chat_name: str
    chat_id: int
    window_start: datetime
    window_end: datetime
    messages: list[Message] = field(default_factory=list)
    reply_context: list[Message] = field(default_factory=list)

    def has_admin_messages(self) -> bool:
        """Check if snapshot contains any admin messages."""
        return any(m.is_admin for m in self.messages)

    def to_content(self) -> str:
        """Format snapshot as content string for the API."""
        lines = []

        # Add context messages first (older, replied-to messages)
        if self.reply_context:
            lines.append("--- Reply Context (older messages) ---")
            for msg in sorted(self.reply_context, key=lambda m: m.timestamp):
                lines.append(msg.to_content_line())
            lines.append("")
            lines.append("--- Main Conversation ---")

        # Add main messages
        for msg in sorted(self.messages, key=lambda m: m.timestamp):
            lines.append(msg.to_content_line())

        return "\n".join(lines)

    def to_address_text(self) -> str:
        """Generate address text for the API."""
        window_str = self.window_start.strftime("%Y%m%d_%H%M")
        chat_slug = self.chat_name.lower().replace(" ", "_")
        return f"telegram:{chat_slug}:snapshot_{window_str}"
