package events

import (
	"context"
	"testing"
)

type fakeEventStore struct {
	listResult   EventPage
	detailResult EventDetail
	listParams   *ListEventsParams
}

func (s fakeEventStore) ListEvents(ctx context.Context, params ListEventsParams) (EventPage, error) {
	if s.listParams != nil {
		*s.listParams = params
	}
	result := s.listResult
	result.Page = params.Page
	result.PageSize = params.PageSize
	return result, nil
}

func (s fakeEventStore) GetEventDetail(ctx context.Context, id int64) (EventDetail, error) {
	return s.detailResult, nil
}

func TestServiceNormalizesListParams(t *testing.T) {
	var captured ListEventsParams
	service := NewService(fakeEventStore{listResult: EventPage{Total: 1}, listParams: &captured})

	page, err := service.ListEvents(context.Background(), ListEventsParams{
		CategoryCode: "",
		Sort:         "",
		Page:         0,
		PageSize:     0,
	})
	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	if page.Page != 1 {
		t.Fatalf("page = %d, want 1", page.Page)
	}
	if page.PageSize != 10 {
		t.Fatalf("page_size = %d, want 10", page.PageSize)
	}
	if captured.Status != "active" {
		t.Fatalf("status = %q, want active", captured.Status)
	}
}

func TestServiceAllowsMonitoringListStatus(t *testing.T) {
	var captured ListEventsParams
	service := NewService(fakeEventStore{listResult: EventPage{Total: 1}, listParams: &captured})

	_, err := service.ListEvents(context.Background(), ListEventsParams{Status: "monitoring", Page: 1, PageSize: 10})
	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	if captured.Status != "monitoring" {
		t.Fatalf("status = %q, want monitoring", captured.Status)
	}
}

func TestServiceNormalizesNilSourceBadges(t *testing.T) {
	service := NewService(fakeEventStore{listResult: EventPage{
		Total:    1,
		Page:     1,
		PageSize: 10,
		Items: []EventListItem{
			{
				ID:           7,
				Title:        "热点事件",
				SourceBadges: nil,
			},
		},
	}})

	page, err := service.ListEvents(context.Background(), ListEventsParams{Page: 1, PageSize: 10})

	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	if page.Items[0].SourceBadges == nil {
		t.Fatal("source badges should be an empty array instead of nil")
	}
	if len(page.Items[0].SourceBadges) != 0 {
		t.Fatalf("source badges = %+v, want empty", page.Items[0].SourceBadges)
	}
}

func TestEventCategoriesAreStableForFrontendTabs(t *testing.T) {
	categories := EventCategories()

	if len(categories) != 5 {
		t.Fatalf("len(categories) = %d, want 5", len(categories))
	}
	if categories[0].Code != "all" || categories[0].Name != "全网" {
		t.Fatalf("first category = %+v", categories[0])
	}
	if categories[1].Code != "tech" {
		t.Fatalf("second category = %+v, want tech", categories[1])
	}
}
