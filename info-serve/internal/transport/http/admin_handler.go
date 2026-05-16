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

func (h *AdminHandler) EventAnalysisQualityReport(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.GetEventAnalysisQualityReport(r.Context(), queryLimit(r))
	if err != nil {
		response.InternalServerError(w, "事件分析质量报告查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) EnqueueEventAnalysisDetailJobs(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.EnqueueEventAnalysisDetailJobs(r.Context(), queryLimit(r))
	if err != nil {
		writeAdminActionError(w, err, "事件分析弱来源入队失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) RebuildStaleEventAnalysis(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.RebuildStaleEventAnalysis(r.Context(), queryLimit(r))
	if err != nil {
		writeAdminActionError(w, err, "过期事件分析处理失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) PrioritizeWeakSourceGovernance(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.PrioritizeWeakSourceGovernance(r.Context(), queryLimit(r))
	if err != nil {
		writeAdminActionError(w, err, "弱来源优先治理失败")
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

func (h *AdminHandler) LLMModelConfigs(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListLLMModelConfigs(r.Context())
	if err != nil {
		response.InternalServerError(w, "大模型配置查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) CreateLLMModelConfig(w http.ResponseWriter, r *http.Request) {
	var payload admin.LLMModelConfigPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求参数格式错误")
		return
	}
	result, err := h.service.CreateLLMModelConfig(r.Context(), payload)
	if err != nil {
		writeAdminConfigError(w, err, "大模型配置创建失败")
		return
	}
	response.Created(w, result)
}

func (h *AdminHandler) UpdateLLMModelConfig(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "配置ID不合法")
		return
	}
	var payload admin.LLMModelConfigPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求参数格式错误")
		return
	}
	result, err := h.service.UpdateLLMModelConfig(r.Context(), id, payload)
	if err != nil {
		writeAdminConfigError(w, err, "大模型配置更新失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) TestLLMChat(w http.ResponseWriter, r *http.Request) {
	var payload admin.LLMChatTestPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求参数格式错误")
		return
	}
	result, err := h.service.TestLLMChat(r.Context(), payload)
	if err != nil {
		writeAdminConfigError(w, err, "大模型调用测试失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) ChatLLM(w http.ResponseWriter, r *http.Request) {
	var payload admin.LLMChatPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求参数格式错误")
		return
	}
	result, err := h.service.ChatLLM(r.Context(), payload)
	if err != nil {
		writeAdminConfigError(w, err, "大模型对话失败")
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

func (h *AdminHandler) GetChannelCredentials(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.GetChannelCredentials(r.Context(), r.PathValue("channel_code"))
	if err != nil {
		writeAdminConfigError(w, err, "渠道凭证查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) UpdateChannelCredentials(w http.ResponseWriter, r *http.Request) {
	var payload admin.ChannelCredentialPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求参数格式错误")
		return
	}
	result, err := h.service.UpdateChannelCredentials(r.Context(), r.PathValue("channel_code"), payload)
	if err != nil {
		writeAdminConfigError(w, err, "渠道凭证更新失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) TestChannelCredentials(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.TestChannelCredentials(r.Context(), r.PathValue("channel_code"))
	if err != nil {
		writeAdminConfigError(w, err, "渠道凭证测试失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) DeleteChannelCredentials(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.DeleteChannelCredentials(r.Context(), r.PathValue("channel_code"))
	if err != nil {
		writeAdminConfigError(w, err, "渠道凭证清除失败")
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

func (h *AdminHandler) UpdateCrawlTaskConfig(w http.ResponseWriter, r *http.Request) {
	channelCode := r.PathValue("channel_code")
	var payload admin.CrawlTaskConfigPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.BadRequest(w, "请求体不是有效JSON")
		return
	}
	if err := h.service.UpdateCrawlTaskConfig(r.Context(), channelCode, payload); err != nil {
		if errors.Is(err, admin.ErrInvalidInput) {
			response.BadRequest(w, "参数不合法")
			return
		}
		if errors.Is(err, admin.ErrNotFound) {
			response.NotFound(w, "渠道不存在")
			return
		}
		response.InternalServerError(w, "更新采集配置失败")
		return
	}
	response.OK(w, map[string]string{"message": "配置已更新"})
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

func (h *AdminHandler) GetEventAnalysisRuns(w http.ResponseWriter, r *http.Request) {
	eventID, err := strconv.ParseInt(r.PathValue("event_id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "事件ID不正确")
		return
	}
	result, err := h.service.GetEventAnalysisRuns(r.Context(), eventID)
	if err != nil {
		writeAdminConfigError(w, err, "事件分析运行查询失败")
		return
	}
	response.OK(w, result)
}

func (h *AdminHandler) GetEventAnalysisSources(w http.ResponseWriter, r *http.Request) {
	eventID, err := strconv.ParseInt(r.PathValue("event_id"), 10, 64)
	if err != nil {
		response.BadRequest(w, "事件ID不正确")
		return
	}
	runID, err := strconv.ParseInt(r.URL.Query().Get("run_id"), 10, 64)
	if err != nil || runID < 1 {
		response.BadRequest(w, "run_id 参数不正确")
		return
	}
	result, err := h.service.GetEventAnalysisSources(r.Context(), eventID, runID)
	if err != nil {
		writeAdminConfigError(w, err, "事件分析来源查询失败")
		return
	}
	response.OK(w, result)
}
