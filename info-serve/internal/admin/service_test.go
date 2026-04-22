package admin

import (
	"context"
	"testing"
)

type fakeAdminStore struct {
	overview         Overview
	crawlRuns        []CrawlRunSummary
	qualitySnapshots []QualitySnapshot
	crawlTasks       []CrawlTask
}

func (s fakeAdminStore) GetOverview(ctx context.Context) (Overview, error) {
	return s.overview, nil
}

func (s fakeAdminStore) ListCrawlRuns(ctx context.Context, limit int) ([]CrawlRunSummary, error) {
	return s.crawlRuns[:min(limit, len(s.crawlRuns))], nil
}

func (s fakeAdminStore) ListQualitySnapshots(ctx context.Context, limit int) ([]QualitySnapshot, error) {
	return s.qualitySnapshots[:min(limit, len(s.qualitySnapshots))], nil
}

func (s fakeAdminStore) ListCrawlTasks(ctx context.Context) ([]CrawlTask, error) {
	return s.crawlTasks, nil
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

func TestServiceReturnsMonitoringLists(t *testing.T) {
	service := NewService(fakeAdminStore{
		crawlRuns: []CrawlRunSummary{
			{ChannelCode: "weibo", Status: "success"},
			{ChannelCode: "csdn", Status: "failed"},
		},
		qualitySnapshots: []QualitySnapshot{
			{CategoryCode: "all", TotalCount: 611},
		},
		crawlTasks: []CrawlTask{
			{TaskCode: "weibo-hot", TaskName: "微博热点", Status: "active"},
		},
	})

	runs, err := service.ListCrawlRuns(context.Background(), 1)
	if err != nil {
		t.Fatalf("ListCrawlRuns returned error: %v", err)
	}
	if len(runs) != 1 || runs[0].ChannelCode != "weibo" {
		t.Fatalf("runs = %+v", runs)
	}

	snapshots, err := service.ListQualitySnapshots(context.Background(), 5)
	if err != nil {
		t.Fatalf("ListQualitySnapshots returned error: %v", err)
	}
	if snapshots[0].TotalCount != 611 {
		t.Fatalf("snapshots = %+v", snapshots)
	}

	tasks, err := service.ListCrawlTasks(context.Background())
	if err != nil {
		t.Fatalf("ListCrawlTasks returned error: %v", err)
	}
	if tasks[0].TaskCode != "weibo-hot" {
		t.Fatalf("tasks = %+v", tasks)
	}
}

func min(left int, right int) int {
	if left < right {
		return left
	}
	return right
}
