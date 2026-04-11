"""
Lazywork MCP Server
====================
Exposes workspace tools over SSE so any Claude on the Tailscale network
can call them as native MCP tools.

Transport: HTTP + SSE  →  http://lazywork-mbp.tailc83490.ts.net:8765/sse
Auth: Tailscale handles network auth — no token needed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

WORKSPACE = Path('/home/lazywork/workspace')
TRADER_DIR = WORKSPACE / 'tools/trader'
THREADS_SCRIPT = WORKSPACE / 'tools/general/playwright/threads-scraper.js'
OPENCLAW = Path('/home/lazywork/.openclaw/workspace')
RUNTIME = OPENCLAW / 'scarlett/runtime'
MONITORING_DIR = RUNTIME / 'monitoring'
LOG_DIR = RUNTIME / 'logs'
WATCHLIST_FILE = RUNTIME / 'watchlists/active.json'

mcp = FastMCP(
    "lazytools",
    instructions="Tools running on lazywork-mbp. Threads scraping, trading screener, stockbit data, monitoring status.",
    host="0.0.0.0",
    port=8765,
)


# ─── Threads ─────────────────────────────────────────────────────────────────

@mcp.tool()
def threads_search(query: str, limit: int = 10) -> str:
    """
    Search Threads posts by keyword using the logged-in Firefox profile.
    Returns post text, likes, and reply counts.
    """
    result = subprocess.run(
        ['node', str(THREADS_SCRIPT), '--query', query, '--limit', str(limit), '--output', '/tmp/mcp_threads.json'],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        return f"Error: {result.stderr[:500]}"
    try:
        data = json.loads(Path('/tmp/mcp_threads.json').read_text())
        posts = data.get('results', [])
        lines = [f"Query: {query} ({len(posts)} results)\n"]
        for p in posts:
            text = p.get('text', '').strip()
            if text:
                lines.append(f"---\n{text[:400]}\nLikes: {p.get('likes',0)} | Replies: {p.get('replies',0)}")
        return '\n'.join(lines)
    except Exception as e:
        return f"Parse error: {e}\nRaw: {result.stdout[:300]}"


# ─── Trader — Screener ───────────────────────────────────────────────────────

@mcp.tool()
def run_screener(tickers: str = '', layer1_only: bool = False, deep_ticker: str = '') -> str:
    """
    Run the Lazyboy stock screener.
    - tickers: space-separated list e.g. 'VKTR ESSA' (empty = full watchlist scan)
    - layer1_only: only run macro + sector rotation layer
    - deep_ticker: single ticker for deep dive (includes SID, slow)
    """
    cmd = [sys.executable, 'screener.py']
    if tickers:
        cmd += ['--tickers'] + tickers.split()
    if layer1_only:
        cmd.append('--layer1')
    if deep_ticker:
        cmd += ['--deep', deep_ticker]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300, cwd=str(TRADER_DIR)
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
        [sys.executable, 'runtime_layer1_context.py'],
        capture_output=True, text=True, timeout=180, cwd=str(TRADER_DIR)
    )
    out = result.stdout + result.stderr
    return out[-4000:] if len(out) > 4000 else out


# ─── Trader — Watchlist ───────────────────────────────────────────────────────

@mcp.tool()
def get_watchlist() -> str:
    """
    Return the current active watchlist (4-group structure: momentum, accumulation, speculative, avoid).
    """
    if not WATCHLIST_FILE.exists():
        return "Watchlist file not found."
    data = json.loads(WATCHLIST_FILE.read_text())
    lines = []
    for group, tickers in data.items():
        if isinstance(tickers, list):
            lines.append(f"{group}: {', '.join(tickers) or '(empty)'}")
        elif isinstance(tickers, dict):
            lines.append(f"{group}:")
            for ticker, meta in tickers.items():
                lines.append(f"  {ticker}: {meta}")
    return '\n'.join(lines) if lines else json.dumps(data, indent=2)


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
import sys, json
sys.path.insert(0, '{trader_dir}')
from config import load_env
load_env()
import api

sid = '{sid}'
results = {{}}

try:
    ob = api.get_orderbook(sid)
    results['orderbook'] = ob
except Exception as e:
    results['orderbook_error'] = str(e)

try:
    bf = api.get_broker_flow(sid)
    results['broker_flow'] = bf
except Exception as e:
    results['broker_flow_error'] = str(e)

print(json.dumps(results, ensure_ascii=False, indent=2))
""".format(trader_dir=str(TRADER_DIR), sid=sid.upper())

    result = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return f"Error: {result.stderr[:500]}"
    return result.stdout[:3000]


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
        return f"Log '{log_name}' not found. Available: {available}"
    content = log_file.read_text().splitlines()
    return '\n'.join(content[-lines:])


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Lazytools MCP server starting on 0.0.0.0:8765 ...")
    mcp.run(transport='sse')
