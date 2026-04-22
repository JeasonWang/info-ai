package handler

import (
	"net/http"

	"info-serve/internal/response"
)

// AdminHealth 是管理后台探活接口，用于验证管理鉴权链路。
func AdminHealth(w http.ResponseWriter, r *http.Request) {
	response.OK(w, map[string]string{
		"service": "info-admin-api",
		"status":  "protected",
	})
}
