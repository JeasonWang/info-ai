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
	GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error)
	GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error)
	ListQualitySnapshots(ctx context.Context, limit int) ([]QualitySnapshot, error)
	ListLowQualityInfos(ctx context.Context, limit int) ([]LowQualityInfo, error)
	GetDetailJobReport(ctx context.Context, filter DetailJobFilter) (DetailJobReport, error)
	GetDetailJob(ctx context.Context, id int64) (DetailJobDetail, error)
	RetryDetailJob(ctx context.Context, id int64) (ActionResult, error)
	CancelDetailJob(ctx context.Context, id int64) (ActionResult, error)
	BatchRetryDetailJobs(ctx context.Context, filter DetailJobFilter) (ActionResult, error)
	BatchCancelDetailJobs(ctx context.Context, filter DetailJobFilter) (ActionResult, error)
	ListCrawlTasks(ctx context.Context) ([]CrawlTask, error)
	ListCategories(ctx context.Context) ([]Category, error)
	CreateCategory(ctx context.Context, payload CategoryPayload) (Category, error)
	UpdateCategory(ctx context.Context, id int64, payload CategoryPayload) (Category, error)
	ListChannels(ctx context.Context) ([]Channel, error)
	CreateChannel(ctx context.Context, payload ChannelPayload) (Channel, error)
	UpdateChannel(ctx context.Context, id int64, payload ChannelPayload) (Channel, error)
	ListLLMModelConfigs(ctx context.Context) (any, error)
	CreateLLMModelConfig(ctx context.Context, payload map[string]any) (any, error)
	UpdateLLMModelConfig(ctx context.Context, id int64, payload map[string]any) (any, error)
	GetChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error)
	UpdateChannelCredentials(ctx context.Context, channelCode string, payload ChannelCredentialPayload) (map[string]any, error)
	DeleteChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error)
	ListAuditLogs(ctx context.Context, limit int) ([]AuditLog, error)
	GetEventAnalysisRuns(ctx context.Context, eventID int64) (EventAnalysisRunsResult, error)
	GetEventAnalysisSources(ctx context.Context, eventID int64, runID int64) (EventAnalysisSourcesResult, error)
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
	ChannelCode          string   `json:"channel_code"`
	ChannelName          string   `json:"channel_name"`
	CategoryName         string   `json:"category_name"`
	Status               string   `json:"status"`
	RecentRunCount       int      `json:"recent_run_count"`
	SuccessRate          int      `json:"success_rate"`
	DetailCompleteRate   int      `json:"detail_complete_rate"`
	HealthScore          int      `json:"health_score"`
	HealthLevel          string   `json:"health_level"`
	FailureCount         int      `json:"failure_count"`
	LastRunAt            string   `json:"last_run_at"`
	LastIssue            string   `json:"last_issue"`
	LatestInfoAt         string   `json:"latest_info_at"`
	LatestEventAt        string   `json:"latest_event_at"`
	InfoCount            int      `json:"info_count"`
	ActiveEventCount     int      `json:"active_event_count"`
	AverageContentLength int      `json:"average_content_length"`
	IncompleteInfoCount  int      `json:"incomplete_info_count"`
	TopFailureReasons    []string `json:"top_failure_reasons"`
}

