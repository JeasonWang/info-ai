package config

import "testing"

func TestLoadConfigUsesDevelopmentDefaults(t *testing.T) {
	t.Setenv("INFO_SERVE_HTTP_ADDR", "")
	t.Setenv("INFO_SERVE_MYSQL_DSN", "")
	t.Setenv("INFO_SERVE_SESSION_SECRET", "")
	t.Setenv("REDIS_ADDR", "")
	t.Setenv("REDIS_PASSWORD", "")
	t.Setenv("REDIS_DB", "")
	t.Setenv("AGGREGATION_COMMAND_STREAM", "")
	t.Setenv("AGGREGATION_RESULT_PREFIX", "")
	t.Setenv("AGGREGATION_RESULT_WAIT_MS", "")
	t.Setenv("AGGREGATION_HTTP_BASE_URL", "")
	t.Setenv("AGGREGATION_LLM_TIMEOUT_MS", "")

	cfg := Load()

	if cfg.HTTPAddr != ":8085" {
		t.Fatalf("HTTPAddr = %q, want :8085", cfg.HTTPAddr)
	}
	if cfg.MySQLDSN != "root:root1234@tcp(localhost:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local" {
		t.Fatalf("MySQLDSN = %q", cfg.MySQLDSN)
	}
	if cfg.SessionSecret == "" {
		t.Fatal("SessionSecret should have a safe development default")
	}
	if cfg.RedisAddr != "127.0.0.1:6379" {
		t.Fatalf("RedisAddr = %q", cfg.RedisAddr)
	}
	if cfg.AggregationCommandStream != "info_ai:aggregation:commands" {
		t.Fatalf("AggregationCommandStream = %q", cfg.AggregationCommandStream)
	}
	if cfg.AggregationHTTPBaseURL != "http://127.0.0.1:8000" || cfg.AggregationLLMTimeoutMS != "240000" {
		t.Fatalf("aggregation http config = %+v", cfg)
	}
}

func TestLoadConfigReadsEnvironment(t *testing.T) {
	t.Setenv("INFO_SERVE_HTTP_ADDR", ":9090")
	t.Setenv("INFO_SERVE_MYSQL_DSN", "user:pass@tcp(localhost:3306)/custom")
	t.Setenv("INFO_SERVE_SESSION_SECRET", "secret")
	t.Setenv("REDIS_ADDR", "127.0.0.1:6380")
	t.Setenv("REDIS_PASSWORD", "secret-redis")
	t.Setenv("REDIS_DB", "2")
	t.Setenv("AGGREGATION_COMMAND_STREAM", "custom:commands")
	t.Setenv("AGGREGATION_RESULT_PREFIX", "custom:results:")
	t.Setenv("AGGREGATION_RESULT_WAIT_MS", "12000")
	t.Setenv("AGGREGATION_HTTP_BASE_URL", "http://aggregation:8000")
	t.Setenv("AGGREGATION_LLM_TIMEOUT_MS", "300000")

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
	if cfg.RedisAddr != "127.0.0.1:6380" || cfg.RedisPassword != "secret-redis" || cfg.RedisDB != "2" {
		t.Fatalf("redis config = %+v", cfg)
	}
	if cfg.AggregationCommandStream != "custom:commands" || cfg.AggregationResultPrefix != "custom:results:" || cfg.AggregationResultWaitMS != "12000" {
		t.Fatalf("aggregation redis config = %+v", cfg)
	}
	if cfg.AggregationHTTPBaseURL != "http://aggregation:8000" || cfg.AggregationLLMTimeoutMS != "300000" {
		t.Fatalf("aggregation http config = %+v", cfg)
	}
}
