package router

import (
	"net/http"

	"info-serve/internal/auth"
	"info-serve/internal/handler"
	"info-serve/internal/middleware"
)

// New 创建 info-serve 路由。
func New(services ...*auth.Service) http.Handler {
	authService := resolveAuthService(services...)
	authHandler := handler.NewAuthHandler(authService)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handler.Health)
	mux.HandleFunc("POST /api/auth/register", authHandler.Register)
	mux.HandleFunc("POST /api/auth/login", authHandler.Login)
	mux.HandleFunc("POST /api/auth/logout", authHandler.Logout)
	mux.HandleFunc("GET /api/me", authHandler.Me)
	mux.HandleFunc("GET /api/admin/health", middleware.RequireAdmin(authService, handler.AdminHealth))
	return mux
}

func resolveAuthService(services ...*auth.Service) *auth.Service {
	if len(services) > 0 && services[0] != nil {
		return services[0]
	}
	return auth.NewService(auth.NewMemoryStore())
}
