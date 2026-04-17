package model

// ─── Portfolio ───────────────────────────────────────────────────────────────

type PortfolioSnapshot struct {
	Date        string  `json:"date"`
	Equity      float64 `json:"equity"`
	Cash        float64 `json:"cash"`
	Deployed    float64 `json:"deployed"`
	Utilization float64 `json:"utilization"`
	Drawdown    float64 `json:"drawdown"`
	HWM         float64 `json:"hwm"`
	Posture     string  `json:"posture"`
	TopExposure string  `json:"top_exposure,omitempty"`
	RawJSON     string  `json:"raw_json,omitempty"`
}

type Holding struct {
	Date          string  `json:"date"`
	Ticker        string  `json:"ticker"`
	Shares        int     `json:"shares"`
	AvgCost       float64 `json:"avg_cost"`
	LastPrice     float64 `json:"last_price,omitempty"`
	MarketValue   float64 `json:"market_value,omitempty"`
	UnrealizedPnL float64 `json:"unrealized_pnl,omitempty"`
	UnrealizedPct float64 `json:"unrealized_pct,omitempty"`
	Sector        string  `json:"sector,omitempty"`
	Action        string  `json:"action,omitempty"`
	ThesisStatus  string  `json:"thesis_status,omitempty"`
}

type Transaction struct {
	ID          int     `json:"id,omitempty"`
	Ts          string  `json:"ts"`
	Ticker      string  `json:"ticker"`
	Side        string  `json:"side"`
	Shares      int     `json:"shares"`
	Price       float64 `json:"price"`
	Value       float64 `json:"value"`
	OrderID     string  `json:"order_id,omitempty"`
	Thesis      string  `json:"thesis,omitempty"`
	Conviction  string  `json:"conviction,omitempty"`
	PnL         float64 `json:"pnl,omitempty"`
	PnLPct      float64 `json:"pnl_pct,omitempty"`
	LayerOrigin string  `json:"layer_origin,omitempty"`
	Notes       string  `json:"notes,omitempty"`
}

// ─── Planning ─────────────────────────────────────────────────────────────────

type Watchlist struct {
	Ticker     string `json:"ticker"`
	FirstAdded string `json:"first_added"`
	Status     string `json:"status"`
	Conviction string `json:"conviction,omitempty"`
	Themes     string `json:"themes,omitempty"`
	Notes      string `json:"notes,omitempty"`
	UpdatedAt  string `json:"updated_at"`
}

type Thesis struct {
	Ticker        string `json:"ticker"`
	Created       string `json:"created"`
	LayerOrigin   string `json:"layer_origin"`
	Status        string `json:"status"`
	Setup         string `json:"setup,omitempty"`
	RelatedThemes string `json:"related_themes,omitempty"`
	BodyMD        string `json:"body_md"`
	LastReview    string `json:"last_review,omitempty"`
	UpdatedAt     string `json:"updated_at"`
}

type ThesisReview struct {
	ID         int    `json:"id,omitempty"`
	Ticker     string `json:"ticker"`
	ReviewDate string `json:"review_date"`
	Layer      string `json:"layer"`
	Note       string `json:"note"`
}

type Theme struct {
	Slug           string `json:"slug"`
	Name           string `json:"name"`
	Created        string `json:"created"`
	Status         string `json:"status"`
	Sector         string `json:"sector,omitempty"`
	RelatedTickers string `json:"related_tickers,omitempty"`
	BodyMD         string `json:"body_md"`
	UpdatedAt      string `json:"updated_at"`
}

type TradePlan struct {
	ID              int     `json:"id,omitempty"`
	PlanDate        string  `json:"plan_date"`
	Ticker          string  `json:"ticker"`
	Mode            string  `json:"mode"`
	SetupType       string  `json:"setup_type,omitempty"`
	Thesis          string  `json:"thesis,omitempty"`
	EntryLow        float64 `json:"entry_low,omitempty"`
	EntryHigh       float64 `json:"entry_high,omitempty"`
	Stop            float64 `json:"stop,omitempty"`
	Target1         float64 `json:"target_1,omitempty"`
	Target2         float64 `json:"target_2,omitempty"`
	SizeShares      int     `json:"size_shares,omitempty"`
	SizeValue       float64 `json:"size_value,omitempty"`
	RiskPct         float64 `json:"risk_pct,omitempty"`
	Conviction      string  `json:"conviction,omitempty"`
	CalibrationJSON string  `json:"calibration_json,omitempty"`
	Priority        int     `json:"priority,omitempty"`
	Level           string  `json:"level"`
	Status          string  `json:"status"`
	RawMD           string  `json:"raw_md"`
	CreatedAt       string  `json:"created_at"`
}

// ─── Signals ──────────────────────────────────────────────────────────────────

type Signal struct {
	ID          int     `json:"id,omitempty"`
	Ts          string  `json:"ts"`
	Ticker      string  `json:"ticker"`
	Layer       string  `json:"layer"`
	Kind        string  `json:"kind"`
	Severity    string  `json:"severity"`
	Price       float64 `json:"price,omitempty"`
	PayloadJSON string  `json:"payload_json"`
	PromotedTo  string  `json:"promoted_to,omitempty"`
}

