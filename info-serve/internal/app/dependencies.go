package app

import (
	"database/sql"
	"net/http"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/events"
	"info-serve/internal/repository"
	transporthttp "info-serve/internal/transport/http"
)

// Stores 收拢服务装配所需的存储依赖，避免 cmd 入口直接感知各业务服务的构造细节。
type Stores struct {
	Auth   auth.Store
	Events events.Store
	Admin  admin.Store
	Audit  audit.Store
}

// NewHTTPHandler 根据存储依赖装配完整 HTTP 路由，供生产入口和测试复用。
func NewHTTPHandler(stores Stores) http.Handler {
	authStore := stores.Auth
	if authStore == nil {
		authStore = auth.NewMemoryStore()
	}
	eventStore := stores.Events
	if eventStore == nil {
		eventStore = events.NewMemoryStore()
	}
	adminStore := stores.Admin
	if adminStore == nil {
		adminStore = admin.NewMemoryStore()
	}
	auditStore := stores.Audit
	if auditStore == nil {
		auditStore = audit.NewMemoryStore()
	}

	return transporthttp.NewRouter(transporthttp.Services{
		Auth:   auth.NewService(authStore),
		Events: events.NewService(eventStore),
		Admin:  admin.NewService(adminStore),
		Audit:  audit.NewService(auditStore),
	})
}

// NewHTTPHandlerFromDB 使用同一个 MySQL store 装配所有业务模块。
func NewHTTPHandlerFromDB(db *sql.DB) http.Handler {
	store := repository.NewMySQLStore(db)
	return NewHTTPHandler(Stores{
		Auth:   store,
		Events: store,
		Admin:  store,
		Audit:  store,
	})
}
