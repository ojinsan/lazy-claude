# Mission 3 — Strategy Depth

**Goal:** deepen the trader's reading of tape, flow, and ownership so signals map to real hedge-fund edges. Each case becomes a MECE triple: **Playbook** (flow), **Skill** (strategy), **Tool** (code). Nothing duplicates across layers.

**Order:** Do Mission 1 first. Mission 3 can run in parallel with Mission 2 phases M2.2–M2.5 once M1 is done — but M3 changes some `vault/data/*.json` schemas, so M2.2 must list any new tables produced by M3 before M2.5 wires dual-write.

---

## Prefix Conventions (so the tool folder doesn't blur)

| Domain | Script prefix | Skill file(s) |
|--------|---------------|---------------|
| Conglomerate ownership | `konglo_*.py` | `konglo-ownership.md` |
| Volume-price state | `vp_*.py` | `volume-price-rules.md` |
| Spring setup | `spring_*.py` | `spring-setup.md` |
| Imposter flow | `imposter_*.py` | `imposter-detection.md` |
| Tape reading | `tape_*.py` | `tape-reading.md` |
| Confluence score | `confluence_*.py` | `confluence-scoring.md` |
| Auto-trigger | `auto_trigger.py` | `auto-trigger.md` |

**Reuse rule:** if a helper already exists in `api.py`, `broker_profile.py`, `wyckoff.py`, `tick_walls.py`, or `psychology.py` — import, do not duplicate. Every new script must declare which existing helpers it composes.

**MECE rule:**
- **Playbook** = *when* this runs inside a layer, *what it reads*, *what it writes*, *what decision follows*.
- **Skill** = *rules*, *thresholds*, *examples*, *how to interpret ambiguous cases*.
- **Tool** = *callable functions + CLI* only. Zero decision prose.

---

## Phase M3.1 — Konglo Mode

### Goal
Resolve every ticker to its conglomerate group and owner family. Track flow within a group as one signal, not 5 independent tickers. Let narrative shift attention to a whole ecosystem when one name moves.

### Deliverables

#### Tool — `tools/trader/konglo_loader.py`

- Canonical source file lives at `/home/lazywork/workspace/tools/trader/data/konglo_list.json` (already copied from the reference-only dir before M3 began — committed). If missing, re-copy:
  ```bash
  mkdir -p /home/lazywork/workspace/tools/trader/data
  cp /home/lazywork/Documents/reference-only-dont-use/bitstock/waterseven/konglo_list.json /home/lazywork/workspace/tools/trader/data/konglo_list.json
  ```
- `konglo_loader` must read from `tools/trader/data/konglo_list.json`. Do NOT write to this file at runtime — it is versioned reference data, not state.
- Load + index:
  ```python
  def load() -> dict
  def group_for(ticker: str) -> Optional[dict]  # {id, name, owner, market_power, sectors, notes}
  def tickers_for_group(group_id: str) -> list[str]
  def peer_tickers(ticker: str) -> list[str]     # sibling tickers within same group
  def groups_by_sector(sector: str) -> list[dict]
  ```
- CLI: `python tools/trader/konglo_loader.py lookup BBCA` → prints group JSON.

#### Tool — `tools/trader/konglo_flow.py`

Uses `api.get_broker_distribution`, `api.get_price`, `api.get_volume_ratio`, and `konglo_loader`.

```python
def group_flow_today(group_id: str) -> dict
# Returns: {"group_id":..., "members":[{"ticker","ret_pct","vol_ratio","smart_money_net"}], "group_ret":..., "group_volume_z":..., "leaders":[...], "laggards":[...], "verdict":"rotation_in"|"rotation_out"|"mixed"}
```

#### Skill — `skills/trader/konglo-ownership.md`

Content (write this from scratch — do NOT reuse existing skill):

```markdown
# Konglo Ownership

## Why Konglo Matters
Indonesian conglomerates move tickers in lockstep. One family may control 5+ names across 3 sectors; flow rotation inside the group telegraphs intent before the tape individually confirms.

## Data
Source: `tools/trader/data/konglo_list.json` (12 groups, ~60 tickers). Owner families: Hartono (BBCA, BBHI, CBDK, BREN, etc.), Widjaja/Sinar Mas, Prajogo (BREN/TPIA/PTRO/CUAN), Bakrie, Salim, Lippo, etc.

## Rules
- **Leader-laggard rotation**: if the group's strongest ticker gaps up with volume while a laggard in the same group consolidates at support with smart money accumulating → laggard = high-probability catch-up trade.
- **Group distribution**: if 2+ names in the same group show distribution_setup on the same day → treat it as group-level exit, not a per-ticker noise event.
- **Cross-control caveat**: BREN is co-controlled (Hartono + Prajogo). Map it into BOTH groups; interpret flow only when both ecosystems align.
- **Size bonus**: a setup with confirmed konglo flow alignment earns +10 confluence points (see `confluence-scoring.md`).
- **Size cap**: never exceed one active position per konglo group. If already holding a peer, the new name substitutes — it does not stack.

## Red Flags
- Konglo name breaks out alone while peers lag → possible fake breakout, bandar using liquidity in one ticker to distribute another.
- Group previously rotating in suddenly rotates out for 3 consecutive sessions → demote all thesis in that group to `watch`.

## Examples
- Barito Grup PTRO crossing to CUAN (14 Mar) — M1.1 audit matrix lists this event; Konglo Mode would surface the group-level reading, not PTRO-only.
- Djarum ecosystem (BBCA, BBHI, CBDK, PBID) rotating simultaneously signals property/bank crossover.
```