type LayerOutput struct {
	ID      int    `json:"id,omitempty"`
	RunDate string `json:"run_date"`
	Layer   string `json:"layer"`
	Ts      string `json:"ts"`
	Summary string `json:"summary"`
	BodyMD  string `json:"body_md,omitempty"`
	Severity string `json:"severity,omitempty"`
	Tickers string `json:"tickers,omitempty"`
}

type DailyNote struct {
	Date      string `json:"date"`
	BodyMD    string `json:"body_md"`
	UpdatedAt string `json:"updated_at"`
}

// ─── Learning ─────────────────────────────────────────────────────────────────

type Lesson struct {
	ID            int    `json:"id,omitempty"`
	Date          string `json:"date"`
	Category      string `json:"category"`
	Severity      string `json:"severity"`
	PatternTag    string `json:"pattern_tag,omitempty"`
	Tickers       string `json:"tickers,omitempty"`
	RelatedThesis string `json:"related_thesis,omitempty"`
	LessonText    string `json:"lesson_text"`
	SourceTradeID int    `json:"source_trade_id,omitempty"`
}

type Calibration struct {
	RunDate         string  `json:"run_date"`
	Bucket          string  `json:"bucket"`
	DeclaredWinRate float64 `json:"declared_win_rate,omitempty"`
	ActualWinRate   float64 `json:"actual_win_rate,omitempty"`
	Drift           float64 `json:"drift,omitempty"`
	NTrades         int     `json:"n_trades"`
	WindowDays      int     `json:"window_days"`
}

type PerformanceDaily struct {
	Date          string  `json:"date"`
	Equity        float64 `json:"equity"`
	IHSGClose     float64 `json:"ihsg_close,omitempty"`
	DailyReturn   float64 `json:"daily_return,omitempty"`
	IHSGReturn    float64 `json:"ihsg_return,omitempty"`
	Alpha         float64 `json:"alpha,omitempty"`
	MTDReturn     float64 `json:"mtd_return,omitempty"`
	YTDReturn     float64 `json:"ytd_return,omitempty"`
	WinRate90d    float64 `json:"win_rate_90d,omitempty"`
	AvgR90d       float64 `json:"avg_r_90d,omitempty"`
	Expectancy90d float64 `json:"expectancy_90d,omitempty"`
}

type Evaluation struct {
	ID          int    `json:"id,omitempty"`
	Period      string `json:"period"`
	PeriodKey   string `json:"period_key"`
	GeneratedAt string `json:"generated_at"`
	BodyMD      string `json:"body_md"`
	KPIJson     string `json:"kpi_json"`
}

// ─── Charts ───────────────────────────────────────────────────────────────────

type ChartAsset struct {
	ID          int    `json:"id,omitempty"`
	Ticker      string `json:"ticker"`
	AsOf        string `json:"as_of"`
	Kind        string `json:"kind"`
	Timeframe   string `json:"timeframe,omitempty"`
	PayloadJSON string `json:"payload_json"`
}

// ─── Cache ────────────────────────────────────────────────────────────────────

type Price struct {
	Ticker string  `json:"ticker"`
	Price  float64 `json:"price"`
	Bid    float64 `json:"bid,omitempty"`
	Ask    float64 `json:"ask,omitempty"`
	Ts     string  `json:"ts"`
}

// ─── Insights ─────────────────────────────────────────────────────────────────

type Insight struct {
	ID              int    `json:"id,omitempty"`
	OccurredAt      string `json:"occurred_at"`
	Ticker          string `json:"ticker"`
	Content         string `json:"content"`
	ParticipantType string `json:"participant_type"`
	AIRecap         string `json:"ai_recap,omitempty"`
	Confidence      int    `json:"confidence"`
	AddressText     string `json:"address_text,omitempty"`
	Source          string `json:"source"`
	Topic           string `json:"topic,omitempty"`
	CreatedAt       string `json:"created_at,omitempty"`
}

type InsightIngestion struct {
	Insights []InsightInput `json:"insights"`
}

type InsightInput struct {
	Time            string `json:"time"`
	Content         string `json:"content"`
	ParticipantType string `json:"participant_type"`
	AddressText     string `json:"address_text"`
	Source          string `json:"source"`
	Topic           string `json:"topic,omitempty"`
	Confidence      int    `json:"confidence,omitempty"`
}

type PositiveCandidate struct {
	Ticker   string `json:"ticker"`
	MaxConf  int    `json:"max_confidence"`
	Count    int    `json:"count"`
	LatestAt string `json:"latest_at"`
	Source   string `json:"source"`
}

// WatchlistEntry is returned by the Lark client and GET /watchlist.
type WatchlistEntry struct {
	Stock  string `json:"stock"`
	Status string `json:"status"`
	Source string `json:"source,omitempty"`
}
