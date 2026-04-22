package main

import (
	"database/sql"
	"log"
	"net/http"

	_ "github.com/go-sql-driver/mysql"

	"info-serve/internal/admin"
	"info-serve/internal/auth"
	"info-serve/internal/config"
	"info-serve/internal/events"
	"info-serve/internal/repository"
	"info-serve/internal/router"
)

func main() {
	cfg := config.Load()
	db, err := sql.Open("mysql", cfg.MySQLDSN)
	if err != nil {
		log.Fatalf("MySQL 配置无效：%v", err)
	}
	defer db.Close()
	if err := db.Ping(); err != nil {
		log.Fatalf("MySQL 连接失败：%v", err)
	}

	store := repository.NewMySQLStore(db)
	authService := auth.NewService(store)
	eventService := events.NewService(store)
	adminService := admin.NewService(store)
	log.Printf("info-serve 启动中，监听地址：%s", cfg.HTTPAddr)
	if err := http.ListenAndServe(cfg.HTTPAddr, router.NewWithDependencies(authService, eventService, adminService)); err != nil {
		log.Fatalf("info-serve 启动失败：%v", err)
	}
}