#### Playbook changes

- **L1 `layer-1-global-context.md`** — "## What To Gather" → add:
  > - Konglo rotation: `python tools/trader/konglo_flow.py --all` → summary by group. Flag groups with `rotation_in`/`rotation_out` as today's themes.
- **L2 `layer-2-stock-screening.md`** — after criterion 6 (Volume confirmation), insert:
  > 7. **Konglo fit** — `konglo_loader.group_for(ticker)`. If ticker belongs to a group in today's L1 rotation-in list → +1 conviction bucket. If portfolio already holds a peer in same group → either substitute (if weaker peer exists) or skip.
- **L4 `layer-4-trade-plan.md`** — "## Inputs" → add:
  > - Konglo state: `tools/trader/data/konglo_list.json` + `group_flow_today(group_id)` for target ticker.
  And in "Trade Plan Format" add a `Konglo:` line under `Catalyst:`.

### Verify
- [ ] `python tools/trader/konglo_loader.py lookup BBCA` prints a dict with 12 groups visible overall.
- [ ] `python tools/trader/konglo_flow.py --group hh_djarum` returns a `verdict` string.
- [ ] L2 playbook references `konglo_loader.group_for`.
- [ ] `skills/trader/CLAUDE.md` Skills Index lists `konglo-ownership.md` under a new **Ownership & Flow** subsection.

### Commit
`[M3.1] Konglo mode: loader + flow + skill + L1/L2/L4 wiring`

---

## Phase M3.2 — Volume-Price State

### Goal
Classify every cycle as one of four Wyckoff volume-price states. Remove the habit of reading "up move" without asking "on what volume."

### Deliverables

#### Tool — `tools/trader/vp_analyzer.py`

Uses `api.get_candles`, `api.get_volume_ratio`, `api.get_avg_volume`.

```python
VPState = Literal["healthy_up","healthy_correction","weak_rally","distribution","indeterminate"]

def classify(ticker: str, timeframe: str = "1d") -> dict
# returns {"state": VPState, "price_delta_pct": float, "vol_ratio": float, "note": str}

def classify_series(ticker: str, days: int = 10) -> list[dict]
# per-day classifications for trend continuity
```

Rules (must be encoded exactly):
- price Δ ≥ +0.5% AND vol_ratio ≥ 1.0 → `healthy_up`
- price Δ ≤ -0.5% AND vol_ratio < 1.0 → `healthy_correction`
- price Δ ≥ +0.5% AND vol_ratio < 0.8 → `weak_rally`
- price Δ ≤ -0.5% AND vol_ratio ≥ 1.2 → `distribution`
- else → `indeterminate`

#### Skill — `skills/trader/volume-price-rules.md`

```markdown
# Volume-Price Rules (Wyckoff)

Every decision must check the 4-quadrant table before acting on price alone.

| Price | Volume | State | Bias | Action |
|-------|--------|-------|------|--------|
| UP | UP | healthy_up | BULLISH | Allow entry / hold |
| DOWN | DOWN | healthy_correction | BULLISH | Add-to-support permitted |
| UP | DOWN | weak_rally | CAUTION | No chase; reduce plan size |
| DOWN | UP | distribution | BEARISH | Cut on confirmation |

## Thresholds
- Baseline `vol_ratio` = 20-day average.
- `healthy_up` only counts if 2 of last 3 sessions were ≥ 1.0. A single spike ≠ trend.
- `distribution` is only actionable if paired with smart-money net selling (cross-check via `broker_profile.py`). Without the broker read, mark `watch` not `cut`.

## Integration
- L2 screening: drop any name whose 5-day composite is `weak_rally` or `distribution` unless spring or shakeout is simultaneously firing.
- L3 monitoring: run `vp_analyzer.classify` each 30-min cycle on 30m timeframe, append to signal trail.
- L4 sizing: `weak_rally` state caps risk_pct at 1% regardless of conviction.

## Anti-patterns
- Do NOT declare `healthy_up` on a gap-up day with thin vol_ratio. Gaps inflate the return but not the volume confirmation.
- Do NOT treat `distribution` as short signal — Indonesian market is long-only. Use it as exit/avoid.
```

#### Playbook changes

- **L2** — Screening Criteria section, add as new criterion 2.5:
  > 2.5. **Volume-price state** — `vp_analyzer.classify(ticker, '1d')`. Drop if `weak_rally` or `distribution` without offset signal.
