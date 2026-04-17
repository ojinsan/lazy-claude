"""Telegram client wrapper with authentication."""
from __future__ import annotations

from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import User, Channel, Chat

from ..config import Settings
from .auth import ensure_authorized


class TelegramClientWrapper:
    """Wrapper around Telethon client with auth handling."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: TelegramClient | None = None
        self._dialogs_cache: dict[str, int] = {}

    @property
    def client(self) -> TelegramClient:
        """Get the underlying Telethon client."""
        if self._client is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._client

    async def connect(self) -> bool:
        """Connect and authenticate the client."""
        session_path = str(self.settings.session_path)

        self._client = TelegramClient(
            session_path,
            self.settings.api_id,
            self.settings.api_hash,
        )

        await self._client.connect()

        # Ensure authorized
        authorized = await ensure_authorized(
            self._client,
            self.settings.phone,
            self.settings.password,
            self.settings.bot_token,
            self.settings.bot_chat_id,
            self.settings.api_id,
            self.settings.api_hash,
        )

        if not authorized:
            await self.disconnect()
            return False

        # Pre-cache dialogs
        await self._cache_dialogs()
        return True

    async def disconnect(self) -> None:
        """Disconnect the client."""
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def _cache_dialogs(self) -> None:
        """Cache dialog name -> id mappings."""
        async for dialog in self.client.iter_dialogs():
            name = dialog.name or ""
            if name:
                self._dialogs_cache[name.lower()] = dialog.id

    def find_chat_id(self, name: str) -> int | None:
        """Find chat ID by name (case-insensitive partial match)."""
        name_lower = name.lower()

        # Exact match first
        if name_lower in self._dialogs_cache:
            return self._dialogs_cache[name_lower]

        # Partial match
        for cached_name, chat_id in self._dialogs_cache.items():
            if name_lower in cached_name or cached_name in name_lower:
                return chat_id

        return None

    async def get_message(self, chat_id: int, message_id: int):
        """Fetch a single message by ID."""
        try:
            messages = await self.client.get_messages(chat_id, ids=message_id)
            return messages if messages else None
        except Exception:
            return None

    async def iter_messages(
        self,
        chat_id: int,
        limit: int = 500,
        offset_date=None,
        reverse: bool = False,
    ):
        """Iterate messages from a chat."""
        async for msg in self.client.iter_messages(
            chat_id,
            limit=limit,
            offset_date=offset_date,
            reverse=reverse,
        ):
            yield msg

    def get_sender_name(self, message) -> str:
        """Extract sender name from a message."""
        sender = message.sender
        if sender is None:
            return "Unknown"
        if isinstance(sender, User):
            parts = [sender.first_name or "", sender.last_name or ""]
            return " ".join(p for p in parts if p).strip() or sender.username or "Unknown"
        if isinstance(sender, (Channel, Chat)):
            return sender.title or "Unknown"
        return "Unknown"

    async def download_media(self, message, path: Path) -> Path | None:
        """Download media from a message."""
        if not message.media:
            return None
        try:
            result = await self.client.download_media(message, file=str(path))
            return Path(result) if result else None
        except Exception:
            return None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
