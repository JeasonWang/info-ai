package router

import (
	"net/http"

	"info-serve/internal/admin"
	"info-serve/internal/auth"
	"info-serve/internal/events"
	"info-serve/internal/handler"
	"info-serve/internal/middleware"
)

// New 创建 info-serve 路由。
func New(services ...*auth.Service) http.Handler {
	authService := resolveAuthService(services...)
	return NewWithDependencies(authService, nil, nil)
}

// NewWithDependencies 创建带依赖注入的路由，便于服务启动和测试复用。
func NewWithDependencies(authService *auth.Service, eventService *events.Service, adminService *admin.Service) http.Handler {
	authService = resolveAuthService(authService)
	eventService = resolveEventService(eventService)
	adminService = resolveAdminService(adminService)
	authHandler := handler.NewAuthHandler(authService)
	eventHandler := handler.NewEventHandler(eventService)
	adminHandler := handler.NewAdminHandler(adminService)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handler.Health)
	mux.HandleFunc("GET /api/event-categories", eventHandler.Categories)
	mux.HandleFunc("GET /api/events", eventHandler.List)
	mux.HandleFunc("GET /api/events/", eventHandler.Detail)
	mux.HandleFunc("POST /api/auth/register", authHandler.Register)
	mux.HandleFunc("POST /api/auth/login", authHandler.Login)
	mux.HandleFunc("POST /api/auth/logout", authHandler.Logout)
	mux.HandleFunc("GET /api/me", authHandler.Me)
	mux.HandleFunc("GET /api/admin/health", middleware.RequireAdmin(authService, handler.AdminHealth))
	mux.HandleFunc("GET /api/admin/overview", middleware.RequireAdmin(authService, adminHandler.Overview))
	return mux
}

func resolveAuthService(services ...*auth.Service) *auth.Service {
	if len(services) > 0 && services[0] != nil {
		return services[0]
	}
	return auth.NewService(auth.NewMemoryStore())
}

func resolveEventService(service *events.Service) *events.Service {
	if service != nil {
		return service
	}
	return events.NewService(events.NewMemoryStore())
}

func resolveAdminService(service *admin.Service) *admin.Service {
	if service != nil {
		return service
	}
	return admin.NewService(admin.NewMemoryStore())
}
