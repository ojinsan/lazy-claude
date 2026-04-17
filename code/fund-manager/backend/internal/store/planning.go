package store

import (
	"database/sql"

	"fund-manager/internal/model"
)

// ─── Watchlist ────────────────────────────────────────────────────────────────

func (s *Store) UpsertWatchlist(w *model.Watchlist) error {
	_, err := s.DB.Exec(`
		INSERT INTO watchlist (ticker,first_added,status,conviction,themes,notes,updated_at)
		VALUES (?,?,?,?,?,?,?)
		ON CONFLICT(ticker) DO UPDATE SET
		  status=excluded.status, conviction=excluded.conviction, themes=excluded.themes,
		  notes=excluded.notes, updated_at=excluded.updated_at`,
		w.Ticker, w.FirstAdded, w.Status, w.Conviction, w.Themes, w.Notes, w.UpdatedAt)
	return err
}

func (s *Store) ListWatchlist(status string) ([]*model.Watchlist, error) {
	q := `SELECT ticker,first_added,status,COALESCE(conviction,''),COALESCE(themes,''),
	      COALESCE(notes,''),updated_at FROM watchlist WHERE 1=1`
	args := []any{}
	if status != "" { q += " AND status=?"; args = append(args, status) }
	q += " ORDER BY updated_at DESC"
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Watchlist
	for rows.Next() {
		w := &model.Watchlist{}
		if err := rows.Scan(&w.Ticker, &w.FirstAdded, &w.Status, &w.Conviction, &w.Themes, &w.Notes, &w.UpdatedAt); err != nil {
			return nil, err
		}
		out = append(out, w)
	}
	return out, rows.Err()
}

func (s *Store) DeleteWatchlist(ticker string) error {
	_, err := s.DB.Exec(`UPDATE watchlist SET status='archived' WHERE ticker=?`, ticker)
	return err
}

// ─── Thesis ───────────────────────────────────────────────────────────────────

func (s *Store) UpsertThesis(t *model.Thesis) error {
	_, err := s.DB.Exec(`
		INSERT INTO thesis (ticker,created,layer_origin,status,setup,related_themes,body_md,last_review,updated_at)
		VALUES (?,?,?,?,?,?,?,?,?)
		ON CONFLICT(ticker) DO UPDATE SET
		  status=excluded.status, setup=excluded.setup, related_themes=excluded.related_themes,
		  body_md=excluded.body_md, last_review=excluded.last_review, updated_at=excluded.updated_at`,
		t.Ticker, t.Created, t.LayerOrigin, t.Status, t.Setup, t.RelatedThemes,
		t.BodyMD, t.LastReview, t.UpdatedAt)
	return err
}

func (s *Store) GetThesis(ticker string) (*model.Thesis, error) {
	row := s.DB.QueryRow(`
		SELECT ticker,created,layer_origin,status,COALESCE(setup,''),COALESCE(related_themes,''),
		body_md,COALESCE(last_review,''),updated_at FROM thesis WHERE ticker=?`, ticker)
	t := &model.Thesis{}
	err := row.Scan(&t.Ticker, &t.Created, &t.LayerOrigin, &t.Status, &t.Setup,
		&t.RelatedThemes, &t.BodyMD, &t.LastReview, &t.UpdatedAt)
	if err == sql.ErrNoRows { return nil, nil }
	return t, err
}

