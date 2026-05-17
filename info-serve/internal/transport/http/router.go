package transporthttp

import (
	"net/http"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/content"
	"info-serve/internal/events"
	transportmiddleware "info-serve/internal/transport/http/middleware"
	"info-serve/internal/user"
)

// Services 鏄?HTTP 灞備緷璧栫殑涓氬姟鏈嶅姟闆嗗悎銆?
type Services struct {
	Auth    *auth.Service
	Events  *events.Service
	Content *content.Service
	Admin   *admin.Service
	Audit   *audit.Service
	User    *user.Service
}

// NewRouter 鍒涘缓 info-serve HTTP 璺敱銆?
func NewRouter(services Services) http.Handler {
	authService := resolveAuthService(services.Auth)
	eventService := resolveEventService(services.Events)
	contentService := resolveContentService(services.Content)
	adminService := resolveAdminService(services.Admin)
	auditService := resolveAuditService(services.Audit)
	userService := resolveUserService(services.User)

	authHandler := NewAuthHandler(authService)
	eventHandler := NewEventHandler(eventService)
	contentHandler := NewContentHandler(contentService)
	adminHandler := NewAdminHandler(adminService)
	userHandler := NewUserHandler(authService, userService)

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", Health)
	registerAPIRoutes(mux, "/api", authService, auditService, authHandler, eventHandler, contentHandler, adminHandler, userHandler)
	registerAPIRoutes(mux, "/api/v1", authService, auditService, authHandler, eventHandler, contentHandler, adminHandler, userHandler)
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
	userHandler *UserHandler,
) {
	mux.HandleFunc("GET "+prefix+"/categories", contentHandler.Categories)
	mux.HandleFunc("GET "+prefix+"/channels", contentHandler.Channels)
	mux.HandleFunc("GET "+prefix+"/event-categories", eventHandler.Categories)
	mux.HandleFunc("GET "+prefix+"/events", eventHandler.List)
	mux.HandleFunc("GET "+prefix+"/events/", eventHandler.Detail)
	mux.HandleFunc("GET "+prefix+"/infos", contentHandler.Infos)
	mux.HandleFunc("GET "+prefix+"/infos/", contentHandler.InfoDetail)
	mux.HandleFunc("GET "+prefix+"/stats", contentHandler.Stats)
	mux.HandleFunc("GET "+prefix+"/daily-briefs", contentHandler.DailyBriefs)
	mux.HandleFunc("GET "+prefix+"/daily-briefs/{date}", contentHandler.DailyBriefByDate)
	mux.HandleFunc("POST "+prefix+"/auth/register", authHandler.Register)
	mux.HandleFunc("POST "+prefix+"/auth/login", authHandler.Login)
	mux.HandleFunc("POST "+prefix+"/auth/logout", authHandler.Logout)
	mux.HandleFunc("GET "+prefix+"/me", authHandler.Me)
	mux.HandleFunc("GET "+prefix+"/me/favorites", userHandler.FavoriteEventIDs)
	mux.HandleFunc("GET "+prefix+"/me/favorite-events", userHandler.FavoriteEvents)
	mux.HandleFunc("POST "+prefix+"/me/favorites", userHandler.AddFavoriteEvent)
	mux.HandleFunc("DELETE "+prefix+"/me/favorites/{event_id}", userHandler.RemoveFavoriteEvent)
	mux.HandleFunc("GET "+prefix+"/me/preferences/home-filter", userHandler.HomeFilterPreference)
	mux.HandleFunc("PUT "+prefix+"/me/preferences/home-filter", userHandler.SaveHomeFilterPreference)
	mux.HandleFunc("GET "+prefix+"/me/read-history", userHandler.ReadHistory)
	mux.HandleFunc("POST "+prefix+"/me/read-history", userHandler.RecordReadHistory)
	mux.HandleFunc("GET "+prefix+"/admin/health", transportmiddleware.RequireAdminWithAudit(authService, auditService, AdminHealth))
	mux.HandleFunc("GET "+prefix+"/admin/overview", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Overview))
	mux.HandleFunc("GET "+prefix+"/admin/crawl-runs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CrawlRuns))
	mux.HandleFunc("GET "+prefix+"/admin/channel-health", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.ChannelHealth))
	mux.HandleFunc("GET "+prefix+"/admin/channel-quality-report", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.ChannelQualityReport))
	mux.HandleFunc("GET "+prefix+"/admin/event-analysis-quality-report", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.EventAnalysisQualityReport))
	mux.HandleFunc("GET "+prefix+"/admin/quality-snapshots", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.QualitySnapshots))
	mux.HandleFunc("GET "+prefix+"/admin/low-quality-infos", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.LowQualityInfos))
	mux.HandleFunc("GET "+prefix+"/admin/detail-jobs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.DetailJobs))
	mux.HandleFunc("GET "+prefix+"/admin/detail-jobs/{id}", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.DetailJob))
	mux.HandleFunc("GET "+prefix+"/admin/crawl-tasks", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CrawlTasks))
	mux.HandleFunc("PUT "+prefix+"/admin/crawl-tasks/{channel_code}/config", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateCrawlTaskConfig))
	mux.HandleFunc("GET "+prefix+"/admin/categories", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Categories))
	mux.HandleFunc("POST "+prefix+"/admin/categories", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateCategory))
	mux.HandleFunc("PUT "+prefix+"/admin/categories/{id}", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateCategory))
	mux.HandleFunc("GET "+prefix+"/admin/channels", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.Channels))
	mux.HandleFunc("POST "+prefix+"/admin/channels", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateChannel))
	mux.HandleFunc("PUT "+prefix+"/admin/channels/{id}", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateChannel))
	mux.HandleFunc("GET "+prefix+"/admin/llm-model-configs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.LLMModelConfigs))
	mux.HandleFunc("POST "+prefix+"/admin/llm-model-configs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CreateLLMModelConfig))
	mux.HandleFunc("PUT "+prefix+"/admin/llm-model-configs/{id}", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateLLMModelConfig))
	mux.HandleFunc("POST "+prefix+"/admin/llm-model-configs/test-chat", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.TestLLMChat))
	mux.HandleFunc("POST "+prefix+"/admin/llm-model-configs/chat", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.ChatLLM))
	mux.HandleFunc("GET "+prefix+"/admin/audit-logs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.AuditLogs))
	mux.HandleFunc("GET "+prefix+"/admin/channels/{channel_code}/credentials", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.GetChannelCredentials))
	mux.HandleFunc("PUT "+prefix+"/admin/channels/{channel_code}/credentials", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.UpdateChannelCredentials))
	mux.HandleFunc("POST "+prefix+"/admin/channels/{channel_code}/credentials/test", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.TestChannelCredentials))
	mux.HandleFunc("DELETE "+prefix+"/admin/channels/{channel_code}/credentials", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.DeleteChannelCredentials))
	mux.HandleFunc("GET "+prefix+"/admin/events/{event_id}/analysis-runs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.GetEventAnalysisRuns))
	mux.HandleFunc("GET "+prefix+"/admin/events/{event_id}/analysis-sources", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.GetEventAnalysisSources))
	mux.HandleFunc("POST "+prefix+"/admin/crawl-tasks/{channel_code}/trigger", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.TriggerCrawl))
	mux.HandleFunc("POST "+prefix+"/admin/rebuild-events", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.RebuildEvents))
	mux.HandleFunc("POST "+prefix+"/admin/refresh-quality", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.RefreshQuality))
	mux.HandleFunc("POST "+prefix+"/admin/retry-low-quality-details", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.RetryLowQualityDetails))
	mux.HandleFunc("POST "+prefix+"/admin/event-analysis-detail-jobs", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.EnqueueEventAnalysisDetailJobs))
	mux.HandleFunc("POST "+prefix+"/admin/rebuild-stale-event-analysis", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.RebuildStaleEventAnalysis))
	mux.HandleFunc("POST "+prefix+"/admin/prioritize-weak-source-governance", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.PrioritizeWeakSourceGovernance))
	mux.HandleFunc("POST "+prefix+"/admin/detail-jobs/retry", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.BatchRetryDetailJobs))
	mux.HandleFunc("POST "+prefix+"/admin/detail-jobs/cancel", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.BatchCancelDetailJobs))
	mux.HandleFunc("POST "+prefix+"/admin/detail-jobs/{id}/retry", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.RetryDetailJob))
	mux.HandleFunc("POST "+prefix+"/admin/detail-jobs/{id}/cancel", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.CancelDetailJob))
	mux.HandleFunc("POST "+prefix+"/admin/archive-low-quality", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.ArchiveLowQuality))
	mux.HandleFunc("POST "+prefix+"/admin/archive-duplicate-titles", transportmiddleware.RequireAdminWithAudit(authService, auditService, adminHandler.ArchiveDuplicateTitles))
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

func resolveUserService(service *user.Service) *user.Service {
	if service != nil {
		return service
	}
	return user.NewService(user.NewMemoryStore())
}
