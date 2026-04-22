package admin

import (
	"context"
	"errors"
	"strings"
)

var (
	ErrInvalidInput = errors.New("参数不合法")
	ErrNotFound     = errors.New("配置不存在")
	ErrDuplicated   = errors.New("配置已存在")
)

// Store 定义管理后台读取监控数据所需的数据访问能力。
type Store interface {
	GetOverview(ctx context.Context) (Overview, error)
	ListCrawlRuns(ctx context.Context, limit int) ([]CrawlRunSummary, error)
	ListQualitySnapshots(ctx context.Context, limit int) ([]QualitySnapshot, error)
	ListCrawlTasks(ctx context.Context) ([]CrawlTask, error)
	ListCategories(ctx context.Context) ([]Category, error)
	CreateCategory(ctx context.Context, payload CategoryPayload) (Category, error)
	UpdateCategory(ctx context.Context, id int64, payload CategoryPayload) (Category, error)
	ListChannels(ctx context.Context) ([]Channel, error)
	CreateChannel(ctx context.Context, payload ChannelPayload) (Channel, error)
	UpdateChannel(ctx context.Context, id int64, payload ChannelPayload) (Channel, error)
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

type QualitySnapshot struct {
	CategoryCode        string `json:"category_code"`
	TotalCount          int    `json:"total_count"`
	DuplicateTitleCount int    `json:"duplicate_title_count"`
	EmptyContentCount   int    `json:"empty_content_count"`
	LowDetailScoreCount int    `json:"low_detail_score_count"`
	MissingEntityCount  int    `json:"missing_entity_count"`
	SnapshotAt          string `json:"snapshot_at"`
}

type CrawlTask struct {
	TaskCode      string `json:"task_code"`
	TaskName      string `json:"task_name"`
	ChannelCode   string `json:"channel_code"`
	ChannelName   string `json:"channel_name"`
	ScheduleType  string `json:"schedule_type"`
	ScheduleValue string `json:"schedule_value"`
	Status        string `json:"status"`
	LastRunAt     string `json:"last_run_at"`
	NextRunAt     string `json:"next_run_at"`
}

type Category struct {
	ID          int64  `json:"id"`
	Name        string `json:"name"`
	Code        string `json:"code"`
	Description string `json:"description"`
	CreatedAt   string `json:"created_at"`
	UpdatedAt   string `json:"updated_at"`
}

type CategoryPayload struct {
	Name        string `json:"name"`
	Code        string `json:"code"`
	Description string `json:"description"`
}

type Channel struct {
	ID            int64  `json:"id"`
	Name          string `json:"name"`
	Code          string `json:"code"`
	BaseURL       string `json:"base_url"`
	CategoryID    int64  `json:"category_id"`
	CategoryName  string `json:"category_name"`
	CrawlInterval int    `json:"crawl_interval"`
	IsActive      int    `json:"is_active"`
	CreatedAt     string `json:"created_at"`
	UpdatedAt     string `json:"updated_at"`
}

type ChannelPayload struct {
	Name          string `json:"name"`
	Code          string `json:"code"`
	BaseURL       string `json:"base_url"`
	CategoryID    int64  `json:"category_id"`
	CrawlInterval int    `json:"crawl_interval"`
	IsActive      int    `json:"is_active"`
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

func (s *Service) GetOverview(ctx context.Context) (Overview, error) {
	return s.store.GetOverview(ctx)
}

func (s *Service) ListCrawlRuns(ctx context.Context, limit int) ([]CrawlRunSummary, error) {
	if limit < 1 {
		limit = 8
	}
	if limit > 50 {
		limit = 50
	}
	return s.store.ListCrawlRuns(ctx, limit)
}

func (s *Service) ListQualitySnapshots(ctx context.Context, limit int) ([]QualitySnapshot, error) {
	if limit < 1 {
		limit = 8
	}
	if limit > 50 {
		limit = 50
	}
	return s.store.ListQualitySnapshots(ctx, limit)
}

func (s *Service) ListCrawlTasks(ctx context.Context) ([]CrawlTask, error) {
	return s.store.ListCrawlTasks(ctx)
}

func (s *Service) ListCategories(ctx context.Context) ([]Category, error) {
	return s.store.ListCategories(ctx)
}

func (s *Service) CreateCategory(ctx context.Context, payload CategoryPayload) (Category, error) {
	normalized, err := normalizeCategoryPayload(payload)
	if err != nil {
		return Category{}, err
	}
	return s.store.CreateCategory(ctx, normalized)
}

func (s *Service) UpdateCategory(ctx context.Context, id int64, payload CategoryPayload) (Category, error) {
	if id < 1 {
		return Category{}, ErrInvalidInput
	}
	normalized, err := normalizeCategoryPayload(payload)
	if err != nil {
		return Category{}, err
	}
	return s.store.UpdateCategory(ctx, id, normalized)
}

func (s *Service) ListChannels(ctx context.Context) ([]Channel, error) {
	return s.store.ListChannels(ctx)
}

func (s *Service) CreateChannel(ctx context.Context, payload ChannelPayload) (Channel, error) {
	normalized, err := normalizeChannelPayload(payload)
	if err != nil {
		return Channel{}, err
	}
	return s.store.CreateChannel(ctx, normalized)
}

func (s *Service) UpdateChannel(ctx context.Context, id int64, payload ChannelPayload) (Channel, error) {
	if id < 1 {
		return Channel{}, ErrInvalidInput
	}
	normalized, err := normalizeChannelPayload(payload)
	if err != nil {
		return Channel{}, err
	}
	return s.store.UpdateChannel(ctx, id, normalized)
}

func normalizeCategoryPayload(payload CategoryPayload) (CategoryPayload, error) {
	payload.Name = strings.TrimSpace(payload.Name)
	payload.Code = strings.TrimSpace(payload.Code)
	payload.Description = strings.TrimSpace(payload.Description)
	if payload.Name == "" || payload.Code == "" {
		return CategoryPayload{}, ErrInvalidInput
	}
	if len([]rune(payload.Name)) > 50 || len([]rune(payload.Code)) > 50 || len([]rune(payload.Description)) > 200 {
		return CategoryPayload{}, ErrInvalidInput
	}
	return payload, nil
}

func normalizeChannelPayload(payload ChannelPayload) (ChannelPayload, error) {
	payload.Name = strings.TrimSpace(payload.Name)
	payload.Code = strings.TrimSpace(payload.Code)
	payload.BaseURL = strings.TrimSpace(payload.BaseURL)
	if payload.Name == "" || payload.Code == "" || payload.CategoryID < 1 || payload.CrawlInterval < 1 {
		return ChannelPayload{}, ErrInvalidInput
	}
	if payload.IsActive != 0 && payload.IsActive != 1 {
		return ChannelPayload{}, ErrInvalidInput
	}
	if len([]rune(payload.Name)) > 50 || len([]rune(payload.Code)) > 50 || len([]rune(payload.BaseURL)) > 255 {
		return ChannelPayload{}, ErrInvalidInput
	}
	return payload, nil
}
