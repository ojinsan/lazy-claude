package handlers

import (
	"net/http"

	"fund-manager/internal/model"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

func PlanningRoutes(r chi.Router, s *store.Store) {
	r.Get("/watchlist", listWatchlist(s))
	r.Post("/watchlist", upsertWatchlist(s))
	r.Delete("/watchlist/{ticker}", archiveWatchlist(s))

	r.Get("/thesis", listThesis(s))
	r.Get("/thesis/{ticker}", getThesis(s))
	r.Post("/thesis", upsertThesis(s))
	r.Put("/thesis/{ticker}", upsertThesisByTicker(s))
	r.Get("/thesis/{ticker}/review", listThesisReviews(s))
	r.Post("/thesis/{ticker}/review", appendThesisReview(s))

	r.Get("/themes", listThemes(s))
	r.Post("/themes", upsertTheme(s))

	r.Get("/tradeplans", listTradePlans(s))
	r.Post("/tradeplans", createTradePlan(s))
	r.Put("/tradeplans/{id}", updateTradePlan(s))
}

func listWatchlist(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListWatchlist(queryStr(r, "status"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Watchlist{} }
		writeList(w, items, len(items))
	}
}

func upsertWatchlist(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var wl model.Watchlist
		if err := decode(r, &wl); err != nil { writeError(w, 400, err.Error()); return }
		if err := s.UpsertWatchlist(&wl); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 201, wl)
	}
}

func archiveWatchlist(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if err := s.DeleteWatchlist(chi.URLParam(r, "ticker")); err != nil {
			writeError(w, 500, err.Error()); return
		}
		w.WriteHeader(204)
	}
}

func listThesis(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListThesis(queryStr(r, "status"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Thesis{} }
		writeList(w, items, len(items))
	}
}

func getThesis(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		t, err := s.GetThesis(chi.URLParam(r, "ticker"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if t == nil { writeError(w, 404, "not found"); return }
		writeJSON(w, 200, t)
	}
}

func upsertThesis(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var t model.Thesis
		if err := decode(r, &t); err != nil { writeError(w, 400, err.Error()); return }
		if err := s.UpsertThesis(&t); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 201, t)
	}
}

func upsertThesisByTicker(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var t model.Thesis
		if err := decode(r, &t); err != nil { writeError(w, 400, err.Error()); return }
		t.Ticker = chi.URLParam(r, "ticker")
		if err := s.UpsertThesis(&t); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 200, t)
	}
}

func listThesisReviews(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListThesisReviews(chi.URLParam(r, "ticker"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.ThesisReview{} }
		writeList(w, items, len(items))
	}
}

func appendThesisReview(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var rev model.ThesisReview
		if err := decode(r, &rev); err != nil { writeError(w, 400, err.Error()); return }
		rev.Ticker = chi.URLParam(r, "ticker")
		id, err := s.AppendThesisReview(&rev)
		if err != nil { writeError(w, 500, err.Error()); return }
		rev.ID = int(id)
		writeJSON(w, 201, rev)
	}
}

func listThemes(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListThemes(queryStr(r, "status"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Theme{} }
		writeList(w, items, len(items))
	}
}

func upsertTheme(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var t model.Theme
		if err := decode(r, &t); err != nil { writeError(w, 400, err.Error()); return }
		if err := s.UpsertTheme(&t); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 201, t)
	}
}

func listTradePlans(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListTradePlans(
			queryStr(r, "plan_date"), queryStr(r, "ticker"),
			queryStr(r, "status"), queryStr(r, "level"), queryInt(r, "limit", 50))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.TradePlan{} }
		writeList(w, items, len(items))
	}
}

func createTradePlan(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var p model.TradePlan
		if err := decode(r, &p); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateTradePlan(&p)
		if err != nil { writeError(w, 500, err.Error()); return }
		p.ID = int(id)
		writeJSON(w, 201, p)
	}
}

func updateTradePlan(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id, err := parseInt(chi.URLParam(r, "id"))
		if err != nil || id == 0 { writeError(w, 400, "bad id"); return }
		var body struct{ Status string `json:"status"` }
		if err := decode(r, &body); err != nil { writeError(w, 400, err.Error()); return }
		if err := s.UpdateTradePlanStatus(id, body.Status); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 200, map[string]any{"id": id, "status": body.Status})
	}
}
