"""Reply chain resolver for fetching messages outside the time window."""
from __future__ import annotations

from datetime import datetime

from ..core.client import TelegramClientWrapper
from ..core.message import Message
from ..config import ChatConfig
from ..utils.time import to_utc


class ReplyResolver:
    """Resolves reply chains to fetch context messages outside the time window."""

    def __init__(
        self,
        client: TelegramClientWrapper,
        max_depth: int = 5,
    ):
        self.client = client
        self.max_depth = max_depth

    async def resolve_replies(
        self,
        messages: list[Message],
        chat_id: int,
        chat_config: ChatConfig,
        window_start: datetime,
    ) -> list[Message]:
        """
        Fetch all replied messages that are outside the current window.

        For admin messages that reply to older messages, fetches the
        original message as context.

        Args:
            messages: Messages in the current window
            chat_id: Telegram chat ID
            chat_config: Chat configuration for admin detection
            window_start: Start of the current time window

        Returns:
            List of context messages (replied-to messages outside window)
        """
        context_messages = []
        seen_ids = {m.id for m in messages}
        to_resolve = []

        # Find admin messages that reply to something outside window
        for msg in messages:
            if msg.is_admin and msg.reply_to_msg_id:
                if msg.reply_to_msg_id not in seen_ids:
                    to_resolve.append((msg.reply_to_msg_id, 0))

        # Resolve replies up to max depth
        while to_resolve:
            msg_id, depth = to_resolve.pop(0)

            if depth >= self.max_depth:
                continue

            if msg_id in seen_ids:
                continue

            # Fetch the message
            raw_msg = await self.client.get_message(chat_id, msg_id)
            if not raw_msg:
                continue

            # Convert to our Message type
            context_msg = self._convert_message(
                raw_msg,
                chat_id,
                chat_config,
            )
            if context_msg:
                context_messages.append(context_msg)
                seen_ids.add(msg_id)

                # If this message also replies to something, add to queue
                if raw_msg.reply_to and raw_msg.reply_to.reply_to_msg_id:
                    reply_id = raw_msg.reply_to.reply_to_msg_id
                    if reply_id not in seen_ids:
                        to_resolve.append((reply_id, depth + 1))

        return context_messages

    def _convert_message(
        self,
        raw_msg,
        chat_id: int,
        chat_config: ChatConfig,
    ) -> Message | None:
        """Convert a Telethon message to our Message type."""
        text = raw_msg.text or ""
        if not text and not raw_msg.media:
            return None

        sender_name = self.client.get_sender_name(raw_msg)
        sender_id = raw_msg.sender_id

        reply_to_id = None
        if raw_msg.reply_to:
            reply_to_id = raw_msg.reply_to.reply_to_msg_id

        return Message(
            id=raw_msg.id,
            chat_id=chat_id,
            sender_name=sender_name,
            sender_id=sender_id,
            text=text,
            timestamp=to_utc(raw_msg.date),
            reply_to_msg_id=reply_to_id,
            is_admin=chat_config.is_admin(sender_name),
        )
