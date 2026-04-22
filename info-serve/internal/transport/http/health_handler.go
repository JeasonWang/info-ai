package transporthttp

import (
	"net/http"
	"time"

	"info-serve/internal/response"
)

// Health 返回服务健康状态，用于本地调试、网关探活和后续监控接入。
func Health(w http.ResponseWriter, r *http.Request) {
	response.OK(w, map[string]string{
		"service":   "info-serve",
		"status":    "running",
		"timestamp": time.Now().Format("2006-01-02 15:04:05"),
	})
}
