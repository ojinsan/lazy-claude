-- 0008_insights.sql
-- Telegram insight ingestion + FTS5 search

CREATE TABLE IF NOT EXISTS insight (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at  TEXT    NOT NULL,
    ticker       TEXT    NOT NULL DEFAULT '',
    content      TEXT    NOT NULL DEFAULT '',
    participant_type TEXT NOT NULL DEFAULT '',
    ai_recap     TEXT    NOT NULL DEFAULT '',
    confidence   INTEGER NOT NULL DEFAULT 0,
    address_text TEXT    NOT NULL DEFAULT '',
    source       TEXT    NOT NULL DEFAULT '',
    topic        TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_insight_ticker_date ON insight(ticker, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_insight_confidence  ON insight(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_insight_occurred    ON insight(occurred_at DESC);

-- FTS5 for RAG search
CREATE VIRTUAL TABLE IF NOT EXISTS insight_fts USING fts5(
    ticker, content, ai_recap, source,
    content='insight',
    content_rowid='id'
);

-- Keep FTS in sync
CREATE TRIGGER IF NOT EXISTS insight_fts_ai AFTER INSERT ON insight BEGIN
    INSERT INTO insight_fts(rowid, ticker, content, ai_recap, source)
    VALUES (new.id, new.ticker, new.content, new.ai_recap, new.source);
END;

CREATE TRIGGER IF NOT EXISTS insight_fts_ad AFTER DELETE ON insight BEGIN
    INSERT INTO insight_fts(insight_fts, rowid, ticker, content, ai_recap, source)
    VALUES ('delete', old.id, old.ticker, old.content, old.ai_recap, old.source);
END;
