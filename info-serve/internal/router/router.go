package router

import (
	"net/http"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/events"
	transporthttp "info-serve/internal/transport/http"
)

// New 创建 info-serve 路由。
func New(services ...*auth.Service) http.Handler {
	authService := resolveAuthService(services...)
	return NewWithDependencies(authService, nil, nil, nil)
}

// NewWithDependencies 创建带依赖注入的路由，便于服务启动和测试复用。
func NewWithDependencies(authService *auth.Service, eventService *events.Service, adminService *admin.Service, auditService *audit.Service) http.Handler {
	return transporthttp.NewRouter(transporthttp.Services{
		Auth:   authService,
		Events: eventService,
		Admin:  adminService,
		Audit:  auditService,
	})
}

func resolveAuthService(services ...*auth.Service) *auth.Service {
	if len(services) > 0 && services[0] != nil {
		return services[0]
	}
	return auth.NewService(auth.NewMemoryStore())
}
