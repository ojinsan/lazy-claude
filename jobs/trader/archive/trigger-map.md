# Trader Trigger Map

## Purpose

Define who triggers each layer of Scarlett trader workflow and what belongs to code vs AI.

## Architecture Rule

```
Code (cron) → collects and compresses data → writes to local storage
Scarlett (AI via heartbeat) → reads local storage → thinks → acts
```

No Python script should contain market judgment, signal classification, or trade decisions.

## Layer 1 — Global Context

**Trigger:** scheduled pre-market heartbeat (05:00-05:29 WIB), or manual catch-up
**Code does:** fetch Stockbit proxies, RAG retrieval, Threads scraping, news feeds
**Scarlett does:** synthesize regime, sector leadership, narrative themes, aggression posture

## Layer 2 — Stock Screening

**Trigger:** scheduled pre-market heartbeat (05:30-05:59 WIB), or after Layer 1 completes
**Code does:** run quantitative screeners, pull technical data, output raw candidate lists
**Scarlett does:** filter for regime fit, narrative alignment, real vs noisy moves, produce shortlist

## Layer 3 — Stock Overseeing

**Trigger:** cron collects data every 10m, compresses every 30m. Scarlett reviews on heartbeat.
**Code does:** fetch orderbook + running trade snapshots, compress into 30m summaries
**Scarlett does:** read summaries → judge whale intent, fake walls, accumulation/distribution → promote or alert

## Layer 4 — Trade Plan

**Trigger:** Scarlett decides (not a threshold counter)
- when Layer 3 thinking reveals strong edge
- when Boss O directly requests
- when material market change occurs
**Code does:** fetch current orderbook, chart, running trade data for thesis building
**Scarlett does:** connect all layers → identify edge, timing, risk → build precise trade plan

## Rule

Not all layers should run all the time. Each layer has a different trigger and purpose.
Code never decides. Scarlett always decides.