- **L3** — "## What To Monitor" → "### Price & Volume", add one bullet:
  > - Every cycle: `vp_analyzer.classify(ticker, '30m')` → attach state to cycle log.

### Verify
- [ ] `python -c "import sys; sys.path.insert(0,'tools/trader'); from vp_analyzer import classify; print(classify('BBCA'))"` returns a dict with `state`.
- [ ] `skills/trader/volume-price-rules.md` added to L2/L3 skills-to-load.

### Commit
`[M3.2] Volume-price state classifier + 4-quadrant skill + L2/L3 wiring`

---

## Phase M3.3 — Spring Detection

### Goal
Identify engineered shakeouts below support where smart money is absorbing — the classic Wyckoff spring. This is a distinct setup type with its own sizing.

### Deliverables

#### Tool — `tools/trader/spring_detector.py`

Uses `api.get_support_resistance`, `api.get_price`, `api.analyze_bid_offer`, `broker_profile` smart-money classifier, `api.get_volume_ratio`.

```python
def detect(ticker: str) -> dict
# returns:
# {
#   "ticker": "...",
#   "is_spring": bool,
#   "support": float,
#   "last": float,
#   "pct_below": float,
#   "bid_offer_ratio": float,
#   "smart_money_bid_freq_ratio": float,   # smart:retail among recent bids
#   "volume_spike": bool,                  # vol_ratio >= 3× in breach window
#   "confidence": Literal["low","med","high"],
#   "notes": [str]
# }
```

Conditions (all must hold for `is_spring=True`):
- `last < support × 0.98`
- `bid_offer_ratio > 1.5` OR `thick_bid_near` from `analyze_bid_offer`
- Smart money net bid-count > retail in last 50 trades (`broker_profile`)
- `vol_ratio >= 1.5`

Confidence tiers:
- `high` — all 4 + vol_spike (≥3×)
- `med` — all 4, vol_ratio 1.5–3
- `low` — 3 of 4

#### Skill — `skills/trader/spring-setup.md`

```markdown
# Spring Setup (Wyckoff Phase C)

Engineered break below a published support where smart money absorbs retail panic. A spring is not "price fell then bounced" — it is "price was *made to fall* so weak hands would sell, and a known buyer was waiting."

## Detection (see `spring_detector.detect`)
1. Price breaks support by ≥2%.
2. Bid stack quality remains — thick near-bid or bid/offer ≥1.5.
3. Smart money net bidding in recent trades (broker_profile).
4. Volume ≥1.5× average in breach window.

## Entry
- Entry zone: support ±1 tick on first successful reclaim of support level.
- Stop: low of spring bar - 1 tick (or -2% if bar is narrow).
- Risk bucket: `med` conviction by default; `high` only if all 4 + vol_spike and the group has konglo alignment.

## Target
- T1 = pre-spring swing high (typical 1.5R–2R).
- T2 = next Wyckoff phase D breakout level (3R+).

## Failure Mode
If price closes below spring low with smart money flipping to net-sell → thesis invalid. Do not average down.

## Integration
- L2: spring firing adds +15 confluence; overrides a `weak_rally` VP state veto.
- L3: spring event triggers a `signal` of kind `spring` with severity based on confidence.
- L4: Mode B (sizing-only) is the default path for `high` confidence springs — tape already defines entry.
- L5: auto-trigger eligible (see `auto-trigger.md`).

## Example (from shared playbook)
> DEF support 5000. XYZ + ABC offer thin at 5000-5100, RF accumulates at 5000 with heavy volume, ABC breaks 4900 on weak vol, RF keeps bidding at 4900-5000 with volume. By afternoon price tembus 5000. Read: "Bos mulai beli di 5000."
```

#### Playbook changes

- **L2** — after the criteria list, add a **Spring override** block:
  > If `spring_detector.detect(ticker).is_spring and confidence in {"med","high"}`: criteria 2 (technical structure) is satisfied even if price closed below support. Promote to L4 instead of rejecting.
- **L3** — "### Manipulation Signals", replace the current `wick_shakeout` bullet's closing sentence with:
  > → if confirmed, call `spring_detector.detect(ticker)` to distinguish a pure wick from an actual spring.
  Add a new signal type in the "Output" schema: `spring`.
- **L4** — Mode B entry rule, add:
  > If arrived via `spring` signal → use spring entry rule from `skills/trader/spring-setup.md` (`## Entry`).

### Verify
- [ ] `python tools/trader/spring_detector.py BBCA` returns a dict with `is_spring` and `confidence`.
- [ ] L2 playbook shows spring override; L3 output schema has `spring` kind.
- [ ] `skills/trader/spring-setup.md` linked in `skills/trader/CLAUDE.md` under Layer 3 and Layer 4 sections.

### Commit
`[M3.3] Spring detector + skill + L2/L3/L4 integration`

---

## Phase M3.4 — Imposter Detection

### Goal
Catch smart money hiding inside retail broker codes. Without this, the broker-flow signal mis-classifies "retail" and distribution traps fire anyway.

### Deliverables

