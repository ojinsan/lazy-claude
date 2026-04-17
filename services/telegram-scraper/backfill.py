#!/usr/bin/env python3
"""
Telegram Scraper - Backfill Mode

Processes historical messages in 30-minute chunks.
Default: Last 2 weeks.
Supports --start and --end date parameters (YYYYMMDD format).
Processes in batches of 5 API calls to avoid overloading the backend.
"""

import argparse
import asyncio
import signal
import sys
from datetime import datetime, date, timedelta, timezone

from .config import Settings, CHAT_CONFIGS
from .core import TelegramClientWrapper
from .scrapers import SnapshotCollector
from .api import BackendAPIClient
from .utils.time import generate_30min_windows, chunked


def parse_date(date_str: str) -> date:
    """Parse date from YYYYMMDD format."""
    return datetime.strptime(date_str, "%Y%m%d").date()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill Telegram messages in 30-minute chunks."
    )
    parser.add_argument(
        "--start",
        type=str,
        help="Start date (YYYYMMDD format). Default: 2 weeks ago.",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End date (YYYYMMDD format). Default: today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without submitting to API.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed progress.",
    )
    return parser.parse_args()


async def run_backfill(
    settings: Settings,
    start_date: date,
    end_date: date,
    verbose: bool = False,
) -> None:
    """Run the backfill process."""
    print(f"Starting Telegram backfill")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Batch size: {settings.backfill_batch_size}")
    print(f"  Chats: {', '.join(CHAT_CONFIGS.keys())}")
    print(f"  API URL: {settings.insight_api_url}")
    if settings.dry_run:
        print("  [DRY RUN MODE - no data will be submitted]")
    print()

    # Generate all 30-minute windows
    windows = generate_30min_windows(start_date, end_date)
    total_windows = len(windows)
    print(f"Total windows to process: {total_windows}")
    print()

    async with TelegramClientWrapper(settings) as client:
        collector = SnapshotCollector(client, settings)

        async with BackendAPIClient(settings) as api:
            for chat_config in CHAT_CONFIGS.values():
                print(f"\n{'='*60}")
                print(f"Processing: {chat_config.name}")
                print(f"{'='*60}")

                processed = 0
                submitted = 0
                errors = 0

                # Process windows in batches
                for batch_idx, batch in enumerate(chunked(windows, settings.backfill_batch_size)):
                    batch_start = batch[0][0]
                    batch_end = batch[-1][1]

                    if verbose:
                        print(f"\nBatch {batch_idx + 1}: {batch_start} to {batch_end}")

                    for window_start, window_end in batch:
                        try:
                            snapshot = await collector.collect_snapshot(
                                chat_config,
                                window_start,
                                window_end,
                            )

                            processed += 1

                            if snapshot:
                                result = await api.submit_snapshot(snapshot)
                                stored = result.get("stored", 0)
                                submitted += 1

                                if verbose:
                                    msg_count = len(snapshot.messages)
                                    print(f"  [{window_start.strftime('%Y-%m-%d %H:%M')}] "
                                          f"{msg_count} msgs -> stored {stored}")
                            elif verbose:
                                print(f"  [{window_start.strftime('%Y-%m-%d %H:%M')}] "
                                      f"no relevant messages")

                        except Exception as e:
                            errors += 1
                            print(f"  [{window_start.strftime('%Y-%m-%d %H:%M')}] "
                                  f"ERROR: {e}")

                    # Rate limit between batches
                    if batch_idx < (total_windows // settings.backfill_batch_size):
                        await asyncio.sleep(1)

                    # Progress update
                    progress = (processed / total_windows) * 100
                    print(f"  Progress: {processed}/{total_windows} ({progress:.1f}%)")

                print(f"\n{chat_config.name} complete:")
                print(f"  Processed: {processed}")
                print(f"  Submitted: {submitted}")
                print(f"  Errors: {errors}")

    print("\n" + "="*60)
    print("Backfill complete!")


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Parse dates
    today = date.today()
    two_weeks_ago = today - timedelta(weeks=2)

    start_date = parse_date(args.start) if args.start else two_weeks_ago
    end_date = parse_date(args.end) if args.end else today

    if start_date > end_date:
        print("Error: Start date must be before end date")
        sys.exit(1)

    # Load settings
    settings = Settings()
    if args.dry_run:
        settings.dry_run = True
        settings.print_messages = args.verbose

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
        loop.run_until_complete(
            run_backfill(settings, start_date, end_date, args.verbose)
        )
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
