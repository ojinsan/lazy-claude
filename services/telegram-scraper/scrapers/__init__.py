"""Scrapers module for Telegram message collection."""

from .snapshot import SnapshotCollector
from .reply_resolver import ReplyResolver

__all__ = ["SnapshotCollector", "ReplyResolver"]
