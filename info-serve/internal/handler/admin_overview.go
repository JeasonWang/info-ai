package handler

import (
	"net/http"

	"info-serve/internal/admin"
	"info-serve/internal/response"
)

// AdminHandler 承载管理后台 API。
type AdminHandler struct {
	service *admin.Service
}

func NewAdminHandler(service *admin.Service) *AdminHandler {
	return &AdminHandler{service: service}
}

func (h *AdminHandler) Overview(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.GetOverview(r.Context())
	if err != nil {
		response.BadRequest(w, "管理总览查询失败")
		return
	}
	response.OK(w, result)
}
