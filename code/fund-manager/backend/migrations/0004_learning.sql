CREATE TABLE lesson (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  date           TEXT NOT NULL,
  category       TEXT NOT NULL,
  severity       TEXT NOT NULL,
  pattern_tag    TEXT,
  tickers        TEXT,
  related_thesis TEXT,
  lesson_text    TEXT NOT NULL,
  source_trade_id INTEGER,
  FOREIGN KEY(source_trade_id) REFERENCES transaction_log(id)
);
CREATE INDEX ix_lesson_date ON lesson(date);
CREATE INDEX ix_lesson_pattern ON lesson(pattern_tag);

CREATE TABLE calibration (
  run_date       TEXT NOT NULL,
  bucket         TEXT NOT NULL,
  declared_win_rate REAL,
  actual_win_rate   REAL,
  drift             REAL,
  n_trades          INTEGER NOT NULL,
  window_days       INTEGER NOT NULL,
  PRIMARY KEY (run_date, bucket, window_days)
);

CREATE TABLE performance_daily (
  date           TEXT PRIMARY KEY,
  equity         REAL NOT NULL,
  ihsg_close     REAL,
  daily_return   REAL,
  ihsg_return    REAL,
  alpha          REAL,
  mtd_return     REAL,
  ytd_return     REAL,
  win_rate_90d   REAL,
  avg_r_90d      REAL,
  expectancy_90d REAL
);

CREATE TABLE evaluation (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  period         TEXT NOT NULL,
  period_key     TEXT NOT NULL,
  generated_at   TEXT NOT NULL,
  body_md        TEXT NOT NULL,
  kpi_json       TEXT NOT NULL
);
CREATE UNIQUE INDEX ix_eval_period ON evaluation(period, period_key);
