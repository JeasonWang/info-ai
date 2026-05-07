package transporthttp

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"info-serve/internal/events"
)

type stubEventStore struct{}

func (s stubEventStore) ListEvents(ctx context.Context, params events.ListEventsParams) (events.EventPage, error) {
	return events.EventPage{
		Total:    1,
		Page:     params.Page,
		PageSize: params.PageSize,
		Items: []events.EventListItem{
			{
				ID:              7,
				Title:           "国产芯片发布新进展",
				OneLineSummary:  "芯片产业链出现新动态",
				PrimaryCategory: events.CategoryBrief{Code: "tech", Name: "科技"},
				SourceBadges:    []string{"CSDN"},
			},
		},
	}, nil
}

func (s stubEventStore) GetEventDetail(ctx context.Context, id int64) (events.EventDetail, error) {
	return events.EventDetail{
		Event: events.EventCore{
			ID:              id,
			Title:           "国产芯片发布新进展",
			PrimaryCategory: events.CategoryBrief{Code: "tech", Name: "科技"},
		},
		Timeline: []events.TimelineItem{{ID: 1, Summary: "发布会开始"}},
		Summaries: map[string]string{
			"what_happened": "芯片产业链出现新动态。",
		},
		SourceViews:           []events.SourceView{},
		RepresentativeSources: []events.RepresentativeSource{},
		TechContext:           events.TechContext{},
	}, nil
}

func TestEventHandlerReturnsCategoriesListAndDetail(t *testing.T) {
	handler := NewEventHandler(events.NewService(stubEventStore{}))

	categoriesReq := httptest.NewRequest(http.MethodGet, "/api/event-categories", nil)
	categoriesRes := httptest.NewRecorder()
	handler.Categories(categoriesRes, categoriesReq)
	if categoriesRes.Code != http.StatusOK {
		t.Fatalf("categories status = %d, want %d", categoriesRes.Code, http.StatusOK)
	}

	listReq := httptest.NewRequest(http.MethodGet, "/api/events?category_code=tech&page=2&page_size=5", nil)
	listRes := httptest.NewRecorder()
	handler.List(listRes, listReq)
	if listRes.Code != http.StatusOK {
		t.Fatalf("list status = %d, want %d", listRes.Code, http.StatusOK)
	}
	var listBody struct {
		Data events.EventPage `json:"data"`
	}
	if err := json.Unmarshal(listRes.Body.Bytes(), &listBody); err != nil {
		t.Fatalf("invalid list json: %v", err)
	}
	if listBody.Data.Page != 2 || listBody.Data.Items[0].ID != 7 {
		t.Fatalf("list body = %+v", listBody.Data)
	}

	detailReq := httptest.NewRequest(http.MethodGet, "/api/events/7", nil)
	detailRes := httptest.NewRecorder()
	handler.Detail(detailRes, detailReq)
	if detailRes.Code != http.StatusOK {
		t.Fatalf("detail status = %d, want %d", detailRes.Code, http.StatusOK)
	}
}
