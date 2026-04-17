#!/usr/bin/env python3
"""
Telegram Scraper - Realtime Mode

Continuously scrapes Telegram chats every 30 minutes.
For groups: Only processes snapshots with admin messages.
For channels: All messages are considered admin.
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta, timezone

from .config import Settings, CHAT_CONFIGS
from .core import TelegramClientWrapper
from .scrapers import SnapshotCollector
from .api import BackendAPIClient


async def run_realtime(settings: Settings) -> None:
    """Run the realtime scraper loop."""
    print(f"Starting Telegram scraper (realtime mode)")
    print(f"  Lookback: {settings.lookback_minutes} minutes")
    print(f"  Poll interval: {settings.poll_interval_minutes} minutes")
    print(f"  Chats: {', '.join(CHAT_CONFIGS.keys())}")
    print(f"  API URL: {settings.insight_api_url}")
    if settings.dry_run:
        print("  [DRY RUN MODE - no data will be submitted]")
    print()

    async with TelegramClientWrapper(settings) as client:
        collector = SnapshotCollector(client, settings)

        async with BackendAPIClient(settings) as api:
            while True:
                now = datetime.now(timezone.utc)
                window_start = now - timedelta(minutes=settings.lookback_minutes)

                print(f"[{now.isoformat()}] Collecting snapshots...")

                for chat_config in CHAT_CONFIGS.values():
                    try:
                        snapshot = await collector.collect_snapshot(
                            chat_config,
                            window_start,
                            now,
                        )

                        if snapshot:
                            msg_count = len(snapshot.messages)
                            ctx_count = len(snapshot.reply_context)
                            print(f"  {chat_config.name}: {msg_count} msgs, {ctx_count} ctx")

                            result = await api.submit_snapshot(snapshot)
                            if not settings.dry_run:
                                print(f"    -> Stored: {result.get('stored', 0)}")
                        else:
                            print(f"  {chat_config.name}: no relevant messages")

                    except Exception as e:
                        print(f"  {chat_config.name}: ERROR - {e}")

                # Sleep until next poll
                sleep_seconds = settings.poll_interval_minutes * 60
                print(f"\nSleeping for {settings.poll_interval_minutes} minutes...\n")
                await asyncio.sleep(sleep_seconds)


def main() -> None:
    """Main entry point."""
    settings = Settings()

    # Handle graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown_handler(sig, frame):
        print("\nShutdown requested...")
        for task in asyncio.all_tasks(loop):
            task.cancel()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        loop.run_until_complete(run_realtime(settings))
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
