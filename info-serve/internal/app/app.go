package app

import (
	"database/sql"
	"net/http"

	_ "github.com/go-sql-driver/mysql"

	"info-serve/internal/admin"
	"info-serve/internal/config"
)

// App 保存 info-serve 运行期依赖，便于 cmd 入口保持轻量。
type App struct {
	cfg     config.Config
	db      *sql.DB
	handler http.Handler
}

// New 创建生产环境应用实例，负责连接 MySQL 并装配 HTTP handler。
func New(cfg config.Config) (*App, error) {
	db, err := sql.Open("mysql", cfg.MySQLDSN)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return &App{
		cfg:     cfg,
		db:      db,
		handler: NewHTTPHandlerFromDB(db, admin.NewAggregationActionRunner(cfg.AggregationBaseURL)),
	}, nil
}

func (a *App) Addr() string {
	return a.cfg.HTTPAddr
}

func (a *App) Handler() http.Handler {
	return a.handler
}

func (a *App) Close() error {
	if a == nil || a.db == nil {
		return nil
	}
	return a.db.Close()
}
