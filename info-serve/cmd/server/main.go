package main

import (
	"log"
	"net/http"

	"info-serve/internal/config"
	"info-serve/internal/router"
)

func main() {
	cfg := config.Load()
	log.Printf("info-serve 启动中，监听地址：%s", cfg.HTTPAddr)
	if err := http.ListenAndServe(cfg.HTTPAddr, router.New()); err != nil {
		log.Fatalf("info-serve 启动失败：%v", err)
	}
}
