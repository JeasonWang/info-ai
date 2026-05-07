package transporthttp

import (
	"log"
	"net/http"
	"strconv"
	"strings"

	"info-serve/internal/events"
	"info-serve/internal/response"
)

// EventHandler 承载用户侧事件读取接口。
type EventHandler struct {
	service *events.Service
}

func NewEventHandler(service *events.Service) *EventHandler {
	return &EventHandler{service: service}
}

func (h *EventHandler) Categories(w http.ResponseWriter, r *http.Request) {
	response.OK(w, events.EventCategories())
}

func (h *EventHandler) List(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	page, _ := strconv.Atoi(query.Get("page"))
	pageSize, _ := strconv.Atoi(query.Get("page_size"))
	result, err := h.service.ListEvents(r.Context(), events.ListEventsParams{
		CategoryCode: query.Get("category_code"),
		ChannelCode:  query.Get("channel_code"),
		Keyword:      query.Get("keyword"),
		Sort:         query.Get("sort"),
		Page:         page,
		PageSize:     pageSize,
	})
	if err != nil {
		log.Printf("[ERROR] ListEvents failed: %v", err)
		response.InternalServerError(w, "事件列表查询失败")
		return
	}
	response.OK(w, result)
}

func (h *EventHandler) Detail(w http.ResponseWriter, r *http.Request) {
	rawID := strings.Trim(r.URL.Path, "/")
	segments := strings.Split(rawID, "/")
	if len(segments) > 0 {
		rawID = segments[len(segments)-1]
	}
	id, err := strconv.ParseInt(rawID, 10, 64)
	if err != nil || id <= 0 {
		response.BadRequest(w, "事件ID不正确")
		return
	}
	result, err := h.service.GetEventDetail(r.Context(), id)
	if err != nil {
		response.InternalServerError(w, "事件详情查询失败")
		return
	}
	response.OK(w, result)
}
