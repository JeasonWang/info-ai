package config

import "testing"

func TestLoadConfigUsesDevelopmentDefaults(t *testing.T) {
	t.Setenv("INFO_SERVE_HTTP_ADDR", "")
	t.Setenv("INFO_SERVE_MYSQL_DSN", "")
	t.Setenv("INFO_SERVE_SESSION_SECRET", "")

	cfg := Load()

	if cfg.HTTPAddr != ":8080" {
		t.Fatalf("HTTPAddr = %q, want :8080", cfg.HTTPAddr)
	}
	if cfg.MySQLDSN != "root:root1234@tcp(localhost:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local" {
		t.Fatalf("MySQLDSN = %q", cfg.MySQLDSN)
	}
	if cfg.SessionSecret == "" {
		t.Fatal("SessionSecret should have a safe development default")
	}
}

func TestLoadConfigReadsEnvironment(t *testing.T) {
	t.Setenv("INFO_SERVE_HTTP_ADDR", ":9090")
	t.Setenv("INFO_SERVE_MYSQL_DSN", "user:pass@tcp(localhost:3306)/custom")
	t.Setenv("INFO_SERVE_SESSION_SECRET", "secret")

	cfg := Load()

	if cfg.HTTPAddr != ":9090" {
		t.Fatalf("HTTPAddr = %q", cfg.HTTPAddr)
	}
	if cfg.MySQLDSN != "user:pass@tcp(localhost:3306)/custom" {
		t.Fatalf("MySQLDSN = %q", cfg.MySQLDSN)
	}
	if cfg.SessionSecret != "secret" {
		t.Fatalf("SessionSecret = %q", cfg.SessionSecret)
	}
}
