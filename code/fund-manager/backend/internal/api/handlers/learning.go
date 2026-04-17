package handlers

import (
	"net/http"

	"fund-manager/internal/model"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
)

func LearningRoutes(r chi.Router, s *store.Store) {
	r.Get("/lessons", listLessons(s))
	r.Post("/lessons", createLesson(s))
	r.Get("/calibration", listCalibration(s))
	r.Post("/calibration", upsertCalibration(s))
	r.Get("/performance/daily", listPerformanceDaily(s))
	r.Post("/performance/daily", upsertPerformanceDaily(s))
	r.Get("/performance/summary", performanceSummary(s))
	r.Get("/evaluations", listEvaluations(s))
	r.Post("/evaluations", createEvaluation(s))
}

func listLessons(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListLessons(
			queryStr(r, "category"), queryStr(r, "severity"),
			queryStr(r, "pattern_tag"), queryInt(r, "days", 0), queryInt(r, "limit", 100))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Lesson{} }
		writeList(w, items, len(items))
	}
}

func createLesson(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var l model.Lesson
		if err := decode(r, &l); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateLesson(&l)
		if err != nil { writeError(w, 500, err.Error()); return }
		l.ID = int(id)
		writeJSON(w, 201, l)
	}
}

func listCalibration(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListCalibration()
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Calibration{} }
		writeList(w, items, len(items))
	}
}

func upsertCalibration(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var c model.Calibration
		if err := decode(r, &c); err != nil { writeError(w, 400, err.Error()); return }
		if err := s.UpsertCalibration(&c); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 201, c)
	}
}

func listPerformanceDaily(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListPerformanceDaily(queryStr(r, "from"), queryStr(r, "to"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.PerformanceDaily{} }
		writeList(w, items, len(items))
	}
}

func upsertPerformanceDaily(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var p model.PerformanceDaily
		if err := decode(r, &p); err != nil { writeError(w, 400, err.Error()); return }
		if err := s.UpsertPerformanceDaily(&p); err != nil { writeError(w, 500, err.Error()); return }
		writeJSON(w, 200, p)
	}
}

func performanceSummary(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		rows, err := s.ListPerformanceDaily("", "")
		if err != nil { writeError(w, 500, err.Error()); return }
		if len(rows) == 0 { writeJSON(w, 200, map[string]any{}); return }
		latest := rows[len(rows)-1]
		writeJSON(w, 200, map[string]any{
			"mtd_return":    latest.MTDReturn,
			"ytd_return":    latest.YTDReturn,
			"alpha":         latest.Alpha,
			"win_rate_90d":  latest.WinRate90d,
			"expectancy_90d": latest.Expectancy90d,
		})
	}
}

func listEvaluations(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		items, err := s.ListEvaluations(queryStr(r, "period"), queryStr(r, "period_key"))
		if err != nil { writeError(w, 500, err.Error()); return }
		if items == nil { items = []*model.Evaluation{} }
		writeList(w, items, len(items))
	}
}

func createEvaluation(s *store.Store) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var e model.Evaluation
		if err := decode(r, &e); err != nil { writeError(w, 400, err.Error()); return }
		id, err := s.CreateEvaluation(&e)
		if err != nil { writeError(w, 500, err.Error()); return }
		e.ID = int(id)
		writeJSON(w, 201, e)
	}
}