type QualitySnapshot struct {
	CategoryCode            string  `json:"category_code"`
	TotalCount              int     `json:"total_count"`
	DuplicateTitleCount     int     `json:"duplicate_title_count"`
	EmptyContentCount       int     `json:"empty_content_count"`
	LowDetailScoreCount     int     `json:"low_detail_score_count"`
	MissingEntityCount      int     `json:"missing_entity_count"`
	SeedDetailCount         int     `json:"seed_detail_count"`
	RealDetailTotal         int     `json:"real_detail_total"`
	RealCompleteDetailCount int     `json:"real_complete_detail_count"`
	RealCompleteDetailRatio float64 `json:"real_complete_detail_ratio"`
	SnapshotAt              string  `json:"snapshot_at"`
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

type DetailJobFailureReason struct {
	Reason string `json:"reason"`
	Count  int    `json:"count"`
}

type DetailJobSample struct {
	ID                int64  `json:"id"`
	InfoID            int64  `json:"info_id"`
	Title             string `json:"title"`
	ChannelCode       string `json:"channel_code"`
	Status            string `json:"status"`
	Priority          int    `json:"priority"`
	AttemptCount      int    `json:"attempt_count"`
	MaxAttempts       int    `json:"max_attempts"`
	LastFailureReason string `json:"last_failure_reason"`
	NextRunAt         string `json:"next_run_at"`
	DetailScore       int    `json:"detail_score"`
	DetailFetchStatus string `json:"detail_fetch_status"`
}

type DetailJobReport struct {
	Total             int                      `json:"total"`
	StatusCounts      map[string]int           `json:"status_counts"`
	ChannelCounts     map[string]int           `json:"channel_counts"`
	TopFailureReasons []DetailJobFailureReason `json:"top_failure_reasons"`
	PendingSamples    []DetailJobSample        `json:"pending_samples"`
	FailedSamples     []DetailJobSample        `json:"failed_samples"`
}

type DetailJobDetail struct {
	ID                int64  `json:"id"`
	InfoID            int64  `json:"info_id"`
	Title             string `json:"title"`
	SourceURL         string `json:"source_url"`
	Content           string `json:"content"`
	ChannelCode       string `json:"channel_code"`
	Status            string `json:"status"`
	Priority          int    `json:"priority"`
	AttemptCount      int    `json:"attempt_count"`
	MaxAttempts       int    `json:"max_attempts"`
	LastFailureReason string `json:"last_failure_reason"`
	NextRunAt         string `json:"next_run_at"`
	DetailScore       int    `json:"detail_score"`
	DetailFetchStatus string `json:"detail_fetch_status"`
	DetailStrategy    string `json:"detail_strategy"`
	CreatedAt         string `json:"created_at"`
	UpdatedAt         string `json:"updated_at"`
}

type DetailJobFilter struct {
	SampleLimit   int
	ChannelCode   string
	FailureReason string
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
	ID                       int64  `json:"id"`
	Name                     string `json:"name"`
	Code                     string `json:"code"`
	BaseURL                  string `json:"base_url"`
	CategoryID               int64  `json:"category_id"`
	CategoryName             string `json:"category_name"`
	CrawlInterval            int    `json:"crawl_interval"`
	BaseIntervalMinutes      int    `json:"base_interval_minutes"`
	HotIntervalMinutes       int    `json:"hot_interval_minutes"`
	MinIntervalMinutes       int    `json:"min_interval_minutes"`
	MaxIntervalMinutes       int    `json:"max_interval_minutes"`
	ManualIntervalEnabled    int    `json:"manual_interval_enabled"`
	EffectiveIntervalMinutes int    `json:"effective_interval_minutes"`
	ScheduleVersion          int    `json:"schedule_version"`
	IsActive                 int    `json:"is_active"`
	CreatedAt                string `json:"created_at"`
	UpdatedAt                string `json:"updated_at"`
}

type ChannelPayload struct {
	Name                     string `json:"name"`
	Code                     string `json:"code"`
	BaseURL                  string `json:"base_url"`
	CategoryID               int64  `json:"category_id"`
	CrawlInterval            int    `json:"crawl_interval"`
	BaseIntervalMinutes      int    `json:"base_interval_minutes"`
	HotIntervalMinutes       int    `json:"hot_interval_minutes"`
	MinIntervalMinutes       int    `json:"min_interval_minutes"`
	MaxIntervalMinutes       int    `json:"max_interval_minutes"`
	ManualIntervalEnabled    int    `json:"manual_interval_enabled"`
	EffectiveIntervalMinutes int    `json:"effective_interval_minutes"`
	IsActive                 int    `json:"is_active"`
}

type LLMModelConfigPayload struct {
	ProviderName   string `json:"provider_name"`
	ProviderCode   string `json:"provider_code"`
	BaseURL        string `json:"base_url"`
	APIKey         string `json:"api_key"`
	ModelName      string `json:"model_name"`
	IsEnabled      int    `json:"is_enabled"`
	DailyCallLimit int    `json:"daily_call_limit"`
	DailyCallCount int    `json:"daily_call_count"`
	Priority       int    `json:"priority"`
}

type LLMChatTestPayload struct {
	ConfigID       int64  `json:"config_id"`
	Prompt         string `json:"prompt"`
	TimeoutSeconds int    `json:"timeout_seconds"`
}

type LLMChatPayload struct {
	ConfigID       int64  `json:"config_id"`
	Message        string `json:"message"`
	TimeoutSeconds int    `json:"timeout_seconds"`
}

type ChannelCredentialPayload struct {
	Cookies          string         `json:"cookies"`
	ExtraCredentials map[string]any `json:"extra_credentials"`
	UpdatedBy        string         `json:"updated_by"`
}

type ChannelCredentialInfo struct {
	ChannelCode      string         `json:"channel_code"`
	CookieConfigured bool           `json:"cookie_configured"`
	CookiePreview    string         `json:"cookie_preview"`
	CookieStatus     string         `json:"cookie_status"`
	ExtraCredentials map[string]any `json:"extra_credentials"`
	UpdatedAt        string         `json:"updated_at"`
	UpdatedBy        string         `json:"updated_by"`
}

type CredentialTestResult struct {
	ChannelCode  string `json:"channel_code"`
	Success      bool   `json:"success"`
	ResponseCode int    `json:"response_code"`
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

// 事件分析溯源相关类型
type AnalysisRun struct {
	RunID           int64   `json:"run_id"`
	AnalysisVersion string  `json:"analysis_version"`
	Mode            string  `json:"mode"`
	Provider        string  `json:"provider"`
	ModelName       string  `json:"model_name"`
	Status          string  `json:"status"`
	InputItemCount  int     `json:"input_item_count"`
	QualityScore    float64 `json:"quality_score"`
	Confidence      float64 `json:"confidence"`
	FallbackUsed    bool    `json:"fallback_used"`
	FailureReason   string  `json:"failure_reason"`
	StartedAt       string  `json:"started_at"`
	FinishedAt      string  `json:"finished_at"`
	CreatedAt       string  `json:"created_at"`
}

type AnalysisSource struct {
	SourceID     int64  `json:"source_id"`
	InfoID       int64  `json:"info_id"`
	Title        string `json:"title"`
	Role         string `json:"role"`
	Weight       int    `json:"weight"`
	QualityScore int    `json:"quality_score"`
	ChannelName  string `json:"channel_name"`
	SourceURL    string `json:"source_url"`
	EventTime    string `json:"event_time"`
}

type EventAnalysisRunsResult struct {
	EventID    int64         `json:"event_id"`
	EventTitle string        `json:"event_title"`
	Runs       []AnalysisRun `json:"runs"`
}

type EventAnalysisSourcesResult struct {
	EventID    int64            `json:"event_id"`
	EventTitle string           `json:"event_title"`
	Run        AnalysisRun      `json:"run"`
	Sources    []AnalysisSource `json:"sources"`
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

func (s *Service) GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error) {
	if sampleLimit < 1 {
		sampleLimit = 5
	}
	if sampleLimit > 20 {
		sampleLimit = 20
	}
	return s.store.GetChannelQualityReport(ctx, sampleLimit)
}

func (s *Service) GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	return s.store.GetEventAnalysisQualityReport(ctx, limit)
}

func (s *Service) ListLLMModelConfigs(ctx context.Context) (any, error) {
	return s.store.ListLLMModelConfigs(ctx)
}

func (s *Service) CreateLLMModelConfig(ctx context.Context, payload LLMModelConfigPayload) (any, error) {
	normalized, err := normalizeLLMModelConfigPayload(payload)
	if err != nil {
		return nil, err
	}
	return s.store.CreateLLMModelConfig(ctx, normalized)
}

func (s *Service) UpdateLLMModelConfig(ctx context.Context, id int64, payload LLMModelConfigPayload) (any, error) {
	if id <= 0 {
		return nil, ErrInvalidInput
	}
	normalized, err := normalizeLLMModelConfigPayload(payload)
	if err != nil {
		return nil, err
	}
	return s.store.UpdateLLMModelConfig(ctx, id, normalized)
}

func (s *Service) TestLLMChat(ctx context.Context, payload LLMChatTestPayload) (map[string]any, error) {
	normalized := payload
	normalized.Prompt = strings.TrimSpace(normalized.Prompt)
	if normalized.Prompt == "" {
		normalized.Prompt = "请返回JSON：{\"ok\":true,\"summary\":\"大模型连接正常\"}"
	}
	if normalized.TimeoutSeconds <= 0 {
		normalized.TimeoutSeconds = 180
	}
	if normalized.TimeoutSeconds < 10 {
		normalized.TimeoutSeconds = 10
	}
	if normalized.TimeoutSeconds > 600 {
		normalized.TimeoutSeconds = 600
	}
	return s.runner.TestLLMChat(ctx, normalized)
}

func (s *Service) ChatLLM(ctx context.Context, payload LLMChatPayload) (map[string]any, error) {
	normalized := payload
	normalized.Message = strings.TrimSpace(normalized.Message)
	if normalized.Message == "" {
		return nil, ErrInvalidInput
	}
	if normalized.TimeoutSeconds <= 0 {
		normalized.TimeoutSeconds = 240
	}
	if normalized.TimeoutSeconds < 10 {
		normalized.TimeoutSeconds = 10
	}
	if normalized.TimeoutSeconds > 600 {
		normalized.TimeoutSeconds = 600
	}
	return s.runner.ChatLLM(ctx, normalized)
}

func (s *Service) EnqueueEventAnalysisDetailJobs(ctx context.Context, limit int) (ActionResult, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	return s.runner.EnqueueEventAnalysisDetailJobs(ctx, limit)
}

func (s *Service) RebuildStaleEventAnalysis(ctx context.Context, limit int) (ActionResult, error) {
	if limit < 1 {
		limit = 200
	}
	if limit > 1000 {
		limit = 1000
	}
	return s.runner.RebuildStaleEventAnalysis(ctx, limit)
}

func (s *Service) PrioritizeWeakSourceGovernance(ctx context.Context, limit int) (ActionResult, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}

	retryResult, err := s.runner.RetryLowQualityDetails(ctx, limit)
	if err != nil {
		return ActionResult{}, err
	}
	enqueueResult, err := s.runner.EnqueueEventAnalysisDetailJobs(ctx, limit)
	if err != nil {
		return ActionResult{}, err
	}
	rebuildResult, err := s.runner.RebuildStaleEventAnalysis(ctx, limit)
	if err != nil {
		return ActionResult{}, err
	}

	data := map[string]any{
		"limit":                       limit,
		"retry_low_quality_details":    retryResult.Data,
		"enqueue_event_analysis_jobs":  enqueueResult.Data,
		"rebuild_stale_event_analysis": rebuildResult.Data,
	}
	return ActionResult{
		Action:  "prioritize_weak_source_governance",
		Message: "已优先治理弱来源事件，完成详情重抓、分析补偿和过期重建。",
		Data:    data,
	}, nil
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

func (s *Service) GetDetailJobReport(ctx context.Context, filter DetailJobFilter) (DetailJobReport, error) {
	normalized := normalizeDetailJobFilter(filter)
	return s.store.GetDetailJobReport(ctx, normalized)
}

func (s *Service) GetDetailJob(ctx context.Context, id int64) (DetailJobDetail, error) {
	if id < 1 {
		return DetailJobDetail{}, ErrInvalidInput
	}
	return s.store.GetDetailJob(ctx, id)
}

func (s *Service) BatchRetryDetailJobs(ctx context.Context, filter DetailJobFilter) (ActionResult, error) {
	normalized := normalizeDetailJobFilter(filter)
	if normalized.ChannelCode == "" && normalized.FailureReason == "" {
		return ActionResult{}, ErrInvalidInput
	}
	return s.store.BatchRetryDetailJobs(ctx, normalized)
}

func (s *Service) BatchCancelDetailJobs(ctx context.Context, filter DetailJobFilter) (ActionResult, error) {
	normalized := normalizeDetailJobFilter(filter)
	if normalized.ChannelCode == "" && normalized.FailureReason == "" {
		return ActionResult{}, ErrInvalidInput
	}
	return s.store.BatchCancelDetailJobs(ctx, normalized)
}

func (s *Service) RetryDetailJob(ctx context.Context, id int64) (ActionResult, error) {
	if id < 1 {
		return ActionResult{}, ErrInvalidInput
	}
	return s.store.RetryDetailJob(ctx, id)
}

func (s *Service) CancelDetailJob(ctx context.Context, id int64) (ActionResult, error) {
	if id < 1 {
		return ActionResult{}, ErrInvalidInput
	}
	return s.store.CancelDetailJob(ctx, id)
}

func normalizeDetailJobFilter(filter DetailJobFilter) DetailJobFilter {
	filter.ChannelCode = strings.TrimSpace(filter.ChannelCode)
	filter.FailureReason = strings.TrimSpace(filter.FailureReason)
	if filter.SampleLimit < 1 {
		filter.SampleLimit = 10
	}
	if filter.SampleLimit > 50 {
		filter.SampleLimit = 50
	}
	return filter
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

func (s *Service) GetChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	channelCode = strings.TrimSpace(channelCode)
	if channelCode == "" || len([]rune(channelCode)) > 80 {
		return nil, ErrInvalidInput
	}
	return s.store.GetChannelCredentials(ctx, channelCode)
}

func (s *Service) UpdateChannelCredentials(ctx context.Context, channelCode string, payload ChannelCredentialPayload) (map[string]any, error) {
	channelCode = strings.TrimSpace(channelCode)
	if channelCode == "" || len([]rune(channelCode)) > 80 {
		return nil, ErrInvalidInput
	}
	payload.UpdatedBy = strings.TrimSpace(payload.UpdatedBy)
	if payload.UpdatedBy == "" {
		payload.UpdatedBy = "admin"
	}
	result, err := s.store.UpdateChannelCredentials(ctx, channelCode, payload)
	if err != nil {
		return nil, err
	}
	_, _ = s.runner.InvalidateCredentials(ctx, channelCode)
	return result, nil
}

func (s *Service) TestChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	channelCode = strings.TrimSpace(channelCode)
	if channelCode == "" || len([]rune(channelCode)) > 80 {
		return nil, ErrInvalidInput
	}
	return s.runner.TestChannelCredentials(ctx, channelCode)
}

