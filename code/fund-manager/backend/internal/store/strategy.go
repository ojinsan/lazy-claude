package store

import "fund-manager/internal/model"

// ─── Tape State ───────────────────────────────────────────────────────────────

type TapeState struct {
	ID          int    `json:"id,omitempty"`
	Ts          string `json:"ts"`
	Ticker      string `json:"ticker"`
	Composite   string `json:"composite"`
	Confidence  string `json:"confidence"`
	WallFate    string `json:"wall_fate,omitempty"`
	PayloadJSON string `json:"payload_json"`
}

func (s *Store) CreateTapeState(t *TapeState) (int64, error) {
	res, err := s.DB.Exec(`INSERT INTO tape_state (ts,ticker,composite,confidence,wall_fate,payload_json) VALUES (?,?,?,?,?,?)`,
		t.Ts, t.Ticker, t.Composite, t.Confidence, t.WallFate, t.PayloadJSON)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListTapeStates(ticker, composite, since string, limit int) ([]*TapeState, error) {
	if limit <= 0 { limit = 100 }
	q := `SELECT id,ts,ticker,composite,confidence,COALESCE(wall_fate,''),payload_json FROM tape_state WHERE 1=1`
	args := []any{}
	if ticker != "" { q += " AND ticker=?"; args = append(args, ticker) }
	if composite != "" { q += " AND composite=?"; args = append(args, composite) }
	if since != "" { q += " AND ts>=?"; args = append(args, since) }
	q += " ORDER BY ts DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*TapeState
	for rows.Next() {
		t := &TapeState{}
		if err := rows.Scan(&t.ID, &t.Ts, &t.Ticker, &t.Composite, &t.Confidence, &t.WallFate, &t.PayloadJSON); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

// ─── Confluence Score ─────────────────────────────────────────────────────────

type ConfluenceScore struct {
	ID             int    `json:"id,omitempty"`
	Ts             string `json:"ts"`
	Ticker         string `json:"ticker"`
	Score          int    `json:"score"`
	Bucket         string `json:"bucket"`
	ComponentsJSON string `json:"components_json"`
}

func (s *Store) CreateConfluenceScore(c *ConfluenceScore) (int64, error) {
	res, err := s.DB.Exec(`INSERT INTO confluence_score (ts,ticker,score,bucket,components_json) VALUES (?,?,?,?,?)`,
		c.Ts, c.Ticker, c.Score, c.Bucket, c.ComponentsJSON)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListConfluenceScores(ticker, bucket, since string, limit int) ([]*ConfluenceScore, error) {
	if limit <= 0 { limit = 100 }
	q := `SELECT id,ts,ticker,score,bucket,components_json FROM confluence_score WHERE 1=1`
	args := []any{}
	if ticker != "" { q += " AND ticker=?"; args = append(args, ticker) }
	if bucket != "" { q += " AND bucket=?"; args = append(args, bucket) }
	if since != "" { q += " AND ts>=?"; args = append(args, since) }
	q += " ORDER BY ts DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*ConfluenceScore
	for rows.Next() {
		c := &ConfluenceScore{}
		if err := rows.Scan(&c.ID, &c.Ts, &c.Ticker, &c.Score, &c.Bucket, &c.ComponentsJSON); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, rows.Err()
}

func (s *Store) LatestConfluencePerTicker() ([]*ConfluenceScore, error) {
	rows, err := s.DB.Query(`
		SELECT id,ts,ticker,score,bucket,components_json FROM confluence_score
		WHERE id IN (SELECT MAX(id) FROM confluence_score GROUP BY ticker)
		ORDER BY score DESC`)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*ConfluenceScore
	for rows.Next() {
		c := &ConfluenceScore{}
		if err := rows.Scan(&c.ID, &c.Ts, &c.Ticker, &c.Score, &c.Bucket, &c.ComponentsJSON); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, rows.Err()
}

// ─── Auto Trigger Log ─────────────────────────────────────────────────────────

type AutoTriggerLog struct {
	ID        int    `json:"id,omitempty"`
	Ts        string `json:"ts"`
	Ticker    string `json:"ticker"`
	Kind      string `json:"kind"`
	Confluence int   `json:"confluence,omitempty"`
	Outcome   string `json:"outcome"`
	Reason    string `json:"reason,omitempty"`
}

func (s *Store) CreateAutoTriggerLog(a *AutoTriggerLog) (int64, error) {
	res, err := s.DB.Exec(`INSERT INTO auto_trigger_log (ts,ticker,kind,confluence,outcome,reason) VALUES (?,?,?,?,?,?)`,
		a.Ts, a.Ticker, a.Kind, nullInt(a.Confluence), a.Outcome, a.Reason)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListAutoTriggerLog(date, outcome string, limit int) ([]*AutoTriggerLog, error) {
	if limit <= 0 { limit = 100 }
	q := `SELECT id,ts,ticker,kind,COALESCE(confluence,0),outcome,COALESCE(reason,'') FROM auto_trigger_log WHERE 1=1`
	args := []any{}
	if date != "" { q += " AND ts LIKE ?"; args = append(args, date+"%") }
	if outcome != "" { q += " AND outcome=?"; args = append(args, outcome) }
	q += " ORDER BY ts DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*AutoTriggerLog
	for rows.Next() {
		a := &AutoTriggerLog{}
		if err := rows.Scan(&a.ID, &a.Ts, &a.Ticker, &a.Kind, &a.Confluence, &a.Outcome, &a.Reason); err != nil {
			return nil, err
		}
		out = append(out, a)
	}
	return out, rows.Err()
}

// ─── Konglo ───────────────────────────────────────────────────────────────────

type KongloGroup struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Owner       string `json:"owner"`
	MarketPower string `json:"market_power,omitempty"`
	Sectors     string `json:"sectors,omitempty"`
}

type KongloTicker struct {
	Ticker  string `json:"ticker"`
	GroupID string `json:"group_id"`
	Category string `json:"category,omitempty"`
	Notes   string `json:"notes,omitempty"`
}

func (s *Store) UpsertKongloGroup(g *KongloGroup) error {
	_, err := s.DB.Exec(`INSERT INTO konglo_group (id,name,owner,market_power,sectors) VALUES (?,?,?,?,?)
		ON CONFLICT(id) DO UPDATE SET name=excluded.name, owner=excluded.owner, market_power=excluded.market_power, sectors=excluded.sectors`,
		g.ID, g.Name, g.Owner, g.MarketPower, g.Sectors)
	return err
}

func (s *Store) ListKongloGroups() ([]*KongloGroup, error) {
	rows, err := s.DB.Query(`SELECT id,name,owner,COALESCE(market_power,''),COALESCE(sectors,'') FROM konglo_group ORDER BY id`)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*KongloGroup
	for rows.Next() {
		g := &KongloGroup{}
		if err := rows.Scan(&g.ID, &g.Name, &g.Owner, &g.MarketPower, &g.Sectors); err != nil { return nil, err }
		out = append(out, g)
	}
	return out, rows.Err()
}

func (s *Store) GetKongloGroupForTicker(ticker string) ([]*KongloGroup, error) {
	rows, err := s.DB.Query(`
		SELECT g.id,g.name,g.owner,COALESCE(g.market_power,''),COALESCE(g.sectors,'')
		FROM konglo_group g JOIN konglo_ticker t ON g.id=t.group_id WHERE t.ticker=?`, ticker)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*KongloGroup
	for rows.Next() {
		g := &KongloGroup{}
		if err := rows.Scan(&g.ID, &g.Name, &g.Owner, &g.MarketPower, &g.Sectors); err != nil { return nil, err }
		out = append(out, g)
	}
	return out, rows.Err()
}

// Ensure model package is used (avoid import cycle)
var _ = model.Signal{}
