package transporthttp

import (
	"net/http"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/events"
	transportmiddleware "info-serve/internal/transport/http/middleware"
)

// Services 是 HTTP 层依赖的业务服务集合。
type Services struct {
	Auth   *auth.Service
	Events *events.Service
	Admin  *admin.Service
	Audit  *audit.Service
}

// NewRouter 创建 info-serve HTTP 路由。
func NewRouter(services Services) http.Handler {
	authService := resolveAuthService(services.Auth)
	eventService := resolveEventService(services.Events)
	adminService := resolveAdminService(services.Admin)
	auditService := resolveAuditService(services.Audit)

	authHandler := NewAuthHandler(authService)
	eventHandler := NewEventHandler(eventService)
	adminHandler := NewAdminHandler(adminService)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", Health)
	mux.HandleFunc("GET /api/event-categories", eventHandler.Categories)
	mux.HandleFunc("GET /api/events", eventHandler.List)
	mux.HandleFunc("GET /api/events/", eventHandler.Detail)
	mux.HandleFunc("POST /api/auth/register", authHandler.Register)
	mux.HandleFunc("POST /api/auth/login", authHandler.Login)
	mux.HandleFunc("POST /api/auth/logout", authHandler.Logout)
	mux.HandleFunc("GET /api/me", authHandler.Me)
	mux.HandleFunc("GET /api/admin/health", transportmiddleware.RequireAdminWithAudit(authService, auditService, AdminHealth))
	mux.HandleFunc("GET /api/admin/overview", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Overview))
	mux.HandleFunc("GET /api/admin/crawl-runs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CrawlRuns))
	mux.HandleFunc("GET /api/admin/quality-snapshots", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.QualitySnapshots))
	mux.HandleFunc("GET /api/admin/crawl-tasks", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CrawlTasks))
	mux.HandleFunc("GET /api/admin/categories", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Categories))
	mux.HandleFunc("POST /api/admin/categories", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateCategory))
	mux.HandleFunc("PUT /api/admin/categories/{id}", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateCategory))
	mux.HandleFunc("GET /api/admin/channels", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Channels))
	mux.HandleFunc("POST /api/admin/channels", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateChannel))
	mux.HandleFunc("PUT /api/admin/channels/{id}", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateChannel))
	return mux
}

func resolveAuthService(service *auth.Service) *auth.Service {
	if service != nil {
		return service
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
