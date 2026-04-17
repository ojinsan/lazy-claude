"""Core module for Telegram client and authentication."""

from .client import TelegramClientWrapper
from .message import Message, Snapshot
from .auth import request_otp_via_bot, request_otp_stdin

__all__ = [
    "TelegramClientWrapper",
    "Message",
    "Snapshot",
    "request_otp_via_bot",
    "request_otp_stdin",
]
