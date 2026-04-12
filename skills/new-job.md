---
name: new-job
description: Create a new scheduled job interactively — asks for name, purpose, and schedule, then scaffolds job file and optional script.
disable-model-invocation: true
---

Create a new scheduled job. Ask the user for:
1. Job name
2. What it should do
3. Schedule (cron expression or plain English like "every day at 8am")

Then create schedule/<name>.md using the format defined in rules/schedule.md.
If the job needs a script, scaffold it in tools/<name>.py or tools/<name>.sh.
Do not register the schedule yet — ask the user to confirm first.
