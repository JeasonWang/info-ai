package main

import (
	"log"
	"net/http"

	"info-serve/internal/app"
	"info-serve/internal/config"
)

func main() {
	cfg := config.Load()
	application, err := app.New(cfg)
	if err != nil {
		log.Fatalf("info-serve 初始化失败：%v", err)
	}
	defer application.Close()

	log.Printf("info-serve 启动中，监听地址：%s", application.Addr())
	if err := http.ListenAndServe(application.Addr(), application.Handler()); err != nil {
		log.Fatalf("info-serve 启动失败：%v", err)
	}
}
