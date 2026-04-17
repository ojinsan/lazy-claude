CREATE TABLE tape_state (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           TEXT NOT NULL,
  ticker       TEXT NOT NULL,
  composite    TEXT NOT NULL,
  confidence   TEXT NOT NULL,
  wall_fate    TEXT,
  payload_json TEXT NOT NULL
);
CREATE INDEX ix_tape_ticker_ts ON tape_state(ticker, ts);

CREATE TABLE confluence_score (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              TEXT NOT NULL,
  ticker          TEXT NOT NULL,
  score           INTEGER NOT NULL,
  bucket          TEXT NOT NULL,
  components_json TEXT NOT NULL
);
CREATE INDEX ix_confluence_ticker_ts ON confluence_score(ticker, ts);

CREATE TABLE auto_trigger_log (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         TEXT NOT NULL,
  ticker     TEXT NOT NULL,
  kind       TEXT NOT NULL,
  confluence INTEGER,
  outcome    TEXT NOT NULL,
  reason     TEXT
);
