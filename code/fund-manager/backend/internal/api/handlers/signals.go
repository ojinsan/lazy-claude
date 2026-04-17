package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"fund-manager/internal/cache"
	"fund-manager/internal/model"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

func SignalsRoutes(r chi.Router, s *store.Store, c *cache.Cache) {
	r.Get("/signals", listSignals(s))
	r.Post("/signals", createSignal(s, c))
	r.Get("/signals/recent", recentSignals(s))
	r.Get("/signals/stream", signalStream(c))

	r.Get("/layer-outputs", listLayerOutputs(s))
	r.Post("/layer-outputs", createLayerOutput(s))

	r.Get("/daily-notes/{date}", getDailyNote(s))
	r.Put("/daily-notes/{date}", putDailyNote(s))
}

func listSignals(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListSignals(
			queryStr(r, "ticker"), queryStr(r, "layer"),
			queryStr(r, "kind"), queryStr(r, "since"), queryInt(r, "limit", 100))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Signal{} }
		writeList(w, items, len(items))
	}
}

func createSignal(s *store.Store, c *cache.Cache) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var sig model.Signal
		if err := decode(r, &sig); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateSignal(&sig)
		if err != nil { writeError(w, 500, err.Error()); return }
		sig.ID = int(id)
		// push to signal queue for SSE
		_ = c.Push(r.Context(), "signal_queue", sig)
		writeJSON(w, 201, sig)
	}
}

func recentSignals(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListSignals("", "", "", "", 100)
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Signal{} }
		writeList(w, items, len(items))
	}
}

func signalStream(c *cache.Cache) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		flusher, ok := w.(http.Flusher)
		if !ok { writeError(w, 500, "streaming not supported"); return }
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")
		ctx := r.Context()
		for {
			var sig model.Signal
			err := c.Pop(ctx, "signal_queue", &sig)
			if ctx.Err() != nil { return }
			if err != nil { continue }
			if _, err := w.Write([]byte("data: ")); err != nil { return }
			if err := jsonWrite(w, sig); err != nil { return }
			if _, err := w.Write([]byte("\n\n")); err != nil { return }
			flusher.Flush()
		}
	}
}

func listLayerOutputs(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListLayerOutputs(
			queryStr(r, "run_date"), queryStr(r, "layer"),
			queryStr(r, "severity"), queryInt(r, "limit", 100))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.LayerOutput{} }
		writeList(w, items, len(items))
	}
}

func createLayerOutput(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var lo model.LayerOutput
		if err := decode(r, &lo); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateLayerOutput(&lo)
		if err != nil { writeError(w, 500, err.Error()); return }
		lo.ID = int(id)
		writeJSON(w, 201, lo)
	}
}

func getDailyNote(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		n, err := s.GetDailyNote(chi.URLParam(r, "date"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if n == nil { writeError(w, 404, "not found"); return }
		writeJSON(w, 200, n)
	}
}

func putDailyNote(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		date := chi.URLParam(r, "date")
		var body struct{ BodyMD string `json:"body_md"` }
		if err := decode(r, &body); err != nil { writeError(w, 400, err.Error()); return }
		n := &model.DailyNote{Date: date, BodyMD: body.BodyMD, UpdatedAt: time.Now().UTC().Format(time.RFC3339)}
		if err := s.UpsertDailyNote(n); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 200, n)
	}
}

func jsonWrite(w http.ResponseWriter, v any) error {
	return json.NewEncoder(w).Encode(v)
}
