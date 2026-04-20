package handlers

import (
	"encoding/json"
	"net/http"
	"strconv"

	"fund-manager/internal/model"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

// InsightsFeedRoutes mounts at root (not /api/v1) — matches telegram scraper target.
func InsightsFeedRoutes(r chi.Router, s *store.Store) {
	r.Post("/feed/telegram/insight", ingestTelegramInsight(s))
}

// InsightsQueryRoutes mounts under /api/v1.
func InsightsQueryRoutes(r chi.Router, s *store.Store) {
	r.Get("/insights/positive-candidates", positiveCandidates(s))
	r.Get("/insights/last", lastInsight(s))
	r.Post("/rag/search", ragSearch(s))
}

func lastInsight(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ts, err := s.LastInsightAt()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"last_insight_at": ts})
	}
}

func ingestTelegramInsight(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var body model.InsightIngestion
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, "bad request: "+err.Error(), http.StatusBadRequest)
			return
		}
		if len(body.Insights) == 0 {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		n, err := s.IngestInsights(body.Insights)
		if err != nil {
			http.Error(w, "store error: "+err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"stored": n})
	}
}

func positiveCandidates(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		minConf, _ := strconv.Atoi(r.URL.Query().Get("min_confidence"))
		days, _ := strconv.Atoi(r.URL.Query().Get("days"))
		candidates, err := s.PositiveCandidates(minConf, days)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		if candidates == nil {
			candidates = []*model.PositiveCandidate{}
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(candidates)
	}
}

func ragSearch(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			Query string `json:"query"`
			Limit int    `json:"limit"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "bad request: "+err.Error(), http.StatusBadRequest)
			return
		}
		if req.Query == "" {
			http.Error(w, "query required", http.StatusBadRequest)
			return
		}
		results, err := s.RAGSearch(req.Query, req.Limit)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		if results == nil {
			results = []*model.Insight{}
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(results)
	}
}
