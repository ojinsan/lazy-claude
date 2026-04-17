package store

import (
	"database/sql"
	"fmt"

	"fund-manager/internal/model"
)

// ─── Portfolio Snapshot ───────────────────────────────────────────────────────

func (s *Store) UpsertPortfolioSnapshot(p *model.PortfolioSnapshot) error {
	_, err := s.DB.Exec(`
		INSERT INTO portfolio_snapshot (date,equity,cash,deployed,utilization,drawdown,hwm,posture,top_exposure,raw_json)
		VALUES (?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(date) DO UPDATE SET
		  equity=excluded.equity, cash=excluded.cash, deployed=excluded.deployed,
		  utilization=excluded.utilization, drawdown=excluded.drawdown, hwm=excluded.hwm,
		  posture=excluded.posture, top_exposure=excluded.top_exposure, raw_json=excluded.raw_json`,
		p.Date, p.Equity, p.Cash, p.Deployed, p.Utilization, p.Drawdown, p.HWM,
		p.Posture, p.TopExposure, p.RawJSON)
	return err
}

func (s *Store) ListPortfolioSnapshots(from, to string, limit int) ([]*model.PortfolioSnapshot, error) {
	if limit <= 0 { limit = 60 }
	rows, err := s.DB.Query(`
		SELECT date,equity,cash,deployed,utilization,drawdown,hwm,posture,
		       COALESCE(top_exposure,''), COALESCE(raw_json,'{}')
		FROM portfolio_snapshot WHERE date BETWEEN ? AND ?
		ORDER BY date DESC LIMIT ?`, from, to, limit)
	if err != nil { return nil, err }
	defer rows.Close()
	return scanSnapshots(rows)
}

func (s *Store) LatestPortfolioSnapshot() (*model.PortfolioSnapshot, error) {
	row := s.DB.QueryRow(`
		SELECT date,equity,cash,deployed,utilization,drawdown,hwm,posture,
		       COALESCE(top_exposure,''), COALESCE(raw_json,'{}')
		FROM portfolio_snapshot ORDER BY date DESC LIMIT 1`)
	p := &model.PortfolioSnapshot{}
	err := row.Scan(&p.Date, &p.Equity, &p.Cash, &p.Deployed, &p.Utilization,
		&p.Drawdown, &p.HWM, &p.Posture, &p.TopExposure, &p.RawJSON)
	if err == sql.ErrNoRows { return nil, nil }
	return p, err
}

func scanSnapshots(rows *sql.Rows) ([]*model.PortfolioSnapshot, error) {
	var out []*model.PortfolioSnapshot
	for rows.Next() {
		p := &model.PortfolioSnapshot{}
		if err := rows.Scan(&p.Date, &p.Equity, &p.Cash, &p.Deployed, &p.Utilization,
			&p.Drawdown, &p.HWM, &p.Posture, &p.TopExposure, &p.RawJSON); err != nil {
			return nil, err
		}
		out = append(out, p)
	}
	return out, rows.Err()
}

// ─── Holdings ─────────────────────────────────────────────────────────────────

func (s *Store) UpsertHoldings(holdings []*model.Holding) error {
	tx, err := s.DB.Begin()
	if err != nil { return err }
	stmt, err := tx.Prepare(`
		INSERT INTO holding (date,ticker,shares,avg_cost,last_price,market_value,
		  unrealized_pnl,unrealized_pct,sector,action,thesis_status)
		VALUES (?,?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(date,ticker) DO UPDATE SET
		  shares=excluded.shares, avg_cost=excluded.avg_cost, last_price=excluded.last_price,
		  market_value=excluded.market_value, unrealized_pnl=excluded.unrealized_pnl,
		  unrealized_pct=excluded.unrealized_pct, sector=excluded.sector,
		  action=excluded.action, thesis_status=excluded.thesis_status`)
	if err != nil { tx.Rollback(); return err }
	defer stmt.Close()
	for _, h := range holdings {
		if _, err := stmt.Exec(h.Date, h.Ticker, h.Shares, h.AvgCost, h.LastPrice,
			h.MarketValue, h.UnrealizedPnL, h.UnrealizedPct, h.Sector, h.Action, h.ThesisStatus); err != nil {
			tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func (s *Store) ListHoldings(date, ticker string) ([]*model.Holding, error) {
	q := `SELECT date,ticker,shares,avg_cost,COALESCE(last_price,0),
	      COALESCE(market_value,0),COALESCE(unrealized_pnl,0),COALESCE(unrealized_pct,0),
	      COALESCE(sector,''),COALESCE(action,''),COALESCE(thesis_status,'')
	      FROM holding WHERE 1=1`
	args := []any{}
	if date != "" { q += " AND date=?"; args = append(args, date) }
	if ticker != "" { q += " AND ticker=?"; args = append(args, ticker) }
	q += " ORDER BY date DESC, ticker"
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Holding
	for rows.Next() {
		h := &model.Holding{}
		if err := rows.Scan(&h.Date, &h.Ticker, &h.Shares, &h.AvgCost, &h.LastPrice,
			&h.MarketValue, &h.UnrealizedPnL, &h.UnrealizedPct, &h.Sector, &h.Action, &h.ThesisStatus); err != nil {
			return nil, err
		}
		out = append(out, h)
	}
	return out, rows.Err()
}

// ─── Transactions ─────────────────────────────────────────────────────────────

func (s *Store) CreateTransaction(t *model.Transaction) (int64, error) {
	res, err := s.DB.Exec(`
		INSERT INTO transaction_log (ts,ticker,side,shares,price,value,order_id,thesis,conviction,pnl,pnl_pct,layer_origin,notes)
		VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`,
		t.Ts, t.Ticker, t.Side, t.Shares, t.Price, t.Value, t.OrderID,
		t.Thesis, t.Conviction, t.PnL, t.PnLPct, t.LayerOrigin, t.Notes)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) UpdateTransaction(id int, pnl, pnlPct float64) error {
	_, err := s.DB.Exec(`UPDATE transaction_log SET pnl=?,pnl_pct=? WHERE id=?`, pnl, pnlPct, id)
	return err
}

func (s *Store) ListTransactions(ticker string, days int, side string, limit int) ([]*model.Transaction, error) {
	if limit <= 0 { limit = 100 }
	q := `SELECT id,ts,ticker,side,shares,price,value,
	      COALESCE(order_id,''),COALESCE(thesis,''),COALESCE(conviction,''),
	      COALESCE(pnl,0),COALESCE(pnl_pct,0),COALESCE(layer_origin,''),COALESCE(notes,'')
	      FROM transaction_log WHERE 1=1`
	args := []any{}
	if ticker != "" { q += " AND ticker=?"; args = append(args, ticker) }
	if days > 0 { q += fmt.Sprintf(" AND ts >= datetime('now','-%d days')", days) }
	if side != "" { q += " AND side=?"; args = append(args, side) }
	q += " ORDER BY ts DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Transaction
	for rows.Next() {
		t := &model.Transaction{}
		if err := rows.Scan(&t.ID, &t.Ts, &t.Ticker, &t.Side, &t.Shares, &t.Price, &t.Value,
			&t.OrderID, &t.Thesis, &t.Conviction, &t.PnL, &t.PnLPct, &t.LayerOrigin, &t.Notes); err != nil {
			return nil, err
		}
		out = append(out, t)
	}
	return out, rows.Err()
}
