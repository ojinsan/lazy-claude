const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8787/api/v1";

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PUT ${path} → ${res.status}`);
  return res.json();
}

// ─── Typed fetchers ──────────────────────────────────────────────────────────

export type PortfolioSnapshot = { date: string; equity: number; cash: number; deployed: number; utilization: number; drawdown: number; hwm: number; posture: string; };
export type Holding = { date: string; ticker: string; shares: number; avg_cost: number; last_price: number; market_value: number; unrealized_pnl: number; unrealized_pct: number; sector: string; action: string; thesis_status: string; };
export type Transaction = { id: number; ts: string; ticker: string; side: string; shares: number; price: number; value: number; pnl: number; pnl_pct: number; layer_origin: string; notes: string; };
export type Signal = { id: number; ts: string; ticker: string; layer: string; kind: string; severity: string; price: number; payload_json: string; };
export type LayerOutput = { id: number; run_date: string; layer: string; ts: string; summary: string; body_md: string; severity: string; tickers: string; };
export type TradePlan = { id: number; plan_date: string; ticker: string; mode: string; setup_type: string; entry_low: number; entry_high: number; stop: number; target_1: number; target_2: number; size_value: number; risk_pct: number; conviction: string; level: string; status: string; raw_md: string; };
export type Watchlist = { ticker: string; first_added: string; status: string; conviction: string; themes: string; notes: string; };
export type Thesis = { ticker: string; created: string; status: string; body_md: string; last_review: string; };
export type ThesisReview = { id: number; ticker: string; review_date: string; layer: string; note: string; };
export type Theme = { slug: string; name: string; status: string; sector: string; related_tickers: string; body_md: string; };
export type Lesson = { id: number; date: string; category: string; severity: string; pattern_tag: string; lesson_text: string; tickers: string; };
export type PerformanceDaily = { date: string; equity: number; ihsg_close: number; daily_return: number; ihsg_return: number; alpha: number; mtd_return: number; ytd_return: number; win_rate_90d: number; };
export type Evaluation = { id: number; period: string; period_key: string; generated_at: string; body_md: string; kpi_json: string; };
export type DailyNote = { date: string; body_md: string; };

type ListResp<T> = { items: T[]; count: number };

export const api = {
  getPortfolioCurrent: () => get<{ snapshot: PortfolioSnapshot; holdings: Holding[] }>("/portfolio/current"),
  getSnapshots: (from?: string, to?: string) => get<ListResp<PortfolioSnapshot>>("/portfolio/snapshot", { from, to }),
  getHoldings: (date?: string, ticker?: string) => get<ListResp<Holding>>("/portfolio/holdings", { date, ticker }),
  getTransactions: (ticker?: string, days?: number, side?: string) => get<ListResp<Transaction>>("/transactions", { ticker, days, side }),
  postSnapshot: (body: Partial<PortfolioSnapshot>) => post<PortfolioSnapshot>("/portfolio/snapshot", body),
  putTransaction: (id: number, pnl: number, pnl_pct: number) => put(`/transactions/${id}`, { pnl, pnl_pct }),

  getWatchlist: (status?: string) => get<ListResp<Watchlist>>("/watchlist", { status }),
  postWatchlist: (body: Partial<Watchlist>) => post<Watchlist>("/watchlist", body),

  getThesisList: (status?: string) => get<ListResp<Thesis>>("/thesis", { status }),
  getThesis: (ticker: string) => get<Thesis>(`/thesis/${ticker}`),
  putThesis: (ticker: string, body: Partial<Thesis>) => put(`/thesis/${ticker}`, body),
  getThesisReviews: (ticker: string) => get<ListResp<ThesisReview>>(`/thesis/${ticker}/review`),
  postThesisReview: (ticker: string, body: Partial<ThesisReview>) => post<ThesisReview>(`/thesis/${ticker}/review`, body),

  getThemes: (status?: string) => get<ListResp<Theme>>("/themes", { status }),
  postTheme: (body: Partial<Theme>) => post<Theme>("/themes", body),

  getTradePlans: (plan_date?: string, ticker?: string, status?: string, level?: string) =>
    get<ListResp<TradePlan>>("/tradeplans", { plan_date, ticker, status, level }),
  postTradePlan: (body: Partial<TradePlan>) => post<TradePlan>("/tradeplans", body),
  putTradePlan: (id: number, status: string) => put(`/tradeplans/${id}`, { status }),

  getSignals: (ticker?: string, layer?: string, kind?: string, since?: string, limit = 100) =>
    get<ListResp<Signal>>("/signals", { ticker, layer, kind, since, limit }),
  getRecentSignals: () => get<ListResp<Signal>>("/signals/recent"),
  postSignal: (body: Partial<Signal>) => post<Signal>("/signals", body),

  getLayerOutputs: (run_date?: string, layer?: string) => get<ListResp<LayerOutput>>("/layer-outputs", { run_date, layer }),
  getDailyNote: (date: string) => get<DailyNote>(`/daily-notes/${date}`).catch(() => null),

  getLessons: (category?: string, severity?: string, pattern_tag?: string, days?: number) =>
    get<ListResp<Lesson>>("/lessons", { category, severity, pattern_tag, days }),

  getPerformanceDaily: (from?: string, to?: string) => get<ListResp<PerformanceDaily>>("/performance/daily", { from, to }),
  getPerformanceSummary: () => get<Record<string, number>>("/performance/summary"),

  getEvaluations: (period?: string) => get<ListResp<Evaluation>>("/evaluations", { period }),

  getKillSwitch: () => get<{ active: boolean; reason?: string }>("/kill-switch"),
};