#### Tool — `tools/trader/imposter_detector.py`

Uses `api.get_running_trades` + broker classification from `api.classify_broker`.

```python
def score(ticker: str, window_trades: int = 200) -> dict
# returns:
# {
#   "ticker": "...",
#   "imposter_score": int,                 # -10..+10 (+ means likely retail-coded smart money)
#   "large_lot_retail_trades": int,        # retail code trades with lot >= 50_000
#   "same_second_retail_cluster": int,     # 2+ retail trades identical ts
#   "one_retail_selling_into_many_retail_buying": bool,
#   "flagged_codes": list[str],
#   "note": str
# }
```

Signals:
- Lot ≥ 50,000 by a retail code on a single trade → +3.
- Two retail codes trading at identical second → +2.
- All retail codes buying AND one retail code heavy selling → +4.
- Clean retail (no anomalies) → 0.
- Negative: if smart-money codes dominate but lots look like retail — rare, usually leave at 0.

#### Skill — `skills/trader/imposter-detection.md`

```markdown
# Imposter Detection

## Why
Smart money hides inside retail codes (XL, YP, CC, KK, PD, SQ, NI, AZ, CP) to avoid telegraphing intent. A naive broker-flow read will call it "retail FOMO" and flash a distribution warning — but the lot sizes and timing give it away.

## Red Flags (+imposter_score)
- Retail-coded lot ≥ 50K in one trade (retail rarely moves that size in one click).
- Multiple retail-coded trades at the exact same second (automated).
- Many retail buyers + ONE retail seller dumping large size → that seller may be the real operator offloading.

## How to Use
- L3 monitoring every cycle: call `imposter_detector.score(ticker)`.
- If `imposter_score ≥ +6` during what looks like "retail accumulation" → upgrade to `accumulation_setup` candidate.
- If `imposter_score ≥ +6` during a rally → downgrade to `distribution` suspect (the seller is the operator).

## Integration
- Adds ±10 to confluence score. See `confluence-scoring.md`.

## Limit
This is a heuristic, not proof. Never override a clear distribution_setup on imposter alone — require broker_profile + SID cross-check.
```

#### Playbook changes

- **L3** — under "### Manipulation Signals", add one bullet:
  > - `imposter_score >= +6` → annotate the cycle's output. Re-read broker flow assuming retail codes may be operator-controlled.
- **Skill** — expand `skills/trader/whale-retail-analysis.md` with a one-line reference pointing to `imposter-detection.md` (do not duplicate).

### Verify
- [ ] `python tools/trader/imposter_detector.py BBCA --trades 200` returns a dict with `imposter_score`.
- [ ] L3 playbook cites the skill; `skills/trader/CLAUDE.md` lists it under Layer 3 skills.

### Commit
`[M3.4] Imposter detector + skill + L3 wiring`

---

## Phase M3.5 — Tape Reading (9 Cases)

### Goal
Turn the 9-case tape-reading playbook into code + skill. Time-sensitive, drives L3 monitoring plus can auto-trigger execution.

### Deliverables

#### Tools — `tools/trader/tape/` package

Keep one module per case for auditability. Shared helpers in `tape/_lib.py`.

| File | Returns | Source data |
|------|---------|-------------|
| `tape/_lib.py` | `load_orderbook(ticker)`, `load_trade_book(ticker, lookback_sec)`, `load_running(ticker, limit)`, thresholds | `api.get_stockbit_orderbook`, `get_stockbit_running_trade`, `get_orderbook_delta` |
| `tape/case1_walls.py` | `detect_walls(ob) -> {'support':[prices], 'resistance':[prices], 'wall_lot':{price:lot}}` | order book |
| `tape/case2_eaten_vs_pulled.py` | `classify_wall_fate(ob_prev, ob_now, tb_delta) -> 'eaten'|'pulled'|'stable'` | ob diff + trade book delta |
| `tape/case3_offer_eaten_bullish.py` | `detect_bullish_absorption(ob_history, tb_history) -> {'is_absorbing':bool, 'levels':[...]}` | ob+tb series |
| `tape/case4_freq_lot.py` | `queue_nature(level) -> 'bandar'|'retail'|'mixed'` using lot/freq ratio (bandar = lot>=20k AND freq<=10) | order book |
| `tape/case5_ganjelan.py` | `detect_fake_queue(ob) -> {'fake_levels':[...], 'risk':'high'|'med'|'low'}` | order book |
| `tape/case6_healthy_markup.py` | `is_healthy_markup(ob_history, tb_history) -> bool` | offer→bid conversion confirmed by trade book |
| `tape/case7_crossing.py` | `detect_crossing(running, tb_delta, level) -> {'is_crossing':bool, 'seller':str, 'buyer':str, 'lot':int}` | running trade |
| `tape/case8_ideal_markup.py` | `is_ideal_markup(ob_history, tb_history) -> bool` | each offer eaten → bid thickens next level |
| `tape/case9_spam_lot.py` | `detect_spam(running, window_sec=60) -> {'is_spam':bool, 'haka':int, 'haki':int, 'note':str}` | running trade |

