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

## Tools
- `konglo_loader.group_for(ticker)` — group membership + owner
- `konglo_loader.peer_tickers(ticker)` — sibling tickers in same group
- `konglo_flow.group_flow_today(group_id)` — today's rotation verdict per group
- CLI: `python tools/trader/konglo_flow.py --all` (L1 morning run), `--group <id>` (per group)
