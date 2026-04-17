CREATE TABLE signal (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ts             TEXT NOT NULL,
  ticker         TEXT NOT NULL,
  layer          TEXT NOT NULL,
  kind           TEXT NOT NULL,
  severity       TEXT NOT NULL,
  price          REAL,
  payload_json   TEXT NOT NULL,
  promoted_to    TEXT
);
CREATE INDEX ix_signal_ticker_ts ON signal(ticker, ts);
CREATE INDEX ix_signal_kind_ts ON signal(kind, ts);

CREATE TABLE layer_output (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date       TEXT NOT NULL,
  layer          TEXT NOT NULL,
  ts             TEXT NOT NULL,
  summary        TEXT NOT NULL,
  body_md        TEXT,
  severity       TEXT,
  tickers        TEXT
);
CREATE INDEX ix_layer_date ON layer_output(run_date, layer);

CREATE TABLE daily_note (
  date           TEXT PRIMARY KEY,
  body_md        TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);