#### Tool — `tools/trader/tape_runner.py`

Orchestrator. CLI and library.

```python
@dataclass
class TapeState:
    ticker: str
    ts: str
    walls: dict
    wall_fate: str            # eaten|pulled|stable
    bullish_absorption: bool
    queue_nature: dict         # {price: 'bandar'|'retail'|'mixed'}
    fake_queue_risk: str       # high|med|low
    healthy_markup: bool
    ideal_markup: bool
    crossing: Optional[dict]
    spam: dict
    composite: Literal["ideal_markup","healthy_markup","spring_ready","fake_support","distribution_trap","crossing_flag","spam_warning","neutral"]
    confidence: Literal["low","med","high"]

def snapshot(ticker: str) -> TapeState
```

Composite rule (applied in order — first match wins):
1. `ideal_markup == True` AND `wall_fate == "eaten"` AND spam.is_spam == False → `ideal_markup`, high.
2. `healthy_markup == True` AND bullish_absorption AND fake_queue_risk != "high" → `healthy_markup`, med/high.
3. walls.support present AND wall_fate=="stable" AND queue is bandar AND spring_detector says `is_spring` → `spring_ready`, same confidence as spring.
4. walls.support present AND wall_fate=="eaten" AND trade book confirms heavy sell → `fake_support`, high.
5. crossing.is_crossing → `crossing_flag`, med.
6. spam.is_spam → `spam_warning`, med.
7. fake_queue_risk == "high" → `distribution_trap`, med.
8. else → `neutral`, low.

#### Skill — `skills/trader/tape-reading.md`

This file has real size — it is the reference card for the trader. Content:

```markdown
# Tape Reading — Order Book + Trade Book + Running Trade

**Use during L3 monitoring cycles.** Time-sensitive. For any ticker in `Superlist` status `Hold` or on today's shortlist, snapshot once per cycle via `tape_runner.snapshot(ticker)`.

## Glossary
- **HAKA** — Hajar Kanan; buyer hits the offer (offer eaten).
- **HAKI** — Hajar Kiri; seller hits the bid (bid eaten).
- **Freq** — number of distinct accounts queued at a price. Low = bandar-like; high = retail-like.
- **Lot** — queue size. Big lot + low freq = bandar. Small lot + high freq = retail.

## 9 Cases (Quick Reference)

| # | Pattern | Signal | Action |
|---|---------|--------|--------|
| 1 | Thick bid/offer at 1–2 prices | S/R defined | Entry near support, TP near resistance |
| 2 | Thick bid eaten (not pulled) on downtrend | Fake support | EXIT / avoid |
| 3 | Thick offer eaten (not pulled) on uptrend | Bullish absorption | Consider entry |
| 4 | Big lot + low freq at one level | Bandar queue | Wait — can be pulled |
| 5 | Repeated "thick" lots all ≤3 freq each | Ganjelan / fake queue | Distribution warning |
| 6 | Offer eaten → bid thickens next tick, repeat | Healthy markup | Positive bias, add permitted |
| 7 | Same-price crossing 100K+ lot in seconds | Cross-trade flag | Investigate broker code |
| 8 | Every offer eaten → bid rebuilt next tick up the ladder | Ideal markup | Strongest buy tape |
| 9 | Frequent HAKA 1-lot spam then HAKI big | Running-trade manipulation | EXIT fast |

## Case Detail

### Case 1 — Walls as S/R
Thick bid at one price = bandar defending support; thick offer = bandar capping. Useful for scalping entries and tighter stops. Validate with `case2_eaten_vs_pulled.classify_wall_fate` next cycle.

### Case 2 — Bid Thick But Eaten (Fake Support)
If a thick bid gets eaten in heavy HAKI, it was a tool for the operator to unload. Trade-book `buy_lot` at that price rises sharply confirms eaten (vs. pulled). Distribution read — exit any existing long.

### Case 3 — Offer Thick But Eaten (Bullish)
Opposite. Offer continually eaten, replaced with bid thickening below. Operator is willing to pay through a fake cap to scare retail out. Entry allowed.

### Case 4 — Freq/Lot Mismatch
Lot=242K at 5 freq is three traders with big books. Entry tactic: add-on near the wall if it has held one cycle. Stop: one tick below the wall (they can cancel, and when they do, price drops hard).

### Case 5 — Ganjelan
Multiple price levels each show a "thick" queue but each has ≤3 freq. That is one or two accounts faking depth. Cancel risk is high — expect a sharp drop once the show ends.

### Case 6 — Healthy Markup
Offer eaten → bid thickens at the next tick → offer above eaten → pattern repeats. Trade-book buy_lot grows at each level. Strong accumulation; good for adding.

### Case 7 — Crossing
Big same-price transaction between two counterparties repeatedly. Common Prajogo/Barito crossings (DP↔NI). Not tradeable — investigate broker codes via `case7_crossing.detect_crossing` and pause judgement until the source is known.

### Case 8 — Ideal Markup
Stepwise: each offer fully eaten, bid immediately restacked at the same or higher level. Continues up the ladder. Enter on pullback to the last restacked bid. Stop: one tick under the last restack that held.

### Case 9 — Spam Lot
Running trade floods with 1-lot HAKA to create FOMO; seconds later a large HAKI prints. Price falls; retail sells into the hole. Treat any spam pattern as immediate exit signal for tight-stop positions.

## Integration
- L3 every cycle: `tape_runner.snapshot(ticker)` for each hold + shortlist. Log `composite` + `confidence` to monitoring trail. Push `signal` row when composite changes vs previous cycle.
- Confluence: composite maps to +/- points (see `confluence-scoring.md`).
- Auto-trigger: `ideal_markup` or `spring_ready` with `confidence="high"` eligible — see `auto-trigger.md`.
- Exit: `fake_support` or `distribution_trap` with `confidence="high"` on a hold → immediate `exit-candidate` flag in `vault/data/thesis-actions.json` and `layer3` telegram.

## Anti-patterns
- Do NOT act on one cycle alone for ambiguous composites (`neutral`, `crossing_flag`). Wait for confirmation.
- Do NOT chase into `spam_warning` even if price is moving up.
- Do NOT interpret crossing as bullish or bearish without broker-code resolution.
```

