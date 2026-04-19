---
name: trade
description: Trading task entrypoint — Indonesian stock market (IDX/IHSG). Loads trader context and confirms before any external actions.
disable-model-invocation: true
---

Trading task entrypoint.
Read these two files at session start:
1. `playbooks/trader/CLAUDE.md` — mission, 4-layer system, schedule, data pipeline
2. `skills/trader/CLAUDE.md` — philosophy, SID rules, broker classification, skills index, tools map

Each CLAUDE.md chains to further files on demand — load only what the active layer or task needs.
Always confirm before executing any real orders or sending any data externally.
Report values in IDR unless user specifies otherwise.
