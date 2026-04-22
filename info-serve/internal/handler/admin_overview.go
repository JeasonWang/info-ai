package handler

import (
	"net/http"
	"strconv"

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

func (h *AdminHandler) CrawlRuns(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListCrawlRuns(r.Context(), queryLimit(r))
	if err != nil {
		response.BadRequest(w, "采集运行日志查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) QualitySnapshots(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListQualitySnapshots(r.Context(), queryLimit(r))
	if err != nil {
		response.BadRequest(w, "质量快照查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) CrawlTasks(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListCrawlTasks(r.Context())
	if err != nil {
		response.BadRequest(w, "采集任务查询失败")
		return
	}
	response.OK(w, result)
}

func queryLimit(r *http.Request) int {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	return limit
}
