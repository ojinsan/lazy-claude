package handlers

import (
	"net/http"
	"time"

	"fund-manager/internal/cache"
	"fund-manager/internal/model"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

func PortfolioRoutes(r chi.Router, s *store.Store, c *cache.Cache) {
	r.Get("/portfolio/snapshot", listSnapshots(s))
	r.Post("/portfolio/snapshot", upsertSnapshot(s))
	r.Get("/portfolio/holdings", listHoldings(s))
	r.Post("/portfolio/holdings", upsertHoldings(s))
	r.Get("/portfolio/current", currentPortfolio(s))
	r.Get("/transactions", listTransactions(s))
	r.Post("/transactions", createTransaction(s))
	r.Put("/transactions/{id}", updateTransaction(s))
	r.Get("/cache/price/{ticker}", getPrice(c))
	r.Post("/cache/price/{ticker}", setPrice(c))
}

func listSnapshots(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		from := queryStr(r, "from")
		to := queryStr(r, "to")
		if from == "" { from = "2000-01-01" }
		if to == "" { to = time.Now().Format("2006-01-02") }
		items, err := s.ListPortfolioSnapshots(from, to, queryInt(r, "limit", 60))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.PortfolioSnapshot{} }
		writeList(w, items, len(items))
	}
}

func upsertSnapshot(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var p model.PortfolioSnapshot
		if err := decode(r, &p); err != nil { writeError(w, 400, err.Error()); return }
		if p.Date == "" { writeError(w, 400, "date required"); return }
		if err := s.UpsertPortfolioSnapshot(&p); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 201, p)
	}
}

func listHoldings(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListHoldings(queryStr(r, "date"), queryStr(r, "ticker"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Holding{} }
		writeList(w, items, len(items))
	}
}

func upsertHoldings(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var batch []*model.Holding
		if err := decode(r, &batch); err != nil { writeError(w, 400, err.Error()); return }
		if err := s.UpsertHoldings(batch); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 201, map[string]int{"inserted": len(batch)})
	}
}

func currentPortfolio(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		snap, err := s.LatestPortfolioSnapshot()
		if err != nil { writeError(w, 500, err.Error()); return }
		if snap == nil { writeJSON(w, 200, map[string]any{}); return }
		holdings, err := s.ListHoldings(snap.Date, "")
		if err != nil { writeError(w, 500, err.Error()); return }
		if holdings == nil { holdings = []*model.Holding{} }
		writeJSON(w, 200, map[string]any{"snapshot": snap, "holdings": holdings})
	}
}

func listTransactions(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListTransactions(
			queryStr(r, "ticker"), queryInt(r, "days", 0), queryStr(r, "side"), queryInt(r, "limit", 100))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Transaction{} }
		writeList(w, items, len(items))
	}
}

func createTransaction(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var t model.Transaction
		if err := decode(r, &t); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateTransaction(&t)
		if err != nil { writeError(w, 500, err.Error()); return }
		t.ID = int(id)
		writeJSON(w, 201, t)
	}
}

func updateTransaction(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		idStr := chi.URLParam(r, "id")
		var body struct{ PnL float64 `json:"pnl"`; PnLPct float64 `json:"pnl_pct"` }
		if err := decode(r, &body); err != nil { writeError(w, 400, err.Error()); return }
		id, err2 := parseInt(idStr)
		if err2 != nil || id == 0 { writeError(w, 400, "bad id"); return }
		if err := s.UpdateTransaction(id, body.PnL, body.PnLPct); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 200, map[string]any{"id": id, "pnl": body.PnL, "pnl_pct": body.PnLPct})
	}
}

func getPrice(c *cache.Cache) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ticker := chi.URLParam(r, "ticker")
		var p model.Price
		if err := c.Get(r.Context(), "price:"+ticker, &p); err != nil {
			writeError(w, 404, "not cached"); return
		}
		writeJSON(w, 200, p)
	}
}

func setPrice(c *cache.Cache) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ticker := chi.URLParam(r, "ticker")
		var p model.Price
		if err := decode(r, &p); err != nil { writeError(w, 400, err.Error()); return }
		p.Ticker = ticker
		if err := c.Set(r.Context(), "price:"+ticker, p, 60*time.Second); err != nil {
			writeError(w, 500, err.Error()); return
		}
		writeJSON(w, 200, p)
	}
}

func parseInt(s string) (int, error) {
	n := 0
	for _, c := range s {
		if c < '0' || c > '9' { return 0, nil }
		n = n*10 + int(c-'0')
	}
	return n, nil
}
