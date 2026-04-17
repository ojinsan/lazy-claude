package api

import (
	"encoding/json"
	"net/http"

	"fund-manager/internal/cache"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

func Mount(r chi.Router, s *store.Store, c *cache.Cache) {
	r.Get("/healthz", Health)
	r.Route("/api/v1", func(r chi.Router) {
		// Handlers mounted in later phases
		_ = s
		_ = c
	})
}

func Health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
