"""Snapshot collector for 30-minute message windows."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..core.client import TelegramClientWrapper
from ..core.message import Message, Snapshot
from ..config import Settings, ChatConfig, CHAT_CONFIGS
from ..utils.time import to_utc
from .reply_resolver import ReplyResolver


class SnapshotCollector:
    """Collects 30-minute snapshots of messages from Telegram chats."""

    def __init__(
        self,
        client: TelegramClientWrapper,
        settings: Settings,
    ):
        self.client = client
        self.settings = settings
        self.reply_resolver = ReplyResolver(
            client,
            max_depth=settings.max_reply_depth,
        )
        self._media_dir = Path(__file__).parent.parent / "media"

    async def collect_snapshot(
        self,
        chat_config: ChatConfig,
        start_time: datetime,
        end_time: datetime,
    ) -> Snapshot | None:
        """
        Collect a 30-minute snapshot from a chat.

        For groups: Only returns snapshot if admin is present in the window.
        For channels: All messages are considered admin.

        Includes replied-to messages from outside the window as context.

        Args:
            chat_config: Configuration for the chat
            start_time: Start of the time window (UTC)
            end_time: End of the time window (UTC)

        Returns:
            Snapshot if there are relevant messages, None otherwise
        """
        # Find chat ID
        chat_id = self.client.find_chat_id(chat_config.name)
        if chat_id is None:
            print(f"Chat not found: {chat_config.name}")
            return None

        # Fetch messages in window
        messages = await self._fetch_messages_in_window(
            chat_id,
            chat_config,
            start_time,
            end_time,
        )

        if not messages:
            return None

        # For groups: check if any admin is present
        if chat_config.chat_type == "group":
            admin_messages = [m for m in messages if m.is_admin]
            if not admin_messages:
                # No admin in this window - skip
                return None

        # Resolve replies to messages outside window
        reply_context = await self.reply_resolver.resolve_replies(
            messages,
            chat_id,
            chat_config,
            start_time,
        )

        return Snapshot(
            chat_name=chat_config.name,
            chat_id=chat_id,
            window_start=start_time,
            window_end=end_time,
            messages=messages,
            reply_context=reply_context,
        )

    async def _fetch_messages_in_window(
        self,
        chat_id: int,
        chat_config: ChatConfig,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Message]:
        """Fetch all messages within the time window."""
        messages = []

        async for raw_msg in self.client.iter_messages(
            chat_id,
            limit=500,
            offset_date=end_time,
        ):
            msg_time = to_utc(raw_msg.date)

            # Stop if we've gone past the start of the window
            if msg_time < start_time:
                break

            # Skip if outside window (shouldn't happen with offset_date)
            if msg_time > end_time:
                continue

            # Convert message
            msg = self._convert_message(raw_msg, chat_id, chat_config)
            if msg:
                messages.append(msg)

        return messages

    def _convert_message(
        self,
        raw_msg,
        chat_id: int,
        chat_config: ChatConfig,
    ) -> Message | None:
        """Convert a Telethon message to our Message type."""
        text = raw_msg.text or ""

        # Skip empty messages (no text and no media)
        if not text and not raw_msg.media:
            return None

        sender_name = self.client.get_sender_name(raw_msg)
        sender_id = raw_msg.sender_id

        reply_to_id = None
        if raw_msg.reply_to:
            reply_to_id = raw_msg.reply_to.reply_to_msg_id

        is_admin = chat_config.is_admin(sender_name)

        return Message(
            id=raw_msg.id,
            chat_id=chat_id,
            sender_name=sender_name,
            sender_id=sender_id,
            text=text,
            timestamp=to_utc(raw_msg.date),
            reply_to_msg_id=reply_to_id,
            is_admin=is_admin,
        )

    async def collect_all_chats(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Snapshot]:
        """Collect snapshots from all configured chats."""
        snapshots = []

        for chat_config in CHAT_CONFIGS.values():
            snapshot = await self.collect_snapshot(
                chat_config,
                start_time,
                end_time,
            )
            if snapshot:
                snapshots.append(snapshot)

        return snapshots
