package router

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
				ID:                   7,
				RepresentativeInfoID: ptrInt64(11),
				Title:                "国产芯片发布新进展",
				OneLineSummary:       "芯片产业链出现新动态",
				PrimaryCategory:      events.CategoryBrief{Code: "tech", Name: "科技动向"},
				HeatScore:            88,
				FreshnessScore:       76,
				CompositeScore:       92,
				LastUpdatedAt:        "2026-04-22 11:00:00",
				SourceCount:          3,
				SourceBadges:         []string{"CSDN", "掘金"},
				NewUpdateCount:       2,
			},
		},
	}, nil
}

func (s stubEventStore) GetEventDetail(ctx context.Context, id int64) (events.EventDetail, error) {
	return events.EventDetail{
		Event: events.EventCore{
			ID:              id,
			Title:           "国产芯片发布新进展",
			OneLineSummary:  "芯片产业链出现新动态",
			PrimaryCategory: events.CategoryBrief{Code: "tech", Name: "科技动向"},
			HeatScore:       88,
			FreshnessScore:  76,
			CompositeScore:  92,
			SourceCount:     3,
			LastUpdatedAt:   "2026-04-22 11:00:00",
		},
		Timeline: []events.TimelineItem{{ID: 1, OccurredAt: "2026-04-22 10:00:00", Summary: "发布会开始", Confidence: 0.9}},
		Summaries: map[string]string{
			"what_happened": "多家媒体报道国产芯片新进展。",
		},
		SourceViews: []events.SourceView{{ChannelName: "CSDN", Summary: "开发者社区关注芯片生态。"}},
		RepresentativeSources: []events.RepresentativeSource{
			{InfoID: 11, Title: "国产芯片发布新进展", ChannelName: "CSDN", SourceURL: "https://example.com", EventTime: "2026-04-22 10:00:00"},
		},
		TechContext: events.TechContext{Entities: []string{"国产芯片"}, Keywords: []string{"芯片", "半导体"}},
	}, nil
}

func TestEventCategoriesRoute(t *testing.T) {
	r := NewWithDependencies(nil, events.NewService(stubEventStore{}), nil)
	req := httptest.NewRequest(http.MethodGet, "/api/event-categories", nil)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
	var body struct {
		Data []events.EventCategory `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Data[0].Code != "all" {
		t.Fatalf("first category code = %q", body.Data[0].Code)
	}
}

func TestListEventsRouteUsesFrontendCompatibleShape(t *testing.T) {
	r := NewWithDependencies(nil, events.NewService(stubEventStore{}), nil)
	req := httptest.NewRequest(http.MethodGet, "/api/events?category_code=tech&sort=latest&page=2&page_size=5", nil)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
	var body struct {
		Data events.EventPage `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Data.Page != 2 || body.Data.PageSize != 5 {
		t.Fatalf("pagination = %+v", body.Data)
	}
	if body.Data.Items[0].SourceBadges[0] != "CSDN" {
		t.Fatalf("source badges = %+v", body.Data.Items[0].SourceBadges)
	}
}

func TestEventDetailRouteUsesFrontendCompatibleShape(t *testing.T) {
	r := NewWithDependencies(nil, events.NewService(stubEventStore{}), nil)
	req := httptest.NewRequest(http.MethodGet, "/api/events/7", nil)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
	var body struct {
		Data events.EventDetail `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Data.Event.ID != 7 {
		t.Fatalf("event id = %d, want 7", body.Data.Event.ID)
	}
	if len(body.Data.Timeline) != 1 {
		t.Fatalf("timeline len = %d, want 1", len(body.Data.Timeline))
	}
}

func ptrInt64(value int64) *int64 {
	return &value
}
