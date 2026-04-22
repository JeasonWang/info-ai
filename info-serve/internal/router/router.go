package router

import (
	"net/http"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/events"
	"info-serve/internal/handler"
	"info-serve/internal/middleware"
)

// New 创建 info-serve 路由。
func New(services ...*auth.Service) http.Handler {
	authService := resolveAuthService(services...)
	return NewWithDependencies(authService, nil, nil, nil)
}

// NewWithDependencies 创建带依赖注入的路由，便于服务启动和测试复用。
func NewWithDependencies(authService *auth.Service, eventService *events.Service, adminService *admin.Service, auditService *audit.Service) http.Handler {
	authService = resolveAuthService(authService)
	eventService = resolveEventService(eventService)
	adminService = resolveAdminService(adminService)
	auditService = resolveAuditService(auditService)
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
	mux.HandleFunc("GET /api/admin/health", middleware.RequireAdminWithAudit(authService, auditService, handler.AdminHealth))
	mux.HandleFunc("GET /api/admin/overview", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.Overview))
	mux.HandleFunc("GET /api/admin/crawl-runs", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.CrawlRuns))
	mux.HandleFunc("GET /api/admin/quality-snapshots", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.QualitySnapshots))
	mux.HandleFunc("GET /api/admin/crawl-tasks", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.CrawlTasks))
	mux.HandleFunc("GET /api/admin/categories", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.Categories))
	mux.HandleFunc("POST /api/admin/categories", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateCategory))
	mux.HandleFunc("PUT /api/admin/categories/{id}", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateCategory))
	mux.HandleFunc("GET /api/admin/channels", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.Channels))
	mux.HandleFunc("POST /api/admin/channels", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateChannel))
	mux.HandleFunc("PUT /api/admin/channels/{id}", middleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateChannel))
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

func resolveAuditService(service *audit.Service) *audit.Service {
	if service != nil {
		return service
	}
	return audit.NewService(audit.NewMemoryStore())
}
