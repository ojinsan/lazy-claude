CREATE TABLE chart_asset (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker         TEXT NOT NULL,
  as_of          TEXT NOT NULL,
  kind           TEXT NOT NULL,
  timeframe      TEXT,
  payload_json   TEXT NOT NULL
);
CREATE INDEX ix_chart_ticker_kind ON chart_asset(ticker, kind, as_of);
