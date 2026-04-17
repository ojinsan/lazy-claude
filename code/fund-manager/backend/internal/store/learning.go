package store

import (
	"fmt"

	"fund-manager/internal/model"
)

func (s *Store) CreateLesson(l *model.Lesson) (int64, error) {
	res, err := s.DB.Exec(`
		INSERT INTO lesson (date,category,severity,pattern_tag,tickers,related_thesis,lesson_text,source_trade_id)
		VALUES (?,?,?,?,?,?,?,?)`,
		l.Date, l.Category, l.Severity, l.PatternTag, l.Tickers, l.RelatedThesis,
		l.LessonText, nullInt(l.SourceTradeID))
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListLessons(category, severity, patternTag string, days, limit int) ([]*model.Lesson, error) {
	if limit <= 0 { limit = 100 }
	q := `SELECT id,date,category,severity,COALESCE(pattern_tag,''),COALESCE(tickers,''),
	      COALESCE(related_thesis,''),lesson_text,COALESCE(source_trade_id,0)
	      FROM lesson WHERE 1=1`
	args := []any{}
	if category != "" { q += " AND category=?"; args = append(args, category) }
	if severity != "" { q += " AND severity=?"; args = append(args, severity) }
	if patternTag != "" { q += " AND pattern_tag=?"; args = append(args, patternTag) }
	if days > 0 { q += fmt.Sprintf(" AND date >= date('now','-%d days')", days) }
	q += " ORDER BY date DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Lesson
	for rows.Next() {
		l := &model.Lesson{}
		if err := rows.Scan(&l.ID, &l.Date, &l.Category, &l.Severity, &l.PatternTag,
			&l.Tickers, &l.RelatedThesis, &l.LessonText, &l.SourceTradeID); err != nil {
			return nil, err
		}
		out = append(out, l)
	}
	return out, rows.Err()
}

func (s *Store) UpsertCalibration(c *model.Calibration) error {
	_, err := s.DB.Exec(`
		INSERT INTO calibration (run_date,bucket,declared_win_rate,actual_win_rate,drift,n_trades,window_days)
		VALUES (?,?,?,?,?,?,?)
		ON CONFLICT(run_date,bucket,window_days) DO UPDATE SET
		  declared_win_rate=excluded.declared_win_rate, actual_win_rate=excluded.actual_win_rate,
		  drift=excluded.drift, n_trades=excluded.n_trades`,
		c.RunDate, c.Bucket, c.DeclaredWinRate, c.ActualWinRate, c.Drift, c.NTrades, c.WindowDays)
	return err
}

func (s *Store) ListCalibration() ([]*model.Calibration, error) {
	rows, err := s.DB.Query(`
		SELECT run_date,bucket,COALESCE(declared_win_rate,0),COALESCE(actual_win_rate,0),
		COALESCE(drift,0),n_trades,window_days FROM calibration ORDER BY run_date DESC`)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Calibration
	for rows.Next() {
		c := &model.Calibration{}
		if err := rows.Scan(&c.RunDate, &c.Bucket, &c.DeclaredWinRate, &c.ActualWinRate,
			&c.Drift, &c.NTrades, &c.WindowDays); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, rows.Err()
}

func (s *Store) UpsertPerformanceDaily(p *model.PerformanceDaily) error {
	_, err := s.DB.Exec(`
		INSERT INTO performance_daily (date,equity,ihsg_close,daily_return,ihsg_return,alpha,mtd_return,ytd_return,win_rate_90d,avg_r_90d,expectancy_90d)
		VALUES (?,?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(date) DO UPDATE SET
		  equity=excluded.equity, ihsg_close=excluded.ihsg_close, daily_return=excluded.daily_return,
		  ihsg_return=excluded.ihsg_return, alpha=excluded.alpha, mtd_return=excluded.mtd_return,
		  ytd_return=excluded.ytd_return, win_rate_90d=excluded.win_rate_90d,
		  avg_r_90d=excluded.avg_r_90d, expectancy_90d=excluded.expectancy_90d`,
		p.Date, p.Equity, p.IHSGClose, p.DailyReturn, p.IHSGReturn, p.Alpha,
		p.MTDReturn, p.YTDReturn, p.WinRate90d, p.AvgR90d, p.Expectancy90d)
	return err
}

func (s *Store) ListPerformanceDaily(from, to string) ([]*model.PerformanceDaily, error) {
	q := `SELECT date,equity,COALESCE(ihsg_close,0),COALESCE(daily_return,0),COALESCE(ihsg_return,0),
	      COALESCE(alpha,0),COALESCE(mtd_return,0),COALESCE(ytd_return,0),COALESCE(win_rate_90d,0),
	      COALESCE(avg_r_90d,0),COALESCE(expectancy_90d,0) FROM performance_daily WHERE 1=1`
	args := []any{}
	if from != "" { q += " AND date>=?"; args = append(args, from) }
	if to != "" { q += " AND date<=?"; args = append(args, to) }
	q += " ORDER BY date ASC"
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.PerformanceDaily
	for rows.Next() {
		p := &model.PerformanceDaily{}
		if err := rows.Scan(&p.Date, &p.Equity, &p.IHSGClose, &p.DailyReturn, &p.IHSGReturn,
			&p.Alpha, &p.MTDReturn, &p.YTDReturn, &p.WinRate90d, &p.AvgR90d, &p.Expectancy90d); err != nil {
			return nil, err
		}
		out = append(out, p)
	}
	return out, rows.Err()
}

func (s *Store) CreateEvaluation(e *model.Evaluation) (int64, error) {
	res, err := s.DB.Exec(`
		INSERT INTO evaluation (period,period_key,generated_at,body_md,kpi_json)
		VALUES (?,?,?,?,?)
		ON CONFLICT(period,period_key) DO UPDATE SET
		  generated_at=excluded.generated_at, body_md=excluded.body_md, kpi_json=excluded.kpi_json`,
		e.Period, e.PeriodKey, e.GeneratedAt, e.BodyMD, e.KPIJson)
	if err != nil { return 0, err }
	return res.LastInsertId()
}

func (s *Store) ListEvaluations(period, periodKey string) ([]*model.Evaluation, error) {
	q := `SELECT id,period,period_key,generated_at,body_md,kpi_json FROM evaluation WHERE 1=1`
	args := []any{}
	if period != "" { q += " AND period=?"; args = append(args, period) }
	if periodKey != "" { q += " AND period_key=?"; args = append(args, periodKey) }
	q += " ORDER BY generated_at DESC"
	rows, err := s.DB.Query(q, args...)
	if err != nil { return nil, err }
	defer rows.Close()
	var out []*model.Evaluation
	for rows.Next() {
		e := &model.Evaluation{}
		if err := rows.Scan(&e.ID, &e.Period, &e.PeriodKey, &e.GeneratedAt, &e.BodyMD, &e.KPIJson); err != nil {
			return nil, err
		}
		out = append(out, e)
	}
	return out, rows.Err()
}

func nullInt(v int) any {
	if v == 0 { return nil }
	return v
}
