package store

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"sort"
)

type Store struct {
	DB *sql.DB
}

func New(dbPath string) (*Store, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	db.SetMaxOpenConns(1) // SQLite: single writer
	s := &Store{DB: db}
	if err := s.runMigrations("migrations"); err != nil {
		return nil, fmt.Errorf("migrations: %w", err)
	}
	return s, nil
}

func (s *Store) runMigrations(dir string) error {
	_, err := s.DB.Exec(`CREATE TABLE IF NOT EXISTS applied_migrations (
		name       TEXT PRIMARY KEY,
		applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)`)
	if err != nil {
		return err
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return fmt.Errorf("read migrations dir %q: %w", dir, err)
	}

	names := make([]string, 0, len(entries))
	for _, e := range entries {
		if filepath.Ext(e.Name()) == ".sql" {
			names = append(names, e.Name())
		}
	}
	sort.Strings(names)

	for _, name := range names {
		var exists int
		_ = s.DB.QueryRow(`SELECT COUNT(1) FROM applied_migrations WHERE name=?`, name).Scan(&exists)
		if exists == 1 {
			continue
		}
		b, err := os.ReadFile(filepath.Join(dir, name))
		if err != nil {
			return fmt.Errorf("read migration %s: %w", name, err)
		}
		if _, err := s.DB.Exec(string(b)); err != nil {
			return fmt.Errorf("apply migration %s: %w", name, err)
		}
		if _, err := s.DB.Exec(`INSERT INTO applied_migrations(name) VALUES(?)`, name); err != nil {
			return fmt.Errorf("record migration %s: %w", name, err)
		}
	}
	return nil
}

func (s *Store) Close() error {
	return s.DB.Close()
}
