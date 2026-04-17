package handlers

import (
	"net/http"

	"fund-manager/internal/model"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

func ChartsRoutes(r chi.Router, s *store.Store) {
	r.Get("/charts", listCharts(s))
	r.Post("/charts", createChart(s))
}

func listCharts(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListChartAssets(
			queryStr(r, "ticker"), queryStr(r, "kind"),
			queryStr(r, "since"), queryInt(r, "limit", 50))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.ChartAsset{} }
		writeList(w, items, len(items))
	}
}

func createChart(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var c model.ChartAsset
		if err := decode(r, &c); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateChartAsset(&c)
		if err != nil { writeError(w, 500, err.Error()); return }
		c.ID = int(id)
		writeJSON(w, 201, c)
	}
}
