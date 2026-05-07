package transporthttp

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"

	"info-serve/internal/admin"
	"info-serve/internal/response"
)

// AdminHealth 是管理后台探活接口，用于验证管理鉴权链路。
func AdminHealth(w http.ResponseWriter, r *http.Request) {
	response.OK(w, map[string]string{
		"service": "info-admin-api",
		"status":  "protected",
	})
}

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

func (h *AdminHandler) ChannelHealth(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListChannelHealth(r.Context())
	if err != nil {
		response.InternalServerError(w, "渠道健康查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) ChannelQualityReport(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.GetChannelQualityReport(r.Context(), querySampleLimit(r))
	if err != nil {
		response.InternalServerError(w, "渠道质量报告查询失败")
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

func (h *AdminHandler) LowQualityInfos(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListLowQualityInfos(r.Context(), queryLimit(r))
	if err != nil {
		response.InternalServerError(w, "低质量信息查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) DetailJobs(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.GetDetailJobReport(r.Context(), detailJobFilterFromRequest(r))
	if err != nil {
		response.InternalServerError(w, "详情补偿队列查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) DetailJob(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "详情补偿任务ID不正确")
		return
	}
	result, err := h.service.GetDetailJob(r.Context(), id)
	if err != nil {
		writeAdminActionError(w, err, "详情补偿任务查询失败")
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

func (h *AdminHandler) AuditLogs(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListAuditLogs(r.Context(), queryLimit(r))
	if err != nil {
		response.InternalServerError(w, "审计日志查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) TriggerCrawl(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.TriggerCrawl(r.Context(), r.PathValue("channel_code"))
	if err != nil {
		writeAdminActionError(w, err, "采集任务触发失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) RebuildEvents(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.RebuildEvents(r.Context())
	if err != nil {
		writeAdminActionError(w, err, "事件重建失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) RefreshQuality(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.RefreshQuality(r.Context())
	if err != nil {
		writeAdminActionError(w, err, "数据质量刷新失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) RetryLowQualityDetails(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.RetryLowQualityDetails(r.Context(), queryLimit(r))
	if err != nil {
		writeAdminActionError(w, err, "低完整详情重抓失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) RetryDetailJob(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "详情补偿任务ID不正确")
		return
	}
	result, err := h.service.RetryDetailJob(r.Context(), id)
	if err != nil {
		writeAdminActionError(w, err, "详情补偿任务重试失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) BatchRetryDetailJobs(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.BatchRetryDetailJobs(r.Context(), detailJobFilterFromRequest(r))
	if err != nil {
		writeAdminActionError(w, err, "详情补偿任务批量重试失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) BatchCancelDetailJobs(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.BatchCancelDetailJobs(r.Context(), detailJobFilterFromRequest(r))
	if err != nil {
		writeAdminActionError(w, err, "详情补偿任务批量取消失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) CancelDetailJob(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "详情补偿任务ID不正确")
		return
	}
	result, err := h.service.CancelDetailJob(r.Context(), id)
	if err != nil {
		writeAdminActionError(w, err, "详情补偿任务取消失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) ArchiveLowQuality(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ArchiveLowQuality(r.Context())
	if err != nil {
		writeAdminActionError(w, err, "低质量内容归档失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) ArchiveDuplicateTitles(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ArchiveDuplicateTitles(r.Context())
	if err != nil {
		writeAdminActionError(w, err, "重复标题归档失败")
		return
	}
	response.OK(w, result)
}

func queryLimit(r *http.Request) int {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	return limit
}

func querySampleLimit(r *http.Request) int {
	limit, _ := strconv.Atoi(r.URL.Query().Get("sample_limit"))
	return limit
}

func detailJobFilterFromRequest(r *http.Request) admin.DetailJobFilter {
	query := r.URL.Query()
	return admin.DetailJobFilter{
		SampleLimit:   queryLimit(r),
		ChannelCode:   query.Get("channel_code"),
		FailureReason: query.Get("failure_reason"),
	}
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

func writeAdminActionError(w http.ResponseWriter, err error, fallback string) {
	switch {
	case errors.Is(err, admin.ErrInvalidInput):
		response.BadRequest(w, "管理动作参数不合法")
	case errors.Is(err, admin.ErrNotFound):
		response.NotFound(w, "管理动作目标不存在")
	default:
		response.InternalServerError(w, fallback)
	}
}