func (s *Store) ListThesis(status string) ([]*model.Thesis, error) {
	q := `SELECT ticker,created,layer_origin,status,COALESCE(setup,''),COALESCE(related_themes,''),
	      body_md,COALESCE(last_review,''),updated_at FROM thesis WHERE 1=1`
	args := []any{}
	if status != "" { q += " AND status=?"; args = append(args, status) }
	q += " ORDER BY updated_at DESC"
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Thesis
	for rows.Next() {
		t := &model.Thesis{}
		if err := rows.Scan(&t.Ticker, &t.Created, &t.LayerOrigin, &t.Status, &t.Setup,
			&t.RelatedThemes, &t.BodyMD, &t.LastReview, &t.UpdatedAt); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

func (s *Store) AppendThesisReview(r *model.ThesisReview) (int64, error) {
	res, err := s.DB.Exec(`INSERT INTO thesis_review (ticker,review_date,layer,note) VALUES (?,?,?,?)`,
		r.Ticker, r.ReviewDate, r.Layer, r.Note)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListThesisReviews(ticker string) ([]*model.ThesisReview, error) {
	rows, err := s.DB.Query(`SELECT id,ticker,review_date,layer,note FROM thesis_review
		WHERE ticker=? ORDER BY review_date DESC`, ticker)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.ThesisReview
	for rows.Next() {
		r := &model.ThesisReview{}
		if err := rows.Scan(&r.ID, &r.Ticker, &r.ReviewDate, &r.Layer, &r.Note); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// ─── Theme ────────────────────────────────────────────────────────────────────

func (s *Store) UpsertTheme(t *model.Theme) error {
	_, err := s.DB.Exec(`
		INSERT INTO theme (slug,name,created,status,sector,related_tickers,body_md,updated_at)
		VALUES (?,?,?,?,?,?,?,?)
		ON CONFLICT(slug) DO UPDATE SET
		  name=excluded.name, status=excluded.status, sector=excluded.sector,
		  related_tickers=excluded.related_tickers, body_md=excluded.body_md, updated_at=excluded.updated_at`,
		t.Slug, t.Name, t.Created, t.Status, t.Sector, t.RelatedTickers, t.BodyMD, t.UpdatedAt)
	return err
}

func (s *Store) ListThemes(status string) ([]*model.Theme, error) {
	q := `SELECT slug,name,created,status,COALESCE(sector,''),COALESCE(related_tickers,''),body_md,updated_at
	      FROM theme WHERE 1=1`
	args := []any{}
	if status != "" { q += " AND status=?"; args = append(args, status) }
	q += " ORDER BY updated_at DESC"
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Theme
	for rows.Next() {
		t := &model.Theme{}
		if err := rows.Scan(&t.Slug, &t.Name, &t.Created, &t.Status, &t.Sector, &t.RelatedTickers, &t.BodyMD, &t.UpdatedAt); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

// ─── TradePlan ────────────────────────────────────────────────────────────────

func (s *Store) CreateTradePlan(p *model.TradePlan) (int64, error) {
	res, err := s.DB.Exec(`
		INSERT INTO tradeplan (plan_date,ticker,mode,setup_type,thesis,entry_low,entry_high,stop,
		  target_1,target_2,size_shares,size_value,risk_pct,conviction,calibration_json,priority,level,status,raw_md,created_at)
		VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
		p.PlanDate, p.Ticker, p.Mode, p.SetupType, p.Thesis, p.EntryLow, p.EntryHigh,
		p.Stop, p.Target1, p.Target2, p.SizeShares, p.SizeValue, p.RiskPct,
		p.Conviction, p.CalibrationJSON, p.Priority, p.Level, p.Status, p.RawMD, p.CreatedAt)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) UpdateTradePlanStatus(id int, status string) error {
	_, err := s.DB.Exec(`UPDATE tradeplan SET status=? WHERE id=?`, status, id)
	return err
}

func (s *Store) ListTradePlans(planDate, ticker, status, level string, limit int) ([]*model.TradePlan, error) {
	if limit <= 0 { limit = 50 }
	q := `SELECT id,plan_date,ticker,mode,COALESCE(setup_type,''),COALESCE(thesis,''),
	      COALESCE(entry_low,0),COALESCE(entry_high,0),COALESCE(stop,0),
	      COALESCE(target_1,0),COALESCE(target_2,0),COALESCE(size_shares,0),COALESCE(size_value,0),
	      COALESCE(risk_pct,0),COALESCE(conviction,''),COALESCE(calibration_json,''),
	      COALESCE(priority,0),level,status,raw_md,created_at
	      FROM tradeplan WHERE 1=1`
	args := []any{}
	if planDate != "" { q += " AND plan_date=?"; args = append(args, planDate) }
	if ticker != "" { q += " AND ticker=?"; args = append(args, ticker) }
	if status != "" { q += " AND status=?"; args = append(args, status) }
	if level != "" { q += " AND level=?"; args = append(args, level) }
	q += " ORDER BY created_at DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.TradePlan
	for rows.Next() {
		p := &model.TradePlan{}
		if err := rows.Scan(&p.ID, &p.PlanDate, &p.Ticker, &p.Mode, &p.SetupType, &p.Thesis,
			&p.EntryLow, &p.EntryHigh, &p.Stop, &p.Target1, &p.Target2, &p.SizeShares,
			&p.SizeValue, &p.RiskPct, &p.Conviction, &p.CalibrationJSON, &p.Priority,
			&p.Level, &p.Status, &p.RawMD, &p.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, p)
	}
	return out, rows.Err()
}
