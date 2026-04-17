CREATE TABLE konglo_group (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  owner        TEXT NOT NULL,
  market_power TEXT,
  sectors      TEXT
);

CREATE TABLE konglo_ticker (
  ticker   TEXT NOT NULL,
  group_id TEXT NOT NULL,
  category TEXT,
  notes    TEXT,
  PRIMARY KEY (ticker, group_id)
);
