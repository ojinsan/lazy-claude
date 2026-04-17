package handlers

import (
	"net/http"

	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

func StrategyRoutes(r chi.Router, s *store.Store) {
	// Tape states
	r.Get("/tape-states", listTapeStates(s))
	r.Post("/tape-states", createTapeState(s))

	// Confluence
	r.Get("/confluence", listConfluence(s))
	r.Post("/confluence", createConfluence(s))
	r.Get("/confluence/latest", latestConfluence(s))

	// Auto-trigger log
	r.Get("/auto-triggers", listAutoTriggers(s))
	r.Post("/auto-triggers", createAutoTrigger(s))

	// Konglo
	r.Get("/konglo/groups", listKongloGroups(s))
	r.Post("/konglo/groups", upsertKongloGroup(s))
	r.Get("/konglo/tickers/{ticker}", getKongloForTicker(s))
}

func listTapeStates(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListTapeStates(queryStr(r, "ticker"), queryStr(r, "composite"), queryStr(r, "since"), queryInt(r, "limit", 100))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*store.TapeState{} }
		writeList(w, items, len(items))
	}
}

func createTapeState(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var t store.TapeState
		if err := decode(r, &t); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateTapeState(&t)
		if err != nil { writeError(w, 500, err.Error()); return }
		t.ID = int(id)
		writeJSON(w, 201, t)
	}
}

func listConfluence(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListConfluenceScores(queryStr(r, "ticker"), queryStr(r, "bucket"), queryStr(r, "since"), queryInt(r, "limit", 100))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*store.ConfluenceScore{} }
		writeList(w, items, len(items))
	}
}

func createConfluence(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var c store.ConfluenceScore
		if err := decode(r, &c); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateConfluenceScore(&c)
		if err != nil { writeError(w, 500, err.Error()); return }
		c.ID = int(id)
		writeJSON(w, 201, c)
	}
}

func latestConfluence(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.LatestConfluencePerTicker()
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*store.ConfluenceScore{} }
		writeList(w, items, len(items))
	}
}

func listAutoTriggers(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListAutoTriggerLog(queryStr(r, "date"), queryStr(r, "outcome"), queryInt(r, "limit", 100))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*store.AutoTriggerLog{} }
		writeList(w, items, len(items))
	}
}

func createAutoTrigger(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var a store.AutoTriggerLog
		if err := decode(r, &a); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateAutoTriggerLog(&a)
		if err != nil { writeError(w, 500, err.Error()); return }
		a.ID = int(id)
		writeJSON(w, 201, a)
	}
}

func listKongloGroups(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListKongloGroups()
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*store.KongloGroup{} }
		writeList(w, items, len(items))
	}
}

func upsertKongloGroup(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var g store.KongloGroup
		if err := decode(r, &g); err != nil { writeError(w, 400, err.Error()); return }
		if err := s.UpsertKongloGroup(&g); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 201, g)
	}
}

func getKongloForTicker(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ticker := chi.URLParam(r, "ticker")
		items, err := s.GetKongloGroupForTicker(ticker)
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*store.KongloGroup{} }
		writeList(w, items, len(items))
	}
}
