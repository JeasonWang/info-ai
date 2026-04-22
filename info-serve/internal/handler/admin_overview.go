package handler

import (
	"encoding/json"
	"errors"
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
		response.InternalServerError(w, "管理总览查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) CrawlRuns(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListCrawlRuns(r.Context(), queryLimit(r))
	if err != nil {
		response.InternalServerError(w, "采集运行日志查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) QualitySnapshots(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListQualitySnapshots(r.Context(), queryLimit(r))
	if err != nil {
		response.InternalServerError(w, "质量快照查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) CrawlTasks(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListCrawlTasks(r.Context())
	if err != nil {
		response.InternalServerError(w, "采集任务查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) Categories(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListCategories(r.Context())
	if err != nil {
		response.InternalServerError(w, "分类配置查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) CreateCategory(w http.ResponseWriter, r *http.Request) {
	var payload admin.CategoryPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}
	result, err := h.service.CreateCategory(r.Context(), payload)
	if err != nil {
		writeAdminConfigError(w, err, "分类创建失败")
		return
	}
	response.Created(w, result)
}

func (h *AdminHandler) UpdateCategory(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "分类ID不正确")
		return
	}
	var payload admin.CategoryPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}
	result, err := h.service.UpdateCategory(r.Context(), id, payload)
	if err != nil {
		writeAdminConfigError(w, err, "分类更新失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) Channels(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListChannels(r.Context())
	if err != nil {
		response.InternalServerError(w, "渠道配置查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) CreateChannel(w http.ResponseWriter, r *http.Request) {
	var payload admin.ChannelPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}
	result, err := h.service.CreateChannel(r.Context(), payload)
	if err != nil {
		writeAdminConfigError(w, err, "渠道创建失败")
		return
	}
	response.Created(w, result)
}

func (h *AdminHandler) UpdateChannel(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "渠道ID不正确")
		return
	}
	var payload admin.ChannelPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}
	result, err := h.service.UpdateChannel(r.Context(), id, payload)
	if err != nil {
		writeAdminConfigError(w, err, "渠道更新失败")
		return
	}
	response.OK(w, result)
}

func queryLimit(r *http.Request) int {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	return limit
}

func writeAdminConfigError(w http.ResponseWriter, err error, fallback string) {
	switch {
	case errors.Is(err, admin.ErrInvalidInput):
		response.BadRequest(w, "配置参数不合法")
	case errors.Is(err, admin.ErrDuplicated):
		response.Conflict(w, "配置名称或编码已存在")
	case errors.Is(err, admin.ErrNotFound):
		response.NotFound(w, "配置不存在")
	default:
		response.InternalServerError(w, fallback)
	}
}
