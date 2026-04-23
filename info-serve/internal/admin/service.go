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
	ListChannelHealth(ctx context.Context) ([]ChannelHealth, error)
	ListQualitySnapshots(ctx context.Context, limit int) ([]QualitySnapshot, error)
	ListLowQualityInfos(ctx context.Context, limit int) ([]LowQualityInfo, error)
	ListCrawlTasks(ctx context.Context) ([]CrawlTask, error)
	ListCategories(ctx context.Context) ([]Category, error)
	CreateCategory(ctx context.Context, payload CategoryPayload) (Category, error)
	UpdateCategory(ctx context.Context, id int64, payload CategoryPayload) (Category, error)
	ListChannels(ctx context.Context) ([]Channel, error)
	CreateChannel(ctx context.Context, payload ChannelPayload) (Channel, error)
	UpdateChannel(ctx context.Context, id int64, payload ChannelPayload) (Channel, error)
	ListAuditLogs(ctx context.Context, limit int) ([]AuditLog, error)
}

type Service struct {
	store  Store
	runner ActionRunner
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

type ChannelHealth struct {
	ChannelCode        string `json:"channel_code"`
	ChannelName        string `json:"channel_name"`
	CategoryName       string `json:"category_name"`
	Status             string `json:"status"`
	RecentRunCount     int    `json:"recent_run_count"`
	SuccessRate        int    `json:"success_rate"`
	DetailCompleteRate int    `json:"detail_complete_rate"`
	HealthScore        int    `json:"health_score"`
	HealthLevel        string `json:"health_level"`
	FailureCount       int    `json:"failure_count"`
	LastRunAt          string `json:"last_run_at"`
	LastIssue          string `json:"last_issue"`
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

type LowQualityInfo struct {
	ID                  int64  `json:"id"`
	Title               string `json:"title"`
	ChannelName         string `json:"channel_name"`
	CategoryName        string `json:"category_name"`
	DetailFetchStatus   string `json:"detail_fetch_status"`
	DetailScore         int    `json:"detail_score"`
	DetailContentLength int    `json:"detail_content_length"`
	IssueReason         string `json:"issue_reason"`
	UpdatedAt           string `json:"updated_at"`
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

type AuditLog struct {
	ID          int64  `json:"id"`
	AdminUserID int64  `json:"admin_user_id"`
	AdminEmail  string `json:"admin_email"`
	Action      string `json:"action"`
	TargetType  string `json:"target_type"`
	TargetID    string `json:"target_id"`
	IPAddress   string `json:"ip_address"`
	CreatedAt   string `json:"created_at"`
}

func NewService(store Store) *Service {
	return NewServiceWithActions(store, NewMemoryActionRunner())
}

func NewServiceWithActions(store Store, runner ActionRunner) *Service {
	if runner == nil {
		runner = NewMemoryActionRunner()
	}
	return &Service{store: store, runner: runner}
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

func (s *Service) ListChannelHealth(ctx context.Context) ([]ChannelHealth, error) {
	return s.store.ListChannelHealth(ctx)
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

func (s *Service) ListLowQualityInfos(ctx context.Context, limit int) ([]LowQualityInfo, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	return s.store.ListLowQualityInfos(ctx, limit)
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

func (s *Service) ListAuditLogs(ctx context.Context, limit int) ([]AuditLog, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	return s.store.ListAuditLogs(ctx, limit)
}

func (s *Service) TriggerCrawl(ctx context.Context, channelCode string) (ActionResult, error) {
	channelCode = strings.TrimSpace(channelCode)
	if channelCode == "" || len([]rune(channelCode)) > 80 {
		return ActionResult{}, ErrInvalidInput
	}
	return s.runner.TriggerCrawl(ctx, channelCode)
}

func (s *Service) RebuildEvents(ctx context.Context) (ActionResult, error) {
	return s.runner.RebuildEvents(ctx)
}

func (s *Service) RefreshQuality(ctx context.Context) (ActionResult, error) {
	return s.runner.RefreshQuality(ctx)
}

func (s *Service) ArchiveLowQuality(ctx context.Context) (ActionResult, error) {
	return s.runner.ArchiveLowQuality(ctx)
}

func (s *Service) ArchiveDuplicateTitles(ctx context.Context) (ActionResult, error) {
	return s.runner.ArchiveDuplicateTitles(ctx)
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
