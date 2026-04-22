package router

import (
	"net/http"

	"info-serve/internal/handler"
)

// New 创建 info-serve 路由。
func New() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handler.Health)
	mux.HandleFunc("POST /api/auth/register", handler.Register)
	return mux
}
