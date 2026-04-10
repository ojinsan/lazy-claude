"""
Alert queue reader — run by OpenClaw cron every 2 minutes.
Reads unread alerts from monitor queue and prints them for OpenClaw to forward to Mr O.
"""
import json
import os
import sys
import time

QUEUE_FILE = "/tmp/lazyboy_alert_queue.jsonl"
SENT_FILE = "/tmp/lazyboy_alert_sent.txt"

def main():
    if not os.path.exists(QUEUE_FILE):
        print("NO_ALERTS")
        return

    # Load already-sent timestamps
    sent = set()
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE) as f:
            sent = set(f.read().splitlines())

    alerts = []
    with open(QUEUE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                key = f"{entry['ts']}:{entry['key']}"
                if key not in sent:
                    alerts.append((key, entry))
            except:
                pass

    if not alerts:
        print("NO_ALERTS")
        return

    # Mark as sent
    with open(SENT_FILE, "a") as f:
        for key, _ in alerts:
            f.write(key + "\n")

    # Print alerts for OpenClaw to forward
    for _, entry in alerts:
        print(entry["message"])
        print("---")

if __name__ == "__main__":
    main()
