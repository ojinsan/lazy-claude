package store

import (
	"fund-manager/internal/model"
)

func (s *Store) CreateSignal(sig *model.Signal) (int64, error) {
	res, err := s.DB.Exec(`
		INSERT INTO signal (ts,ticker,layer,kind,severity,price,payload_json,promoted_to)
		VALUES (?,?,?,?,?,?,?,?)`,
		sig.Ts, sig.Ticker, sig.Layer, sig.Kind, sig.Severity, sig.Price, sig.PayloadJSON, sig.PromotedTo)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListSignals(ticker, layer, kind, since string, limit int) ([]*model.Signal, error) {
	if limit <= 0 { limit = 100 }
	q := `SELECT id,ts,ticker,layer,kind,severity,COALESCE(price,0),payload_json,COALESCE(promoted_to,'')
	      FROM signal WHERE 1=1`
	args := []any{}
	if ticker != "" { q += " AND ticker=?"; args = append(args, ticker) }
	if layer != "" { q += " AND layer=?"; args = append(args, layer) }
	if kind != "" { q += " AND kind=?"; args = append(args, kind) }
	if since != "" { q += " AND ts>=?"; args = append(args, since) }
	q += " ORDER BY ts DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Signal
	for rows.Next() {
		sig := &model.Signal{}
		if err := rows.Scan(&sig.ID, &sig.Ts, &sig.Ticker, &sig.Layer, &sig.Kind,
			&sig.Severity, &sig.Price, &sig.PayloadJSON, &sig.PromotedTo); err != nil {
			return nil, err
		}
		out = append(out, sig)
	}
	return out, rows.Err()
}

func (s *Store) CreateLayerOutput(lo *model.LayerOutput) (int64, error) {
	res, err := s.DB.Exec(`
		INSERT INTO layer_output (run_date,layer,ts,summary,body_md,severity,tickers)
		VALUES (?,?,?,?,?,?,?)`,
		lo.RunDate, lo.Layer, lo.Ts, lo.Summary, lo.BodyMD, lo.Severity, lo.Tickers)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListLayerOutputs(runDate, layer, severity string, limit int) ([]*model.LayerOutput, error) {
	if limit <= 0 { limit = 100 }
	q := `SELECT id,run_date,layer,ts,summary,COALESCE(body_md,''),COALESCE(severity,''),COALESCE(tickers,'')
	      FROM layer_output WHERE 1=1`
	args := []any{}
	if runDate != "" { q += " AND run_date=?"; args = append(args, runDate) }
	if layer != "" { q += " AND layer=?"; args = append(args, layer) }
	if severity != "" { q += " AND severity=?"; args = append(args, severity) }
	q += " ORDER BY ts DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.LayerOutput
	for rows.Next() {
		lo := &model.LayerOutput{}
		if err := rows.Scan(&lo.ID, &lo.RunDate, &lo.Layer, &lo.Ts, &lo.Summary,
			&lo.BodyMD, &lo.Severity, &lo.Tickers); err != nil {
			return nil, err
		}
		out = append(out, lo)
	}
	return out, rows.Err()
}

func (s *Store) UpsertDailyNote(n *model.DailyNote) error {
	_, err := s.DB.Exec(`
		INSERT INTO daily_note (date,body_md,updated_at) VALUES (?,?,?)
		ON CONFLICT(date) DO UPDATE SET body_md=excluded.body_md, updated_at=excluded.updated_at`,
		n.Date, n.BodyMD, n.UpdatedAt)
	return err
}

func (s *Store) GetDailyNote(date string) (*model.DailyNote, error) {
	row := s.DB.QueryRow(`SELECT date,body_md,updated_at FROM daily_note WHERE date=?`, date)
	n := &model.DailyNote{}
	if err := row.Scan(&n.Date, &n.BodyMD, &n.UpdatedAt); err != nil {
		return nil, nil
	}
	return n, nil
}
