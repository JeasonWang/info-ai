package config

import "os"

// Config 保存 info-serve 的运行配置。
type Config struct {
	HTTPAddr           string
	MySQLDSN           string
	SessionSecret      string
	AggregationBaseURL string
}

// Load 从环境变量读取配置，并提供本地开发默认值。
func Load() Config {
	return Config{
		HTTPAddr:           readEnv("INFO_SERVE_HTTP_ADDR", ":8080"),
		MySQLDSN:           readEnv("INFO_SERVE_MYSQL_DSN", "root:root1234@tcp(localhost:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local"),
		SessionSecret:      readEnv("INFO_SERVE_SESSION_SECRET", "info-serve-development-session-secret"),
		AggregationBaseURL: readEnv("INFO_AGGREGATION_BASE_URL", "http://localhost:8000"),
	}
}

func readEnv(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}