func (s *Service) DeleteChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	channelCode = strings.TrimSpace(channelCode)
	if channelCode == "" || len([]rune(channelCode)) > 80 {
		return nil, ErrInvalidInput
	}
	result, err := s.store.DeleteChannelCredentials(ctx, channelCode)
	if err != nil {
		return nil, err
	}
	_, _ = s.runner.InvalidateCredentials(ctx, channelCode)
	return result, nil
}

func (s *Service) GetEventAnalysisRuns(ctx context.Context, eventID int64) (EventAnalysisRunsResult, error) {
	if eventID < 1 {
		return EventAnalysisRunsResult{}, ErrInvalidInput
	}
	return s.store.GetEventAnalysisRuns(ctx, eventID)
}

func (s *Service) GetEventAnalysisSources(ctx context.Context, eventID int64, runID int64) (EventAnalysisSourcesResult, error) {
	if eventID < 1 || runID < 1 {
		return EventAnalysisSourcesResult{}, ErrInvalidInput
	}
	return s.store.GetEventAnalysisSources(ctx, eventID, runID)
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

func (s *Service) RetryLowQualityDetails(ctx context.Context, limit int) (ActionResult, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 50 {
		limit = 50
	}
	return s.runner.RetryLowQualityDetails(ctx, limit)
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
	if payload.BaseIntervalMinutes == 0 {
		payload.BaseIntervalMinutes = payload.CrawlInterval
	}
	if payload.CrawlInterval == 0 {
		payload.CrawlInterval = payload.BaseIntervalMinutes
	}
	if payload.HotIntervalMinutes == 0 {
		payload.HotIntervalMinutes = 10
	}
	if payload.MinIntervalMinutes == 0 {
		payload.MinIntervalMinutes = 3
	}
	if payload.MaxIntervalMinutes == 0 {
		payload.MaxIntervalMinutes = 240
	}
	if payload.EffectiveIntervalMinutes == 0 {
		payload.EffectiveIntervalMinutes = payload.CrawlInterval
	}
	if payload.Name == "" || payload.Code == "" || payload.CategoryID < 1 || payload.BaseIntervalMinutes < 1 {
		return ChannelPayload{}, ErrInvalidInput
	}
	if payload.BaseIntervalMinutes < 1 || payload.HotIntervalMinutes < 1 || payload.MinIntervalMinutes < 1 || payload.MaxIntervalMinutes < 1 || payload.EffectiveIntervalMinutes < 1 {
		return ChannelPayload{}, ErrInvalidInput
	}
	if payload.MinIntervalMinutes > payload.MaxIntervalMinutes || payload.EffectiveIntervalMinutes < payload.MinIntervalMinutes || payload.EffectiveIntervalMinutes > payload.MaxIntervalMinutes {
		return ChannelPayload{}, ErrInvalidInput
	}
	if payload.IsActive != 0 && payload.IsActive != 1 {
		return ChannelPayload{}, ErrInvalidInput
	}
	if payload.ManualIntervalEnabled != 0 && payload.ManualIntervalEnabled != 1 {
		return ChannelPayload{}, ErrInvalidInput
	}
	if len([]rune(payload.Name)) > 50 || len([]rune(payload.Code)) > 50 || len([]rune(payload.BaseURL)) > 255 {
		return ChannelPayload{}, ErrInvalidInput
	}
	return payload, nil
}

func normalizeLLMModelConfigPayload(payload LLMModelConfigPayload) (map[string]any, error) {
	payload.ProviderName = strings.TrimSpace(payload.ProviderName)
	payload.ProviderCode = strings.TrimSpace(payload.ProviderCode)
	payload.BaseURL = strings.TrimSpace(payload.BaseURL)
	payload.ModelName = strings.TrimSpace(payload.ModelName)
	if payload.ProviderName == "" || payload.ProviderCode == "" || payload.ModelName == "" {
		return nil, ErrInvalidInput
	}
	if payload.IsEnabled != 0 && payload.IsEnabled != 1 {
		return nil, ErrInvalidInput
	}
	if payload.DailyCallLimit < 0 || payload.DailyCallCount < 0 || payload.Priority < 1 {
		return nil, ErrInvalidInput
	}
	if len([]rune(payload.ProviderName)) > 50 || len([]rune(payload.ProviderCode)) > 50 || len([]rune(payload.BaseURL)) > 255 || len([]rune(payload.ModelName)) > 100 || len([]rune(payload.APIKey)) > 500 {
		return nil, ErrInvalidInput
	}
	return map[string]any{
		"provider_name":    payload.ProviderName,
		"provider_code":    payload.ProviderCode,
		"base_url":         payload.BaseURL,
		"api_key":          payload.APIKey,
		"model_name":       payload.ModelName,
		"is_enabled":       payload.IsEnabled,
		"daily_call_limit": payload.DailyCallLimit,
		"daily_call_count": payload.DailyCallCount,
		"priority":         payload.Priority,
	}, nil
}
