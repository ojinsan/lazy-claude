"""
Lazywork MCP Server
====================
Exposes workspace tools over streamable HTTP so any Claude on the Tailscale network
can call them as native MCP tools.

Transport: streamable-http  →  http://lazywork-mbp.tailc83490.ts.net:8765/mcp
Auth: Tailscale handles network auth — no token needed.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

WORKSPACE = Path('/home/lazywork/workspace')
TRADER_DIR = WORKSPACE / 'tools/trader'
THREADS_SCRIPT  = WORKSPACE / 'tools/general/playwright/threads-scraper.js'
FACEBOOK_SCRIPT = WORKSPACE / 'tools/general/playwright/facebook-scraper.js'
GOOGLE_SCRIPT   = WORKSPACE / 'tools/general/scripts/google_workspace.py'
RUNTIME = WORKSPACE / 'runtime'
MONITORING_DIR = RUNTIME / 'monitoring'
LOG_DIR = RUNTIME / 'logs'
WATCHLIST_FILE = RUNTIME / 'watchlists/active.json'

# Trader scripts need system python (has requests, httpx, etc.)
SYSTEM_PYTHON = '/usr/bin/python3'
# Google scripts need gsheets venv (has google-api-python-client)
GOOGLE_PYTHON = '/home/lazywork/workspace/.venv-gsheets/bin/python3'

# Shared env for trader subprocess calls — never embed paths into script strings
_TRADER_ENV = {**os.environ, 'TRADER_DIR': str(TRADER_DIR), 'PYTHONPATH': str(WORKSPACE / 'tools')}

mcp = FastMCP(
    "lazytools",
    instructions="Tools running on lazywork-mbp. Threads/Facebook scraping, trading screener, stockbit data, broker profile, SID tracker, Wyckoff, market structure, trade plan, journal, macro, layer2 screening, alerts, monitoring, logs. Stockbit screener: run preset templates or custom filters (stockbit_run_template, stockbit_run_custom_screener, stockbit_screener_templates, stockbit_screener_presets, stockbit_screener_metrics). Stockbit emitten info + native watchlists. Carina broker: cash balance, position detail, orders list, cancel order, amend order. Google: Calendar (list/create/update/delete), Sheets (read/write/append), Drive (search/list).",
    host="0.0.0.0",
    port=8765,
    stateless_http=True,  # No session state — each request is independent, survives server restarts
)


# ─── Threads ─────────────────────────────────────────────────────────────────

@mcp.tool()
def threads_search(query: str, limit: int = 10) -> str:
    """
    Search Threads posts by keyword using the logged-in Firefox profile.
    Returns post text plus top reply snippets.
    """
    result = subprocess.run(
        ['node', str(THREADS_SCRIPT), '--query', query, '--limit', str(limit), '--comments'],
        capture_output=True, text=True, timeout=240
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    try:
        data = json.loads(result.stdout)
        posts = data.get('results', [])
        lines = [f"Query: {query} ({len(posts)} results)\n"]
        for p in posts:
            text = p.get('text', '').strip()
            comments = [c for c in p.get('comments', []) if c.get('text')]
            if not text and not comments:
                continue

            lines.append('---')
            if text:
                lines.append(text[:400])
            if p.get('views'):
                lines.append(f"Views: {p.get('views')}")
            if p.get('url'):
                lines.append(f"URL: {p.get('url')}")
            if comments:
                lines.append('Replies:')
                for c in comments[:4]:
                    author = c.get('author') or 'unknown'
                    tags = []
                    if c.get('byAuthor'):
                        tags.append('author')
                    elif c.get('isThreadStarter'):
                        tags.append('starter')
                    tag_text = f" ({', '.join(tags)})" if tags else ''
                    lines.append(f"- @{author}{tag_text}: {c.get('text', '')[:220]}")
        return '\n'.join(lines)
    except Exception as e:
        raise RuntimeError(f"Parse error: {e}\nRaw: {result.stdout[:300]}")


# ─── Facebook ────────────────────────────────────────────────────────────────

@mcp.tool()
def facebook_marketplace_search(query: str, location: str = 'jakarta', limit: int = 20, detail: bool = False) -> str:
    """
    Search Facebook Marketplace listings by keyword.
    Returns title, price, location, and URL per listing.
    Set detail=True to also fetch description from each listing page (slower).
    """
    cmd = [
        'node', str(FACEBOOK_SCRIPT),
        '--query', query,
        '--mode', 'marketplace',
        '--location', location,
        '--limit', str(limit),
    ]
    if detail:
        cmd.append('--detail')

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    try:
        data = json.loads(result.stdout)
        listings = data.get('results', [])
        lines = [f"Marketplace: {query} @ {location} ({len(listings)} listings)\n"]
        for item in listings:
            lines.append(
                f"---\n{item.get('title','')}\n"
                f"Price: {item.get('price','')}\n"
                f"Location: {item.get('location','')}\n"
                f"URL: {item.get('url','')}"
            )
            if item.get('description'):
                lines.append(f"Desc: {item['description'][:300]}")
        return '\n'.join(lines)
    except Exception as e:
        raise RuntimeError(f"Parse error: {e}\nRaw: {result.stdout[:300]}")


@mcp.tool()
def facebook_search(query: str, limit: int = 15) -> str:
    """
    Search Facebook public posts by keyword.
    Returns post text, author, timestamp, and engagement counts.
    """
    result = subprocess.run(
        [
            'node', str(FACEBOOK_SCRIPT),
            '--query', query,
            '--mode', 'search',
            '--limit', str(limit),
        ],
        capture_output=True, text=True, timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    try:
        data = json.loads(result.stdout)
        posts = data.get('results', [])
        lines = [f"Facebook search: {query} ({len(posts)} posts)\n"]
        for p in posts:
            text = p.get('text', '').strip()
            if text:
                lines.append(
                    f"---\n{text[:500]}\n"
                    f"Author: {p.get('author','')} | {p.get('timestamp','')}\n"
                    f"Reactions: {p.get('reactions','')} | Comments: {p.get('comments','')}"
                )
        return '\n'.join(lines)
    except Exception as e:
        raise RuntimeError(f"Parse error: {e}\nRaw: {result.stdout[:300]}")


# ─── Trader — Screener ───────────────────────────────────────────────────────

@mcp.tool()
def run_screener(tickers: str = '', layer1_only: bool = False, deep_ticker: str = '') -> str:
    """
    Run the Lazyboy stock screener.
    - tickers: space-separated list e.g. 'VKTR ESSA' (empty = full watchlist scan)
    - layer1_only: only run macro + sector rotation layer
    - deep_ticker: single ticker for deep dive (includes SID, slow)
    """
    cmd = [SYSTEM_PYTHON, 'screener.py']
    if tickers:
        cmd += ['--tickers'] + tickers.split()
    if layer1_only:
        cmd.append('--layer1')
    if deep_ticker:
        cmd += ['--deep', deep_ticker]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300,
        cwd=str(TRADER_DIR), env=_TRADER_ENV
    )
    out = result.stdout + result.stderr
    return out[-4000:] if len(out) > 4000 else out


# ─── Trader — Layer 1 Context ─────────────────────────────────────────────────

@mcp.tool()
def run_layer1_context() -> str:
    """
    Fetch macro context: IHSG regime, sector rotation, active theses, Threads sentiment.
    Takes 1-2 min. Returns the full Layer 1 narrative.
    """
    result = subprocess.run(
        [SYSTEM_PYTHON, 'runtime_layer1_context.py'],
        capture_output=True, text=True, timeout=180,
        cwd=str(TRADER_DIR), env=_TRADER_ENV
    )
    out = result.stdout + result.stderr
    return out[-4000:] if len(out) > 4000 else out


# ─── Trader — Watchlist ───────────────────────────────────────────────────────

@mcp.tool()
def get_watchlist() -> str:
    """
    Return the current active watchlist (4-group structure: momentum, accumulation, speculative, avoid).
    """
    script = """
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    result = api.get_watchlist()
    print(json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print(json.dumps({"error": str(e)}))
"""
    result = subprocess.run(
        [SYSTEM_PYTHON, '-c', script],
        capture_output=True, text=True, timeout=15,
        env=_TRADER_ENV
    )
    if not result.stdout:
        raise RuntimeError(result.stderr[:500])
    return result.stdout[:3000]


# ─── Trader — Monitoring Status ───────────────────────────────────────────────

@mcp.tool()
def get_monitoring_status() -> str:
    """
    Return latest monitoring state: active alerts, orderbook snapshots, recent notes.
    """
    lines = []

    # Orderbook state files
    ob_dir = MONITORING_DIR / 'orderbook_state'
    if ob_dir.exists():
        files = sorted(ob_dir.glob('*.json'), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        if files:
            lines.append("=== Recent Orderbook State ===")
            for f in files:
                try:
                    d = json.loads(f.read_text())
                    lines.append(f"{f.stem}: {json.dumps(d, ensure_ascii=False)[:200]}")
                except Exception:
                    lines.append(f"{f.stem}: (unreadable)")

    # Notes
    notes_dir = MONITORING_DIR / 'notes'
    if notes_dir.exists():
        note_files = sorted(notes_dir.rglob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)[:3]
        if note_files:
            lines.append("\n=== Recent Notes ===")
            for f in note_files:
                lines.append(f"\n--- {f.name} ---\n{f.read_text()[:500]}")

    return '\n'.join(lines) if lines else "No monitoring data found."


# ─── Trader — Stockbit Data ───────────────────────────────────────────────────

@mcp.tool()
def get_stockbit_data(sid: str) -> str:
    """
    Fetch live orderbook and broker flow for a stock ticker (e.g. 'VKTR', 'ESSA').
    Calls Stockbit API directly via the backend proxy.
    """
    script = """
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env
load_env()
import api

sid = os.environ['SID']
results = {}

try:
    ob = api.get_stockbit_orderbook(sid)
    results['orderbook'] = ob
except Exception as e:
    results['orderbook_error'] = str(e)

try:
    bf = api.get_stockbit_broker_info(sid)
    results['broker_flow'] = bf
except Exception as e:
    results['broker_flow_error'] = str(e)

print(json.dumps(results, ensure_ascii=False, indent=2))
"""
    result = subprocess.run(
        [SYSTEM_PYTHON, '-c', script],
        capture_output=True, text=True, timeout=30,
        env={**_TRADER_ENV, 'SID': sid.upper()}
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout[:3000]


# ─── Trader — Broker Profile ─────────────────────────────────────────────────

@mcp.tool()
def get_broker_profile(ticker: str) -> str:
    """
    Analyze broker player composition for a ticker.
    Returns accumulation/distribution signals, dominant players, and net flow summary.
    """
    script = """
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
from broker_profile import analyze_players
try:
    result = analyze_players(os.environ['TICKER'])
    print(json.dumps(result.__dict__ if hasattr(result, '__dict__') else result, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
"""
    result = subprocess.run(
        [SYSTEM_PYTHON, '-c', script],
        capture_output=True, text=True, timeout=60,
        env={**_TRADER_ENV, 'TICKER': ticker.upper()}
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout[:4000]


# ─── Trader — SID Tracker ─────────────────────────────────────────────────────

@mcp.tool()
def get_sid_trend(ticker: str) -> str:
    """
    Return SID (Smart/Institutional Demand) trend for a ticker.
    Shows buy/sell accumulation pattern over recent sessions.
    """
    script = """
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
from sid_tracker import get_sid_trend
try:
    result = get_sid_trend(os.environ['TICKER'])
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
"""
    result = subprocess.run(
        [SYSTEM_PYTHON, '-c', script],
        capture_output=True, text=True, timeout=30,
        env={**_TRADER_ENV, 'TICKER': ticker.upper()}
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout[:3000]


# ─── Trader — Market Structure ────────────────────────────────────────────────

@mcp.tool()
def get_market_structure(ticker: str, days: int = 30) -> str:
    """
    Analyze market structure (swing highs/lows, trend phase, BOS/CHoCH) for a ticker.
    """
    script = """
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
from market_structure import get_structure
try:
    result = get_structure(os.environ['TICKER'])
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
"""
    result = subprocess.run(
        [SYSTEM_PYTHON, '-c', script],
        capture_output=True, text=True, timeout=30,
        env={**_TRADER_ENV, 'TICKER': ticker.upper()}
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout[:3000]


# ─── Trader — Wyckoff ─────────────────────────────────────────────────────────

@mcp.tool()
def run_wyckoff(ticker: str) -> str:
    """
    Run Wyckoff phase analysis for a ticker.
    Returns phase (accumulation/distribution/markup/markdown), cause, and key levels.
    """
    result = subprocess.run(
        [SYSTEM_PYTHON, 'wyckoff.py', ticker.upper()],
        capture_output=True, text=True, timeout=60,
        cwd=str(TRADER_DIR), env=_TRADER_ENV
    )
    out = result.stdout + result.stderr
    return out[-3000:] if len(out) > 3000 else out


# ─── Trader — Trade Plan ─────────────────────────────────────────────────────

@mcp.tool()
def run_tradeplan(ticker: str, entry: float = 0.0, cl: float = 0.0, tp: float = 0.0, portfolio: float = 0.0, risk: float = 0.0) -> str:
    """
    Generate a risk-sized trade plan for a ticker.
    - ticker: stock symbol e.g. 'VKTR'
    - entry: entry price (0 = use current price)
    - cl: cut loss price
    - tp: take profit price
    - portfolio: portfolio size in IDR (0 = use default)
    - risk: risk per trade % (0 = use default)
    """
    cmd = [SYSTEM_PYTHON, 'tradeplan.py', ticker.upper()]
    if entry:
        cmd += ['--entry', str(entry)]
    if cl:
        cmd += ['--cl', str(cl)]
    if tp:
        cmd += ['--tp', str(tp)]
    if portfolio:
        cmd += ['--portfolio', str(portfolio)]
    if risk:
        cmd += ['--risk', str(risk)]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30,
        cwd=str(TRADER_DIR), env=_TRADER_ENV
    )
    out = result.stdout + result.stderr
    return out[-3000:] if len(out) > 3000 else out


# ─── Trader — Journal ────────────────────────────────────────────────────────

@mcp.tool()
def get_journal(ticker: str = '', limit: int = 20) -> str:
    """
    Return trading journal entries: open positions, trade history, and lessons.
    - ticker: filter by ticker (empty = all)
    - limit: max trade history entries
    """
    script = """
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
from journal import get_open_positions, get_trade_history

ticker = os.environ.get('TICKER', '')
limit = int(os.environ.get('LIMIT', '20'))

out = {}
try:
    out['open_positions'] = get_open_positions()
except Exception as e:
    out['open_positions_error'] = str(e)
try:
    out['trade_history'] = get_trade_history(ticker or None, limit)
except Exception as e:
    out['trade_history_error'] = str(e)

print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
"""
    result = subprocess.run(
        [SYSTEM_PYTHON, '-c', script],
        capture_output=True, text=True, timeout=15,
        env={**_TRADER_ENV, 'TICKER': ticker.upper(), 'LIMIT': str(limit)}
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout[:4000]


# ─── Trader — Macro ──────────────────────────────────────────────────────────

@mcp.tool()
def get_macro() -> str:
    """
    Return current macro state: last market regime, active sector theses.
    """
    script = """
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
from macro import get_last_regime, get_active_theses

out = {}
try:
    regime = get_last_regime()
    out['regime'] = regime.__dict__ if hasattr(regime, '__dict__') else regime
except Exception as e:
    out['regime_error'] = str(e)
try:
    theses = get_active_theses()
    out['active_theses'] = [t.__dict__ if hasattr(t, '__dict__') else t for t in theses]
except Exception as e:
    out['theses_error'] = str(e)

print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
"""
    result = subprocess.run(
        [SYSTEM_PYTHON, '-c', script],
        capture_output=True, text=True, timeout=15,
        env=_TRADER_ENV
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout[:3000]


# ─── Trader — Layer 2 Screening ──────────────────────────────────────────────

@mcp.tool()
def run_layer2_screening() -> str:
    """
    Run Layer 2 screening: technical + broker flow scan across watchlist.
    Identifies tickers with confirmed structure + institutional accumulation.
    Takes ~1 min.
    """
    result = subprocess.run(
        [SYSTEM_PYTHON, 'runtime_layer2_screening.py'],
        capture_output=True, text=True, timeout=120,
        cwd=str(TRADER_DIR), env=_TRADER_ENV
    )
    out = result.stdout + result.stderr
    return out[-4000:] if len(out) > 4000 else out


# ─── Alerts ──────────────────────────────────────────────────────────────────

@mcp.tool()
def read_alerts() -> str:
    """
    Read unread alerts from the monitoring queue.
    Returns pending alert messages and marks them as read.
    """
    result = subprocess.run(
        [SYSTEM_PYTHON, 'read_alerts.py'],
        capture_output=True, text=True, timeout=10,
        cwd=str(TRADER_DIR), env=_TRADER_ENV
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout or "NO_ALERTS"


# ─── Logs ────────────────────────────────────────────────────────────────────

@mcp.tool()
def read_runtime_log(log_name: str = 'intraday-10m', lines: int = 50) -> str:
    """
    Read recent lines from a runtime log.
    Available logs: intraday-10m, heartbeat-30m, eod-publish, morning-prep, running-trade-poller.
    """
    log_file = LOG_DIR / f'{log_name}.log'
    if not log_file.exists():
        available = [f.stem for f in LOG_DIR.glob('*.log')]
        raise RuntimeError(f"Log '{log_name}' not found. Available: {available}")
    content = log_file.read_text().splitlines()
    return '\n'.join(content[-lines:])


# ─── Google — helpers ────────────────────────────────────────────────────────

def _gws(*args) -> str:
    """Call google_workspace.py with given args, return stdout or raise."""
    result = subprocess.run(
        [GOOGLE_PYTHON, str(GOOGLE_SCRIPT)] + list(args),
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        # google_workspace.py outputs {"ok": false, "error": "..."} on failure
        if result.stdout.strip():
            return result.stdout[:4000]
        raise RuntimeError(result.stderr.strip()[:500] or "google_workspace.py exited non-zero")
    return result.stdout[:4000]


# ─── Google — Calendar ───────────────────────────────────────────────────────

@mcp.tool()
def google_calendar_list(days: int = 7, calendar_id: str = 'primary') -> str:
    """List upcoming Google Calendar events. Default: next 7 days, primary calendar."""
    return _gws('calendar', 'list', '--days', str(days), '--calendar-id', calendar_id)


@mcp.tool()
def google_calendar_create(title: str, start: str, end: str, description: str = '', calendar_id: str = 'primary') -> str:
    """
    Create a Google Calendar event.
    - start/end: ISO 8601 datetime e.g. '2026-04-12T10:00:00+07:00'
    """
    args = ['calendar', 'create', '--title', title, '--start', start, '--end', end, '--calendar-id', calendar_id]
    if description:
        args += ['--description', description]
    return _gws(*args)


@mcp.tool()
def google_calendar_update(event_id: str, title: str = '', start: str = '', end: str = '', description: str = '', calendar_id: str = 'primary') -> str:
    """Update an existing Google Calendar event by event_id. Only pass fields to change."""
    args = ['calendar', 'update', '--event-id', event_id, '--calendar-id', calendar_id]
    if title:
        args += ['--title', title]
    if start:
        args += ['--start', start]
    if end:
        args += ['--end', end]
    if description:
        args += ['--description', description]
    return _gws(*args)


@mcp.tool()
def google_calendar_delete(event_id: str, calendar_id: str = 'primary') -> str:
    """Delete a Google Calendar event by event_id."""
    return _gws('calendar', 'delete', '--event-id', event_id, '--calendar-id', calendar_id)


# ─── Google — Sheets ─────────────────────────────────────────────────────────

@mcp.tool()
def google_sheets_read(spreadsheet_id: str, range_name: str) -> str:
    """
    Read values from a Google Sheet.
    - spreadsheet_id: the sheet ID from the URL
    - range_name: A1 notation e.g. 'Sheet1!A1:D10'
    """
    return _gws('sheets', 'read', '--spreadsheet-id', spreadsheet_id, '--range', range_name)


@mcp.tool()
def google_sheets_write(spreadsheet_id: str, range_name: str, values: str) -> str:
    """
    Write values to a Google Sheet.
    - values: JSON 2D array e.g. '[["Name","Score"],["Alice",95]]'
    """
    return _gws('sheets', 'write', '--spreadsheet-id', spreadsheet_id, '--range', range_name, '--values', values)


@mcp.tool()
def google_sheets_append(spreadsheet_id: str, range_name: str, values: str) -> str:
    """
    Append rows to a Google Sheet.
    - values: JSON 2D array e.g. '[["Alice",95]]'
    """
    return _gws('sheets', 'append', '--spreadsheet-id', spreadsheet_id, '--range', range_name, '--values', values)


# ─── Google — Drive ──────────────────────────────────────────────────────────

@mcp.tool()
def google_drive_search(query: str, max_results: int = 10) -> str:
    """Search Google Drive files by name keyword."""
    return _gws('drive', 'search', '--query', query, '--max', str(max_results))


@mcp.tool()
def google_drive_list(folder_id: str = '', max_results: int = 25) -> str:
    """
    List files in Google Drive.
    - folder_id: restrict to a specific folder (empty = root/all)
    """
    args = ['drive', 'list', '--max', str(max_results)]
    if folder_id:
        args += ['--folder-id', folder_id]
    return _gws(*args)


# ─── Trader — Stockbit Screener ──────────────────────────────────────────────

def _sb_script(code: str, env: dict | None = None) -> str:
    """Run inline trader script, return stdout (trimmed) or raise."""
    full_env = {**_TRADER_ENV, **(env or {})}
    result = subprocess.run(
        [SYSTEM_PYTHON, '-c', code],
        capture_output=True, text=True, timeout=30, env=full_env,
    )
    if not result.stdout and result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout[:4000]


@mcp.tool()
def stockbit_screener_templates() -> str:
    """
    List all Stockbit screener templates (saved + favorites).
    Returns: [{id, name, type, favorite}, ...]
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    print(json.dumps(api.get_screener_templates(), ensure_ascii=False, indent=2))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""")


@mcp.tool()
def stockbit_screener_presets() -> str:
    """
    List Stockbit preset screener categories (Guru Screener, Value, Growth, etc.).
    Returns nested preset tree with template IDs.
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    print(json.dumps(api.get_screener_presets(), ensure_ascii=False, indent=2))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""")


@mcp.tool()
def stockbit_screener_metrics(search: str = '') -> str:
    """
    List available Stockbit screening metrics (fitem_ids for building filters).
    - search: optional keyword filter (e.g. 'volume', 'pe', 'roe')
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
keyword = os.environ.get('SEARCH', '').lower()
try:
    all_metrics = api.get_screener_metrics()
    if keyword:
        matches = []
        for group in all_metrics:
            for child in group.get('child', []):
                if keyword in child.get('fitem_name', '').lower():
                    matches.append({'fitem_id': child.get('fitem_id'), 'fitem_name': child.get('fitem_name'), 'group': group.get('fitem_name')})
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(all_metrics, ensure_ascii=False, indent=2))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""", env={'SEARCH': search})


@mcp.tool()
def stockbit_run_template(template_id: int, result_type: str = 'TEMPLATE_TYPE_CUSTOM') -> str:
    """
    Run a Stockbit screener template by ID.
    Get IDs from stockbit_screener_templates() or stockbit_screener_presets().
    - template_id: numeric template ID
    - result_type: 'TEMPLATE_TYPE_CUSTOM' or 'TEMPLATE_TYPE_GURU'
    Returns matching companies with metric values.
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    result = api.run_screener_template(int(os.environ['TMPL_ID']), result_type=os.environ['TMPL_TYPE'])
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""", env={'TMPL_ID': str(template_id), 'TMPL_TYPE': result_type})


@mcp.tool()
def stockbit_run_custom_screener(
    filters_json: str,
    universe_scope: str = 'IHSG',
    universe_scope_id: str = '',
    ordercol: int = 2,
    ordertype: str = 'desc',
    page: int = 1,
) -> str:
    """
    Run a custom Stockbit screener with arbitrary filters.

    filters_json: JSON array of filter rules, e.g.:
        '[{"type":"lt","item1":2667,"item2":"15"},{"type":"gt","item1":2676,"item2":"10"}]'
      Each rule: {"type": "gt"|"lt"|"eq"|"between", "item1": <fitem_id>, "item2": <value>, "item3": <upper> (between only)}
      Get fitem_ids from stockbit_screener_metrics().

    universe_scope: 'IHSG' (all), 'idx' (index), 'sector'
    universe_scope_id: for idx/sector — e.g. '550' for LQ45, '559' for IDX30
    ordercol: column index to sort by (default 2)
    ordertype: 'asc' or 'desc'
    page: result page (each page ~50 stocks)
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    filters = json.loads(os.environ['FILTERS'])
    universe = {"scope": os.environ['SCOPE'], "scopeID": os.environ['SCOPE_ID'], "name": ""}
    result = api.run_screener_custom(
        filters=filters,
        universe=universe,
        page=int(os.environ['PAGE']),
        ordercol=int(os.environ['ORDERCOL']),
        ordertype=os.environ['ORDERTYPE'],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""", env={
        'FILTERS': filters_json,
        'SCOPE': universe_scope,
        'SCOPE_ID': universe_scope_id,
        'PAGE': str(page),
        'ORDERCOL': str(ordercol),
        'ORDERTYPE': ordertype,
    })


# ─── Trader — Stockbit Emitten & Watchlist ────────────────────────────────────

@mcp.tool()
def stockbit_emitten_info(symbol: str) -> str:
    """
    Get Stockbit company info for a ticker (price, change, avg volume, market cap, exchange).
    Endpoint: exodus.stockbit.com/emitten/{symbol}/info
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    print(json.dumps(api.get_emitten_info(os.environ['SYM']), ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""", env={'SYM': symbol.upper()})


@mcp.tool()
def stockbit_watchlists() -> str:
    """List user's Stockbit native watchlists (not backend watchlist)."""
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    print(json.dumps(api.get_stockbit_watchlists(), ensure_ascii=False, indent=2))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""")


@mcp.tool()
def stockbit_watchlist_items(watchlist_id: int, page: int = 1, limit: int = 50) -> str:
    """
    Get stocks in a Stockbit native watchlist.
    Get watchlist_id from stockbit_watchlists().
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    print(json.dumps(api.get_stockbit_watchlist(int(os.environ['WID']), page=int(os.environ['PAGE']), limit=int(os.environ['LIMIT'])), ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""", env={'WID': str(watchlist_id), 'PAGE': str(page), 'LIMIT': str(limit)})


# ─── Trader — Carina (Portfolio & Orders) ────────────────────────────────────

@mcp.tool()
def carina_cash_balance() -> str:
    """Get available cash balance from Carina broker API."""
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    cash = api.get_cash_balance()
    info = api.get_cash_info()
    print(json.dumps({"available_cash": cash, "cash_info": info}, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""")


@mcp.tool()
def carina_position_detail(stock_code: str) -> str:
    """
    Get per-stock position detail from Carina (qty, avg price, P/L, market value).
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    print(json.dumps(api.get_position_detail(os.environ['SYM']), ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""", env={'SYM': stock_code.upper()})


@mcp.tool()
def carina_orders(stock_code: str = '') -> str:
    """
    List open/today's orders from Carina broker.
    - stock_code: filter by ticker (empty = all orders)
    Returns: [{order_id, symbol, side, price, shares, status_text, filled_shares}, ...]
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
sym = os.environ.get('SYM', '')
try:
    print(json.dumps(api.get_orders(sym or None), ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}))
""", env={'SYM': stock_code.upper()})


@mcp.tool()
def carina_place_buy(symbol: str, price: int, shares: int, board_type: str = 'RG', is_gtc: bool = False) -> str:
    """
    Place a BUY order via Carina broker.
    WARNING: This is a REAL trading order. Confirm symbol/price/shares with user before calling.
    - symbol: ticker e.g. 'BBCA'
    - price: limit price in IDR
    - shares: number of shares (1 lot = 100 shares)
    - board_type: 'RG' (regular) or 'TN' (negotiated)
    - is_gtc: Good Till Cancelled (default False = day order)
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    result = api.place_buy_order(
        symbol=os.environ['SYM'],
        price=int(os.environ['PRICE']),
        shares=int(os.environ['SHARES']),
        board_type=os.environ['BOARD'],
        is_gtc=os.environ['GTC'] == '1',
    )
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
""", env={
        'SYM': symbol.upper(), 'PRICE': str(price), 'SHARES': str(shares),
        'BOARD': board_type, 'GTC': '1' if is_gtc else '0',
    })


@mcp.tool()
def carina_place_sell(symbol: str, price: int, shares: int, board_type: str = 'RG', is_gtc: bool = False) -> str:
    """
    Place a SELL order via Carina broker.
    WARNING: This is a REAL trading order. Confirm symbol/price/shares with user before calling.
    - symbol: ticker e.g. 'BBCA'
    - price: limit price in IDR
    - shares: number of shares (1 lot = 100 shares)
    - board_type: 'RG' (regular) or 'TN' (negotiated)
    - is_gtc: Good Till Cancelled (default False = day order)
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    result = api.place_sell_order(
        symbol=os.environ['SYM'],
        price=int(os.environ['PRICE']),
        shares=int(os.environ['SHARES']),
        board_type=os.environ['BOARD'],
        is_gtc=os.environ['GTC'] == '1',
    )
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
""", env={
        'SYM': symbol.upper(), 'PRICE': str(price), 'SHARES': str(shares),
        'BOARD': board_type, 'GTC': '1' if is_gtc else '0',
    })


@mcp.tool()
def carina_cancel_order(order_id: str) -> str:
    """
    Cancel an open order on Carina broker.
    WARNING: This is a real trading action.
    - order_id: Order ID string (e.g. 'XL039421L...')
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    result = api.cancel_order(os.environ['ORDER_ID'])
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
""", env={'ORDER_ID': order_id})


@mcp.tool()
def carina_amend_order(order_id: str, price: int, shares: int) -> str:
    """
    Amend price/shares of an open order on Carina broker.
    WARNING: This is a real trading action.
    - order_id: Order ID string
    - price: new limit price in IDR
    - shares: new share count (not lots)
    """
    return _sb_script("""
import sys, json, os
sys.path.insert(0, os.environ['TRADER_DIR'])
from config import load_env; load_env()
import api
try:
    req = [{"order_id": os.environ['ORDER_ID'], "price": int(os.environ['PRICE']), "shares": int(os.environ['SHARES'])}]
    result = api.amend_orders(req)
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2, default=str))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
""", env={'ORDER_ID': order_id, 'PRICE': str(price), 'SHARES': str(shares)})


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Lazytools MCP server starting on 0.0.0.0:8765 ...")
    mcp.run(transport='streamable-http')
