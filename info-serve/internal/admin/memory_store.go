package admin

import "context"

// MemoryStore 是本地开发和路由测试使用的管理端空存储。
type MemoryStore struct{}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{}
}

func (s *MemoryStore) GetOverview(ctx context.Context) (Overview, error) {
	return Overview{
		Quality:    QualityOverview{},
		RecentRuns: []CrawlRunSummary{},
	}, nil
}

func (s *MemoryStore) ListCrawlRuns(ctx context.Context, limit int) ([]CrawlRunSummary, error) {
	return []CrawlRunSummary{}, nil
}

func (s *MemoryStore) ListChannelHealth(ctx context.Context) ([]ChannelHealth, error) {
	return []ChannelHealth{}, nil
}

func (s *MemoryStore) ListQualitySnapshots(ctx context.Context, limit int) ([]QualitySnapshot, error) {
	return []QualitySnapshot{}, nil
}

func (s *MemoryStore) ListLowQualityInfos(ctx context.Context, limit int) ([]LowQualityInfo, error) {
	return []LowQualityInfo{}, nil
}

func (s *MemoryStore) GetDetailJobReport(ctx context.Context, filter DetailJobFilter) (DetailJobReport, error) {
	return DetailJobReport{
		StatusCounts:  map[string]int{},
		ChannelCounts: map[string]int{},
	}, nil
}

func (s *MemoryStore) GetDetailJob(ctx context.Context, id int64) (DetailJobDetail, error) {
	return DetailJobDetail{ID: id, Title: "本地测试详情补偿任务", Status: "pending"}, nil
}

func (s *MemoryStore) RetryDetailJob(ctx context.Context, id int64) (ActionResult, error) {
	return ActionResult{Action: "retry_detail_job", Message: "本地测试模式已模拟重新入队详情补偿任务", Data: map[string]any{"detail_job_id": id}}, nil
}

func (s *MemoryStore) CancelDetailJob(ctx context.Context, id int64) (ActionResult, error) {
	return ActionResult{Action: "cancel_detail_job", Message: "本地测试模式已模拟取消详情补偿任务", Data: map[string]any{"detail_job_id": id}}, nil
}

func (s *MemoryStore) BatchRetryDetailJobs(ctx context.Context, filter DetailJobFilter) (ActionResult, error) {
	return ActionResult{Action: "batch_retry_detail_jobs", Message: "本地测试模式已模拟批量重新入队详情补偿任务", Data: map[string]any{"matched_count": 0}}, nil
}

func (s *MemoryStore) BatchCancelDetailJobs(ctx context.Context, filter DetailJobFilter) (ActionResult, error) {
	return ActionResult{Action: "batch_cancel_detail_jobs", Message: "本地测试模式已模拟批量取消详情补偿任务", Data: map[string]any{"matched_count": 0}}, nil
}

func (s *MemoryStore) ListCrawlTasks(ctx context.Context) ([]CrawlTask, error) {
	return []CrawlTask{}, nil
}

func (s *MemoryStore) ListCategories(ctx context.Context) ([]Category, error) {
	return []Category{}, nil
}

func (s *MemoryStore) CreateCategory(ctx context.Context, payload CategoryPayload) (Category, error) {
	return Category{ID: 1, Name: payload.Name, Code: payload.Code, Description: payload.Description}, nil
}

func (s *MemoryStore) UpdateCategory(ctx context.Context, id int64, payload CategoryPayload) (Category, error) {
	return Category{ID: id, Name: payload.Name, Code: payload.Code, Description: payload.Description}, nil
}

func (s *MemoryStore) ListChannels(ctx context.Context) ([]Channel, error) {
	return []Channel{}, nil
}

func (s *MemoryStore) CreateChannel(ctx context.Context, payload ChannelPayload) (Channel, error) {
	return Channel{ID: 1, Name: payload.Name, Code: payload.Code, BaseURL: payload.BaseURL, CategoryID: payload.CategoryID, CrawlInterval: payload.CrawlInterval, IsActive: payload.IsActive}, nil
}

func (s *MemoryStore) UpdateChannel(ctx context.Context, id int64, payload ChannelPayload) (Channel, error) {
	return Channel{ID: id, Name: payload.Name, Code: payload.Code, BaseURL: payload.BaseURL, CategoryID: payload.CategoryID, CrawlInterval: payload.CrawlInterval, IsActive: payload.IsActive}, nil
}

func (s *MemoryStore) ListAuditLogs(ctx context.Context, limit int) ([]AuditLog, error) {
	return []AuditLog{}, nil
}

func (s *MemoryStore) GetEventAnalysisRuns(ctx context.Context, eventID int64) (EventAnalysisRunsResult, error) {
	return EventAnalysisRunsResult{
		EventID:    eventID,
		EventTitle: "本地测试事件",
		Runs:       []AnalysisRun{},
	}, nil
}

func (s *MemoryStore) GetEventAnalysisSources(ctx context.Context, eventID int64, runID int64) (EventAnalysisSourcesResult, error) {
	return EventAnalysisSourcesResult{
		EventID:    eventID,
		EventTitle: "本地测试事件",
		Run:        AnalysisRun{RunID: runID, Mode: "rule", Status: "succeeded"},
		Sources:    []AnalysisSource{},
	}, nil
}
