package config

import (
	"os"
	"strconv"
)

type Config struct {
	DBPath    string
	RedisAddr string
	RedisDB   int
	Port      string
}

func Load() (*Config, error) {
	redisDB := 0
	if v := os.Getenv("REDIS_DB"); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			redisDB = n
		}
	}
	host := getenv("REDIS_HOST", "127.0.0.1")
	port := getenv("REDIS_PORT", "6379")
	return &Config{
		DBPath:    getenv("FUND_DB_PATH", "../data/fund.db"),
		RedisAddr: host + ":" + port,
		RedisDB:   redisDB,
		Port:      getenv("FUND_API_PORT", "8787"),
	}, nil
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