#### Playbook changes

- **L3** — "## Tools" add:
  > | Tape reading | `tools/trader/tape_runner.py` (snapshot per cycle) |
- **L3** — "## What To Monitor" → add a new top-level bullet:
  > ### Tape State (every cycle)
  > Call `tape_runner.snapshot(ticker)` for each actively monitored name. Append `composite` + `confidence` + `wall_fate` to the monitoring log. Promote to Airtable Insights on any state change to a `fake_support`, `distribution_trap`, `ideal_markup`, `healthy_markup`, or `spring_ready`.
- **L3** — Output schema: add a `tape_state` field to every per-ticker block.

### Verify
- [ ] `python tools/trader/tape_runner.py BBCA` returns a full `TapeState` as JSON.
- [ ] Each case module has a standalone CLI that prints its output for a given ticker.
- [ ] L3 playbook references `tape_runner.snapshot` in "## What To Monitor" and "## Tools".
- [ ] `skills/trader/tape-reading.md` appears in `skills/trader/CLAUDE.md` Layer 3 section.

### Commit
`[M3.5] Tape reading — 9 case modules + runner + skill + L3 wiring`

---

## Phase M3.6 — Confluence Scoring

### Goal
Collapse all per-dim signals into a single 0–100 score. Playbooks and auto-trigger decide on one number, not a spray.

### Deliverables

#### Tool — `tools/trader/confluence_score.py`

```python
def score(ticker: str) -> dict
# returns:
# {
#   "ticker": "...",
#   "ts": "...",
#   "components": {
#     "narrative_fit":  0..10,     # from L1 themes active today
#     "technical":      0..15,     # trend + structure + RS
#     "broker_flow":   -15..+15,   # smart vs retail net
#     "sid":           -10..+10,   # trend direction
#     "vp_state":      -10..+10,   # volume-price classifier
#     "orderbook":     -10..+10,   # bid stack quality from case1/6/8
#     "imposter":      -10..+10,
#     "wyckoff_phase":   0..10,    # A=2, B=5, C=8, D=10
#     "spring_bonus":    0..15,    # only if is_spring
#     "konglo_bonus":    0..10
#   },
#   "score": int,   # 0..100 mapped + clamped
#   "bucket": "reject"|"watch"|"plan"|"execute",
#   "reasons": [str]
# }
```

Bucket thresholds:
- `score < 40` → reject
- `40–59` → watch
- `60–79` → plan (L4 eligible)
- `80+` → execute (auto-trigger eligible if other gates pass)

#### Skill — `skills/trader/confluence-scoring.md`

```markdown
# Confluence Scoring

One score, one decision. Every L2/L3 cycle computes it for every candidate.

## Components & Weights
| Component | Range | Source |
|-----------|-------|--------|
| Narrative fit | 0..10 | L1 themes + konglo_flow |
| Technical | 0..15 | structure + RS + trend |
| Broker flow | -15..+15 | broker_profile net |
| SID | -10..+10 | sid_tracker trend |
| VP state | -10..+10 | vp_analyzer.classify |
| Orderbook | -10..+10 | tape_runner case1/6/8 |
| Imposter | -10..+10 | imposter_detector.score |
| Wyckoff phase | 0..10 | wyckoff.py classifier |
| Spring bonus | 0..15 | spring_detector.confidence |
| Konglo bonus | 0..10 | konglo_flow alignment |

Sum, clamp to 0..100.

## Buckets
- < 40 — reject. Log rejection reason.
- 40–59 — watch. Keep on monitoring list; no plan yet.
- 60–79 — plan. Promote to L4.
- 80+ — execute. Eligible for inline execution if other gates pass.

## When To Call
- L2: compute for each shortlisted ticker. Only promote `plan`+ to L4.
- L3: recompute every cycle; if score transitions up a bucket → telegram + signal row.
- L4: attach score to every tradeplan as `conviction_score`.
- L5: pre-entry, require score ≥ 60. Execute inline only if score ≥ 80.

## Anti-game
Do not inflate components to hit a threshold. Each must have its own data source firing, not narrative reasoning.
```

