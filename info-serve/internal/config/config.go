package config

import "os"

// Config 保存 info-serve 的运行配置。
type Config struct {
	HTTPAddr                 string
	MySQLDSN                 string
	SessionSecret            string
	RedisAddr                string
	RedisPassword            string
	RedisDB                  string
	AggregationCommandStream string
	AggregationResultPrefix  string
	AggregationResultWaitMS  string
	AggregationHTTPBaseURL   string
	AggregationLLMTimeoutMS  string
}

// Load 从环境变量读取配置，并提供本地开发默认值。
func Load() Config {
	return Config{
		HTTPAddr:                 readEnv("INFO_SERVE_HTTP_ADDR", ":8085"),
		MySQLDSN:                 readEnv("INFO_SERVE_MYSQL_DSN", "root:root1234@tcp(localhost:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local"),
		SessionSecret:            readEnv("INFO_SERVE_SESSION_SECRET", "info-serve-development-session-secret"),
		RedisAddr:                readEnv("REDIS_ADDR", "127.0.0.1:6379"),
		RedisPassword:            readEnv("REDIS_PASSWORD", ""),
		RedisDB:                  readEnv("REDIS_DB", "0"),
		AggregationCommandStream: readEnv("AGGREGATION_COMMAND_STREAM", "info_ai:aggregation:commands"),
		AggregationResultPrefix:  readEnv("AGGREGATION_RESULT_PREFIX", "info_ai:aggregation:results:"),
		AggregationResultWaitMS:  readEnv("AGGREGATION_RESULT_WAIT_MS", "5000"),
		AggregationHTTPBaseURL:   readEnv("AGGREGATION_HTTP_BASE_URL", "http://127.0.0.1:8000"),
		AggregationLLMTimeoutMS:  readEnv("AGGREGATION_LLM_TIMEOUT_MS", "240000"),
	}
}

func readEnv(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}
