package api

import (
	"encoding/json"
	"net/http"

	"fund-manager/internal/api/handlers"
	"fund-manager/internal/cache"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

func Mount(r chi.Router, s *store.Store, c *cache.Cache) {
	r.Get("/healthz", Health)
	r.Route("/api/v1", func(r chi.Router) {
		handlers.PortfolioRoutes(r, s, c)
		handlers.PlanningRoutes(r, s)
		handlers.SignalsRoutes(r, s, c)
		handlers.LearningRoutes(r, s)
		handlers.ChartsRoutes(r, s)
	})
}

func Health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