#### Playbook changes

- **L2** — final gate line replaces the "5/5 criteria" rule:
  > Compute `confluence_score.score(ticker)`. Only names with bucket `plan` or `execute` advance.
- **L3** — per-cycle output adds `confluence_score` + `bucket` per tracked name.
- **L4** — plan format adds `Confluence: <score>/<bucket>`.
- **L5** — execution gate: `score ≥ 60` required; inline if `score ≥ 80`.

### Verify
- [ ] `python tools/trader/confluence_score.py BBCA` prints full dict with `score` and `bucket`.
- [ ] L2/L3/L4/L5 playbooks reference the score.

### Commit
`[M3.6] Confluence score + skill + L2-L5 gating`

---

## Phase M3.7 — Auto-Trigger (Cost-Guarded)

### Goal
When tape + confluence + spring all light up on high conviction, auto-invoke Claude (via `claude --settings monitoring.openclaude.json`) to think about the signal and, if approved, run L4 + L5. Strict dedup and daily budget.

### Deliverables

#### Tool — `tools/trader/auto_trigger.py`

```python
# Exit codes: 0 = triggered; 1 = deduped; 2 = over budget; 3 = gate failed

def should_trigger(ticker: str, signal_kind: str) -> tuple[bool, str]
# Checks: confluence >= 80, tape composite in {ideal_markup, spring_ready, healthy_markup} high confidence,
# DD < 5%, posture >= 2, NOT in kill switch,
# redis key signal:triggered:{ticker}:{signal_kind} not present,
# daily budget: counter autogen:YYYY-MM-DD < 5

def trigger(ticker: str, signal_kind: str, context: dict) -> dict
# 1. Telegram first: 'auto_trigger_detected' with context
# 2. Set redis dedup key (TTL 3600)
# 3. Increment daily budget counter
# 4. Exec with fallback pattern (mirror cron-dispatcher.sh commit 474f117):
#    try: claude --dangerously-skip-permissions --bare --settings .claude/settings.openclaude.json -p "<prompt>"
#    on non-zero exit: log warning, retry without --settings
#    Prompt must name the ticker, signal, confluence breakdown, and explicitly say "Decide to proceed with L4+L5 or skip. Telegram-first."
# 5. Log the invocation to vault/data/auto_trigger_log.jsonl
```

All side effects (telegram, redis, fork) go through existing clients; no new env vars.

#### Skill — `skills/trader/auto-trigger.md`

```markdown
# Auto-Trigger

## Purpose
High-conviction tape signals are time-sensitive. Let the monitoring cron auto-invoke Claude when the signal beats every gate — without letting costs run away.

## Gates (all must pass)
- `confluence_score.bucket == "execute"` (score ≥ 80)
- `tape_runner.snapshot(...).composite in {"ideal_markup","spring_ready","healthy_markup"}` with `confidence == "high"`
- Portfolio: DD < 5%, posture ≥ 2, kill switch inactive
- Dedup: no trigger fired for this `{ticker, signal_kind}` in the last 60 minutes
- Budget: fewer than 5 auto-triggers fired today

Any gate fails → telegram only (`signal-notify` with context), NO Claude invocation.

## Prompt Contract
The auto-trigger prompt always asks Claude to:
1. Re-read today's L1 posture + L0 state.
2. Verify the tape + confluence evidence at the invocation time.
3. Decide: proceed to L4+L5, or abort. State the reason.
4. Telegram-first before any order.

## Logging
Every trigger writes to `vault/data/auto_trigger_log.jsonl`:
```
{"ts":"...","ticker":"...","kind":"spring|ideal_markup|healthy_markup","confluence":85,"outcome":"fired|deduped|budget|gate_failed"}
```

## Tuning
- Confluence threshold (80) and budget (5) live in `tools/trader/auto_trigger.py`. Adjust only via commit — no env flag.
- Increase budget only after reviewing the log shows all prior triggers were worthwhile.

## Anti-pattern
- Never call `auto_trigger.trigger` from anywhere except the monitoring runtime. No inline scripts, no REPL shortcuts.
- Never skip the telegram step, even when firing Claude.
```

#### Integration

- **Edit** `/home/lazywork/workspace/tools/trader/runtime_monitoring.py`: at the end of each per-ticker cycle, call `auto_trigger.should_trigger(ticker, composite)` then `auto_trigger.trigger(...)` if true.
- **Edit** `/home/lazywork/workspace/skills/trader/execution.md` "## Confidence Gate (Inline Execution from L2–L4)". Add a row:
  > | Auto-Trigger | Only from `tools/trader/auto_trigger.py` gate success | confluence ≥ 80 + tape high + budget OK |
