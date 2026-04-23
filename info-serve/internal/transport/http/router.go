package transporthttp

import (
	"net/http"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/content"
	"info-serve/internal/events"
	transportmiddleware "info-serve/internal/transport/http/middleware"
)

// Services 是 HTTP 层依赖的业务服务集合。
type Services struct {
	Auth    *auth.Service
	Events  *events.Service
	Content *content.Service
	Admin   *admin.Service
	Audit   *audit.Service
}

// NewRouter 创建 info-serve HTTP 路由。
func NewRouter(services Services) http.Handler {
	authService := resolveAuthService(services.Auth)
	eventService := resolveEventService(services.Events)
	contentService := resolveContentService(services.Content)
	adminService := resolveAdminService(services.Admin)
	auditService := resolveAuditService(services.Audit)

	authHandler := NewAuthHandler(authService)
	eventHandler := NewEventHandler(eventService)
	contentHandler := NewContentHandler(contentService)
	adminHandler := NewAdminHandler(adminService)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", Health)
	registerAPIRoutes(mux, "/api", authService, auditService, authHandler, eventHandler, contentHandler, adminHandler)
	registerAPIRoutes(mux, "/api/v1", authService, auditService, authHandler, eventHandler, contentHandler, adminHandler)
	return withCORS(mux)
}

func registerAPIRoutes(
	mux *http.ServeMux,
	prefix string,
	authService *auth.Service,
	auditService *audit.Service,
	authHandler *AuthHandler,
	eventHandler *EventHandler,
	contentHandler *ContentHandler,
	adminHandler *AdminHandler,
) {
	mux.HandleFunc("GET "+prefix+"/categories", contentHandler.Categories)
	mux.HandleFunc("GET "+prefix+"/channels", contentHandler.Channels)
	mux.HandleFunc("GET "+prefix+"/event-categories", eventHandler.Categories)
	mux.HandleFunc("GET "+prefix+"/events", eventHandler.List)
	mux.HandleFunc("GET "+prefix+"/events/", eventHandler.Detail)
	mux.HandleFunc("GET "+prefix+"/infos", contentHandler.Infos)
	mux.HandleFunc("GET "+prefix+"/infos/", contentHandler.InfoDetail)
	mux.HandleFunc("GET "+prefix+"/stats", contentHandler.Stats)
	mux.HandleFunc("POST "+prefix+"/auth/register", authHandler.Register)
	mux.HandleFunc("POST "+prefix+"/auth/login", authHandler.Login)
	mux.HandleFunc("POST "+prefix+"/auth/logout", authHandler.Logout)
	mux.HandleFunc("GET "+prefix+"/me", authHandler.Me)
	mux.HandleFunc("GET "+prefix+"/admin/health", transportmiddleware.RequireAdminWithAudit(authService, auditService, AdminHealth))
	mux.HandleFunc("GET "+prefix+"/admin/overview", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Overview))
	mux.HandleFunc("GET "+prefix+"/admin/crawl-runs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CrawlRuns))
	mux.HandleFunc("GET "+prefix+"/admin/quality-snapshots", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.QualitySnapshots))
	mux.HandleFunc("GET "+prefix+"/admin/low-quality-infos", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.LowQualityInfos))
	mux.HandleFunc("GET "+prefix+"/admin/crawl-tasks", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CrawlTasks))
	mux.HandleFunc("GET "+prefix+"/admin/categories", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Categories))
	mux.HandleFunc("POST "+prefix+"/admin/categories", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateCategory))
	mux.HandleFunc("PUT "+prefix+"/admin/categories/{id}", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateCategory))
	mux.HandleFunc("GET "+prefix+"/admin/channels", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Channels))
	mux.HandleFunc("POST "+prefix+"/admin/channels", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateChannel))
	mux.HandleFunc("PUT "+prefix+"/admin/channels/{id}", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateChannel))
	mux.HandleFunc("GET "+prefix+"/admin/audit-logs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.AuditLogs))
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

func resolveContentService(service *content.Service) *content.Service {
	if service != nil {
		return service
	}
	return content.NewService(content.NewMemoryStore())
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
