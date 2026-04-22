package admin

import (
	"context"
	"testing"
)

type fakeAdminStore struct {
	overview Overview
}

func (s fakeAdminStore) GetOverview(ctx context.Context) (Overview, error) {
	return s.overview, nil
}

func TestServiceReturnsOverview(t *testing.T) {
	service := NewService(fakeAdminStore{overview: Overview{
		ChannelCount: 12,
		EventCount:   199,
		InfoCount:    611,
		Quality: QualityOverview{
			DuplicateTitleCount: 2,
			EmptyContentCount:   1,
		},
	}})

	overview, err := service.GetOverview(context.Background())
	if err != nil {
		t.Fatalf("GetOverview returned error: %v", err)
	}
	if overview.ChannelCount != 12 {
		t.Fatalf("channel_count = %d, want 12", overview.ChannelCount)
	}
	if overview.Quality.EmptyContentCount != 1 {
		t.Fatalf("empty_content_count = %d, want 1", overview.Quality.EmptyContentCount)
	}
}
