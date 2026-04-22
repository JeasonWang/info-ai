package admin

import "context"

// Store 定义管理后台读取监控数据所需的数据访问能力。
type Store interface {
	GetOverview(ctx context.Context) (Overview, error)
}

type Service struct {
	store Store
}

type Overview struct {
	ChannelCount int               `json:"channel_count"`
	EventCount   int               `json:"event_count"`
	InfoCount    int               `json:"info_count"`
	Quality      QualityOverview   `json:"quality"`
	RecentRuns   []CrawlRunSummary `json:"recent_runs"`
}

type QualityOverview struct {
	DuplicateTitleCount int `json:"duplicate_title_count"`
	EmptyContentCount   int `json:"empty_content_count"`
	LowDetailScoreCount int `json:"low_detail_score_count"`
	MissingEntityCount  int `json:"missing_entity_count"`
}

type CrawlRunSummary struct {
	ChannelCode        string `json:"channel_code"`
	Status             string `json:"status"`
	RawCount           int    `json:"raw_count"`
	CleanedCount       int    `json:"cleaned_count"`
	SavedCount         int    `json:"saved_count"`
	DetailSuccessCount int    `json:"detail_success_count"`
	DetailFailedCount  int    `json:"detail_failed_count"`
	StartedAt          string `json:"started_at"`
	FinishedAt         string `json:"finished_at"`
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

func (s *Service) GetOverview(ctx context.Context) (Overview, error) {
	return s.store.GetOverview(ctx)
}
