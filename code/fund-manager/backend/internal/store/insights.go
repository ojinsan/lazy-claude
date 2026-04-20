package store

import (
	"fund-manager/internal/model"
	"regexp"
	"strings"
)

// tickerRe matches 4-character uppercase IDX tickers (e.g. BBRI, ANTM)
var tickerRe = regexp.MustCompile(`\b([A-Z]{4})\b`)

// extractTickers pulls ticker mentions from address_text or content.
// Returns first ticker found, or empty string.
func extractTickers(addressText, content string) []string {
	src := addressText
	if src == "" {
		src = content
	}
	matches := tickerRe.FindAllString(src, -1)
	seen := map[string]bool{}
	out := []string{}
	for _, m := range matches {
		// Skip common false positives
		skip := map[string]bool{
			"STOP": true, "TAKE": true, "SELL": true, "HOLD": true,
			"WAIT": true, "OPEN": true, "GOOD": true, "HIGH": true,
			"RISK": true, "GAIN": true, "LOSS": true, "FROM": true,
			"WITH": true, "THAT": true, "THIS": true, "HAVE": true,
			"BEEN": true, "WILL": true, "THEN": true, "WHEN": true,
		}
		if skip[strings.ToUpper(m)] {
			continue
		}
		if !seen[m] {
			seen[m] = true
			out = append(out, m)
		}
	}
	return out
}

// IngestInsights stores a batch of telegram insights.
// Each InsightInput may produce multiple rows if multiple tickers are found.
// If no ticker is extracted, stores one row with ticker="".
func (s *Store) IngestInsights(inputs []model.InsightInput) (int64, error) {
	var total int64
	for _, inp := range inputs {
		tickers := extractTickers(inp.AddressText, inp.Content)
		if len(tickers) == 0 {
			tickers = []string{""}
		}
		for _, ticker := range tickers {
			res, err := s.DB.Exec(`
				INSERT INTO insight (occurred_at, ticker, content, participant_type,
				                     ai_recap, confidence, address_text, source, topic)
				VALUES (?,?,?,?,?,?,?,?,?)`,
				inp.Time, ticker, inp.Content, inp.ParticipantType,
				"", inp.Confidence, inp.AddressText, inp.Source, inp.Topic,
			)
			if err != nil {
				return total, err
			}
			if _, err := res.LastInsertId(); err == nil {
				total++
			}
		}
	}
	return total, nil
}

// PositiveCandidates returns high-confidence tickers from recent insights.
func (s *Store) PositiveCandidates(minConfidence, days int) ([]*model.PositiveCandidate, error) {
	if minConfidence <= 0 {
		minConfidence = 60
	}
	if days <= 0 {
		days = 3
	}
	rows, err := s.DB.Query(`
		SELECT ticker, MAX(confidence), COUNT(*), MAX(occurred_at), source
		FROM insight
		WHERE ticker != ''
		  AND confidence >= ?
		  AND occurred_at >= datetime('now', '-' || ? || ' days')
		GROUP BY ticker
		ORDER BY MAX(confidence) DESC, COUNT(*) DESC
		LIMIT 50`,
		minConfidence, days,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []*model.PositiveCandidate
	for rows.Next() {
		c := &model.PositiveCandidate{}
		if err := rows.Scan(&c.Ticker, &c.MaxConf, &c.Count, &c.LatestAt, &c.Source); err != nil {
			return nil, err
		}
		out = append(out, c)
	}
	return out, rows.Err()
}

// LastInsightAt returns the MAX(occurred_at) across all insights, or "" when empty.
func (s *Store) LastInsightAt() (string, error) {
	var ts *string
	err := s.DB.QueryRow(`SELECT MAX(occurred_at) FROM insight`).Scan(&ts)
	if err != nil {
		return "", err
	}
	if ts == nil {
		return "", nil
	}
	return *ts, nil
}

// RAGSearch performs FTS5 full-text search over insights.
func (s *Store) RAGSearch(query string, limit int) ([]*model.Insight, error) {
	if limit <= 0 {
		limit = 20
	}
	rows, err := s.DB.Query(`
		SELECT i.id, i.occurred_at, i.ticker, i.content, i.participant_type,
		       i.ai_recap, i.confidence, i.address_text, i.source, i.topic, i.created_at
		FROM insight i
		JOIN insight_fts f ON i.id = f.rowid
		WHERE insight_fts MATCH ?
		ORDER BY rank
		LIMIT ?`,
		query, limit,
	)
	if err != nil {
		// Fallback to LIKE search if FTS fails (e.g. table not migrated yet)
		return s.ragSearchLike(query, limit)
	}
	defer rows.Close()
	return scanInsights(rows)
}

func (s *Store) ragSearchLike(query string, limit int) ([]*model.Insight, error) {
	like := "%" + query + "%"
	rows, err := s.DB.Query(`
		SELECT id, occurred_at, ticker, content, participant_type,
		       ai_recap, confidence, address_text, source, topic, created_at
		FROM insight
		WHERE content LIKE ? OR ai_recap LIKE ? OR ticker LIKE ?
		ORDER BY occurred_at DESC
		LIMIT ?`,
		like, like, like, limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanInsights(rows)
}

func scanInsights(rows interface {
	Next() bool
	Scan(...any) error
	Err() error
	Close() error
}) ([]*model.Insight, error) {
	var out []*model.Insight
	for rows.Next() {
		ins := &model.Insight{}
		if err := rows.Scan(&ins.ID, &ins.OccurredAt, &ins.Ticker, &ins.Content,
			&ins.ParticipantType, &ins.AIRecap, &ins.Confidence,
			&ins.AddressText, &ins.Source, &ins.Topic, &ins.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, ins)
	}
	return out, rows.Err()
}
