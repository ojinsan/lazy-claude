CREATE TABLE watchlist (
  ticker         TEXT PRIMARY KEY,
  first_added    TEXT NOT NULL,
  status         TEXT NOT NULL,
  conviction     TEXT,
  themes         TEXT,
  notes          TEXT,
  updated_at     TEXT NOT NULL
);

CREATE TABLE thesis (
  ticker         TEXT PRIMARY KEY,
  created        TEXT NOT NULL,
  layer_origin   TEXT NOT NULL,
  status         TEXT NOT NULL,
  setup          TEXT,
  related_themes TEXT,
  body_md        TEXT NOT NULL,
  last_review    TEXT,
  updated_at     TEXT NOT NULL
);

CREATE TABLE thesis_review (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker         TEXT NOT NULL,
  review_date    TEXT NOT NULL,
  layer          TEXT NOT NULL,
  note           TEXT NOT NULL,
  FOREIGN KEY(ticker) REFERENCES thesis(ticker)
);
CREATE INDEX ix_review_ticker_date ON thesis_review(ticker, review_date);

CREATE TABLE theme (
  slug           TEXT PRIMARY KEY,
  name           TEXT NOT NULL,
  created        TEXT NOT NULL,
  status         TEXT NOT NULL,
  sector         TEXT,
  related_tickers TEXT,
  body_md        TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);

CREATE TABLE tradeplan (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_date      TEXT NOT NULL,
  ticker         TEXT NOT NULL,
  mode           TEXT NOT NULL,
  setup_type     TEXT,
  thesis         TEXT,
  entry_low      REAL,
  entry_high     REAL,
  stop           REAL,
  target_1       REAL,
  target_2       REAL,
  size_shares    INTEGER,
  size_value     REAL,
  risk_pct       REAL,
  conviction     TEXT,
  calibration_json TEXT,
  priority       INTEGER,
  level          TEXT NOT NULL,
  status         TEXT NOT NULL,
  raw_md         TEXT NOT NULL,
  created_at     TEXT NOT NULL
);
CREATE INDEX ix_plan_date_ticker ON tradeplan(plan_date, ticker);