- **Edit** `/home/lazywork/workspace/skills/trader/telegram-notify.md` — add a subcommand `auto_trigger_detected` that posts: ticker, confluence, tape composite, reason for firing.

### Verify
- [ ] `python tools/trader/auto_trigger.py --dry-run BBCA ideal_markup` logs gates without invoking Claude.
- [ ] Running twice within 60 min prints `deduped`.
- [ ] Injecting 5 fake triggers in the counter key returns `over budget`.
- [ ] Telegram notifier has the `auto_trigger_detected` subcommand.

### Commit
`[M3.7] Auto-trigger with dedup + daily budget + telegram-first`

---

## Phase M3.8 — Dashboard & DB Extensions (depends on M2.2+)

### Goal
Schema + UI surfaces for M3 artifacts.

### Migrations (append to `backend/migrations/`)

#### `0006_konglo.sql`

```sql
CREATE TABLE konglo_group (
  id             TEXT PRIMARY KEY,
  name           TEXT NOT NULL,
  owner          TEXT NOT NULL,
  market_power   TEXT,
  sectors        TEXT
);
CREATE TABLE konglo_ticker (
  ticker         TEXT NOT NULL,
  group_id       TEXT NOT NULL,
  category       TEXT,
  notes          TEXT,
  PRIMARY KEY (ticker, group_id)
);
```

#### `0007_strategy_signals.sql`

```sql
CREATE TABLE tape_state (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ts             TEXT NOT NULL,
  ticker         TEXT NOT NULL,
  composite      TEXT NOT NULL,
  confidence     TEXT NOT NULL,
  wall_fate      TEXT,
  payload_json   TEXT NOT NULL
);
CREATE INDEX ix_tape_ticker_ts ON tape_state(ticker, ts);

CREATE TABLE confluence_score (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ts             TEXT NOT NULL,
  ticker         TEXT NOT NULL,
  score          INTEGER NOT NULL,
  bucket         TEXT NOT NULL,
  components_json TEXT NOT NULL
);
CREATE INDEX ix_confluence_ticker_ts ON confluence_score(ticker, ts);

CREATE TABLE auto_trigger_log (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ts             TEXT NOT NULL,
  ticker         TEXT NOT NULL,
  kind           TEXT NOT NULL,
  confluence     INTEGER,
  outcome        TEXT NOT NULL,
  reason         TEXT
);
```

### API additions

| Path | Methods | Notes |
|------|---------|-------|
| `/api/v1/konglo/groups` | GET list | all groups |
| `/api/v1/konglo/tickers/{ticker}` | GET | group membership |
| `/api/v1/tape-states` | GET list (filter: ticker, since, composite), POST | |
| `/api/v1/confluence` | GET list (filter: ticker, bucket, since), POST | |
| `/api/v1/auto-triggers` | GET list (filter: date, outcome), POST | |

### Dashboard pages

- **`/tape`** — live tape feed (SSE from signal stream filtered to `kind ∈ tape_*`). Columns: ticker, composite, confidence, wall_fate, last-seen.
- **`/konglo`** — groups with member tickers, today's group return + volume z, highlight rotation in/out.
- **`/confluence`** — latest score per ticker with bucket badge, click → drill to components bar chart.
- Extend **`/ticker/[ticker]`**: add tabs **Tape** (history of composites) and **Konglo** (group membership + peers).

### Python client additions (`tools/fund_api.py`)

- `post_tape_state`, `get_tape_history`
- `post_confluence`, `get_confluence_latest`
- `post_auto_trigger_log`
- `get_konglo_group(ticker)`

### Verify
- [ ] Three new tables exist after migration.
- [ ] Each new endpoint returns 200 for a valid request.
- [ ] `/tape`, `/konglo`, `/confluence` render with seeded data.
- [ ] Ticker drill shows Tape + Konglo tabs.

### Commit
`[M3.8] Dashboard + DB for konglo/tape/confluence/auto-trigger`

---

## Mission 3 Complete When

- [ ] All seven prefixes (`konglo_*`, `vp_*`, `spring_*`, `imposter_*`, `tape_*`, `confluence_*`, `auto_trigger`) exist as scripts under `tools/trader/`.
- [ ] Seven new skills appear in `skills/trader/` and are indexed in `skills/trader/CLAUDE.md` — grouped under a new **Ownership & Flow** subsection (konglo), **Tape & Microstructure** subsection (tape, spring, imposter), and **Scoring** subsection (vp, confluence, auto-trigger).
- [ ] L1/L2/L3/L4/L5 playbooks each reference at least one new tool and one new skill introduced in M3, with each reference marked to its phase (e.g., `<!-- M3.3 -->`).
- [ ] Auto-trigger dry-run works; dedup + budget logic tested.
- [ ] Dashboard surfaces all four strategy-specific views.
- [ ] One full cycle of `runtime_monitoring.py` writes: tape_state rows, confluence rows, no auto-trigger invocation (budget intact, thresholds tuned conservatively on day 1).

**Only then**: raise the auto-trigger budget, never before.
