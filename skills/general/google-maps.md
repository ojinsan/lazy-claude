# Google Maps

## Purpose
Search places, get directions, geocode addresses, and plan trips using Google Maps tooling.

## Primary Tooling
- Manual: `~/workspace/tools/manual/google.md`
- Script: `~/workspace/tools/general/scripts/google_maps.py`

## Usage Path
Read `tools/manual/google.md` first for auth and Google setup. Then use `google_maps.py` for map queries.

## Common Calls
```bash
python3 ~/workspace/tools/general/scripts/google_maps.py search --query "coffee near Sudirman"
python3 ~/workspace/tools/general/scripts/google_maps.py directions --origin "Jakarta" --destination "Bandung"
```

## When to use
- trip planning
- location research
- route and distance checks
- place discovery

## Safety
- read-only map and route queries are safe
- no booking or purchases involved
