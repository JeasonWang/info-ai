package transporthttp

import (
	"net/http"
	"strconv"
	"strings"

	"info-serve/internal/content"
	"info-serve/internal/response"
)

// ContentHandler 承载用户侧非事件内容读取接口。
type ContentHandler struct {
	service *content.Service
}

func NewContentHandler(service *content.Service) *ContentHandler {
	return &ContentHandler{service: service}
}

func (h *ContentHandler) Categories(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.ListCategories(r.Context())
	if err != nil {
		response.InternalServerError(w, "分类查询失败")
		return
	}
	response.OK(w, result)
}

func (h *ContentHandler) Channels(w http.ResponseWriter, r *http.Request) {
	categoryID, _ := strconv.ParseInt(r.URL.Query().Get("category_id"), 10, 64)
	result, err := h.service.ListChannels(r.Context(), categoryID)
	if err != nil {
		response.InternalServerError(w, "渠道查询失败")
		return
	}
	response.OK(w, result)
}

func (h *ContentHandler) Infos(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	categoryID, _ := strconv.ParseInt(query.Get("category_id"), 10, 64)
	channelID, _ := strconv.ParseInt(query.Get("channel_id"), 10, 64)
	page, _ := strconv.Atoi(query.Get("page"))
	pageSize, _ := strconv.Atoi(query.Get("page_size"))
	result, err := h.service.ListInfos(r.Context(), content.ListInfoParams{
		CategoryID: categoryID,
		ChannelID:  channelID,
		Keyword:    query.Get("keyword"),
		Page:       page,
		PageSize:   pageSize,
	})
	if err != nil {
		response.InternalServerError(w, "信息列表查询失败")
		return
	}
	response.OK(w, result)
}

func (h *ContentHandler) InfoDetail(w http.ResponseWriter, r *http.Request) {
	rawID := strings.Trim(r.URL.Path, "/")
	segments := strings.Split(rawID, "/")
	if len(segments) > 0 {
		rawID = segments[len(segments)-1]
	}
	id, err := strconv.ParseInt(rawID, 10, 64)
	if err != nil || id <= 0 {
		response.BadRequest(w, "信息ID不正确")
		return
	}
	result, err := h.service.GetInfoDetail(r.Context(), id)
	if err != nil {
		response.InternalServerError(w, "信息详情查询失败")
		return
	}
	response.OK(w, result)
}

func (h *ContentHandler) Stats(w http.ResponseWriter, r *http.Request) {
	result, err := h.service.GetStats(r.Context())
	if err != nil {
		response.InternalServerError(w, "统计数据查询失败")
		return
	}
	response.OK(w, result)
}

func (h *ContentHandler) DailyBriefs(w http.ResponseWriter, r *http.Request) {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	result, err := h.service.DailyBriefs(r.Context(), limit, offset)
	if err != nil {
		response.InternalServerError(w, "Daily briefs query failed")
		return
	}
	response.OK(w, result)
}

func (h *ContentHandler) DailyBriefByDate(w http.ResponseWriter, r *http.Request) {
	date := r.PathValue("date")
	if date == "" {
		response.BadRequest(w, "Date parameter is required")
		return
	}
	result, err := h.service.DailyBriefByDate(r.Context(), date)
	if err != nil {
		response.NotFound(w, "Daily brief not found")
		return
	}
	response.OK(w, result)
}
