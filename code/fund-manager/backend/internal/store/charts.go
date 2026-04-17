package store

import "fund-manager/internal/model"

func (s *Store) CreateChartAsset(c *model.ChartAsset) (int64, error) {
	res, err := s.DB.Exec(`
		INSERT INTO chart_asset (ticker,as_of,kind,timeframe,payload_json)
		VALUES (?,?,?,?,?)`,
		c.Ticker, c.AsOf, c.Kind, c.Timeframe, c.PayloadJSON)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListChartAssets(ticker, kind, since string, limit int) ([]*model.ChartAsset, error) {
	if limit <= 0 { limit = 50 }
	q := `SELECT id,ticker,as_of,kind,COALESCE(timeframe,''),payload_json FROM chart_asset WHERE 1=1`
	args := []any{}
	if ticker != "" { q += " AND ticker=?"; args = append(args, ticker) }
	if kind != "" { q += " AND kind=?"; args = append(args, kind) }
	if since != "" { q += " AND as_of>=?"; args = append(args, since) }
	q += " ORDER BY as_of DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.ChartAsset
	for rows.Next() {
		c := &model.ChartAsset{}
		if err := rows.Scan(&c.ID, &c.Ticker, &c.AsOf, &c.Kind, &c.Timeframe, &c.PayloadJSON); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, rows.Err()
}
