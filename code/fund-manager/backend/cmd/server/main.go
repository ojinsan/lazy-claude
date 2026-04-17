package main

import (
	"log"
	"net/http"

	"fund-manager/internal/api"
	"fund-manager/internal/cache"
	"fund-manager/internal/config"
	"fund-manager/internal/lark"
	"fund-manager/internal/store"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/joho/godotenv"
	_ "modernc.org/sqlite"
)

func main() {
	_ = godotenv.Load("../../.env.local")

	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config: %v", err)
	}

	s, err := store.New(cfg.DBPath)
	if err != nil {
		log.Fatalf("store: %v", err)
	}
	defer s.Close()
	log.Println("sqlite: connected →", cfg.DBPath)

	c, err := cache.New(cfg.RedisAddr, cfg.RedisDB)
	if err != nil {
		log.Fatalf("cache: %v", err)
	}
	defer c.Close()
	log.Println("redis: connected →", cfg.RedisAddr)

	// Build Lark client (optional — falls back gracefully if env vars not set)
	lc := lark.New(lark.Config{
		AppID:      cfg.LarkAppID,
		AppSecret:  cfg.LarkAppSecret,
		SheetToken: cfg.LarkSheetToken,
		WikiToken:  cfg.LarkWikiToken,
		Range:      cfg.LarkRange,
	})
	if lc.Configured() {
		log.Println("lark: watchlist client configured")
	} else {
		log.Println("lark: not configured — watchlist will use local SQLite only")
	}

	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	api.Mount(r, s, c, lc)

	addr := "127.0.0.1:" + cfg.Port
	log.Printf("fund-manager listening on %s", addr)
	if err := http.ListenAndServe(addr, r); err != nil {
		log.Fatal(err)
	}
}
