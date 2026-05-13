package app

import (
	"database/sql"
	"net/http"
	"time"

	_ "github.com/go-sql-driver/mysql"

	"info-serve/internal/admin"
	"info-serve/internal/config"
)

// App 保存 info-serve 运行期依赖，便于 cmd 入口保持轻量。
type App struct {
	cfg     config.Config
	db      *sql.DB
	handler http.Handler
	closers []func() error
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
	adminActions := admin.NewRedisActionRunner(admin.RedisActionRunnerConfig{
		Addr:         cfg.RedisAddr,
		Password:     cfg.RedisPassword,
		DB:           admin.RedisDBFromString(cfg.RedisDB),
		Stream:       cfg.AggregationCommandStream,
		ResultPrefix: cfg.AggregationResultPrefix,
		WaitTimeout:  admin.RedisWaitTimeoutFromString(cfg.AggregationResultWaitMS),
	})
	llmRunner := admin.NewAggregationLLMRunner(
		cfg.AggregationHTTPBaseURL,
		admin.DurationFromMilliseconds(cfg.AggregationLLMTimeoutMS, 4*60*time.Second),
	)
	return &App{
		cfg:     cfg,
		db:      db,
		handler: NewHTTPHandlerFromDB(db, admin.NewCompositeActionRunner(adminActions, llmRunner)),
		closers: []func() error{
			adminActions.Close,
		},
	}, nil
}

func (a *App) Addr() string {
	return a.cfg.HTTPAddr
}

func (a *App) Handler() http.Handler {
	return a.handler
}

func (a *App) Close() error {
	if a == nil {
		return nil
	}
	var closeErr error
	for _, closer := range a.closers {
		if err := closer(); err != nil && closeErr == nil {
			closeErr = err
		}
	}
	if a.db != nil {
		if err := a.db.Close(); err != nil && closeErr == nil {
			closeErr = err
		}
	}
	return closeErr
}
