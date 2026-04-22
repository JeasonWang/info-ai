package events

import (
	"context"
	"testing"
)

type fakeEventStore struct {
	listResult   EventPage
	detailResult EventDetail
}

func (s fakeEventStore) ListEvents(ctx context.Context, params ListEventsParams) (EventPage, error) {
	result := s.listResult
	result.Page = params.Page
	result.PageSize = params.PageSize
	return result, nil
}

func (s fakeEventStore) GetEventDetail(ctx context.Context, id int64) (EventDetail, error) {
	return s.detailResult, nil
}

func TestServiceNormalizesListParams(t *testing.T) {
	service := NewService(fakeEventStore{listResult: EventPage{Total: 1}})

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
