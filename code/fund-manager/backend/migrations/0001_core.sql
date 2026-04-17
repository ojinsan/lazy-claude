CREATE TABLE portfolio_snapshot (
  date          TEXT PRIMARY KEY,
  equity        REAL NOT NULL,
  cash          REAL NOT NULL,
  deployed      REAL NOT NULL,
  utilization   REAL NOT NULL,
  drawdown      REAL NOT NULL,
  hwm           REAL NOT NULL,
  posture       TEXT NOT NULL,
  top_exposure  TEXT,
  raw_json      TEXT NOT NULL
);

CREATE TABLE holding (
  date          TEXT NOT NULL,
  ticker        TEXT NOT NULL,
  shares        INTEGER NOT NULL,
  avg_cost      REAL NOT NULL,
  last_price    REAL,
  market_value  REAL,
  unrealized_pnl REAL,
  unrealized_pct REAL,
  sector        TEXT,
  action        TEXT,
  thesis_status TEXT,
  PRIMARY KEY (date, ticker)
);

CREATE TABLE transaction_log (
  id            INTEGER PRIMARY KEY,
  ts            TEXT NOT NULL,
  ticker        TEXT NOT NULL,
  side          TEXT NOT NULL,
  shares        INTEGER NOT NULL,
  price         REAL NOT NULL,
  value         REAL NOT NULL,
  order_id      TEXT,
  thesis        TEXT,
  conviction    TEXT,
  pnl           REAL,
  pnl_pct       REAL,
  layer_origin  TEXT,
  notes         TEXT
);
CREATE INDEX ix_tx_ticker_ts ON transaction_log(ticker, ts);
