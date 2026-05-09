package admin

import (
	"context"
	"testing"
)

type fakeAdminStore struct {
	overview         Overview
	crawlRuns        []CrawlRunSummary
	channelHealth    []ChannelHealth
	qualitySnapshots []QualitySnapshot
	lowQualityInfos  []LowQualityInfo
	detailJobReport  DetailJobReport
	crawlTasks       []CrawlTask
	categories       []Category
	channels         []Channel
	auditLogs        []AuditLog
}

type fakeActionRunner struct {
	action      string
	channelCode string
	limit       int
}

func (r *fakeActionRunner) TriggerCrawl(ctx context.Context, channelCode string) (ActionResult, error) {
	r.action = "trigger_crawl"
	r.channelCode = channelCode
	return ActionResult{Action: r.action, Message: "已触发采集", Data: map[string]any{"channel_code": channelCode}}, nil
}

func (r *fakeActionRunner) GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error) {
	r.action = "channel_quality_report"
	r.limit = sampleLimit
	return map[string]any{
		"summary": map[string]any{"usable_ratio": 88.0},
		"channels": []any{
			map[string]any{"channel_code": "weibo", "usable_ratio": 88.0},
		},
	}, nil
}

func (r *fakeActionRunner) GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error) {
	r.action = "event_analysis_quality_report"
	r.limit = limit
	return map[string]any{
		"summary": map[string]any{"low_confidence_count": 1},
		"risk_events": []any{
			map[string]any{"event_id": 1, "issue_reasons": []any{"low_confidence"}},
		},
	}, nil
}

func (r *fakeActionRunner) ListLLMModelConfigs(ctx context.Context) (any, error) {
	r.action = "list_llm_model_configs"
	return []any{map[string]any{"provider_code": "qwen"}}, nil
}

func (r *fakeActionRunner) CreateLLMModelConfig(ctx context.Context, payload map[string]any) (any, error) {
	r.action = "create_llm_model_config"
	return payload, nil
}

func (r *fakeActionRunner) UpdateLLMModelConfig(ctx context.Context, id int64, payload map[string]any) (any, error) {
	r.action = "update_llm_model_config"
	payload["id"] = id
	return payload, nil
}

func (r *fakeActionRunner) EnqueueEventAnalysisDetailJobs(ctx context.Context, limit int) (ActionResult, error) {
	r.action = "event_analysis_detail_jobs"
	r.limit = limit
	return ActionResult{Action: r.action, Message: "已入队事件分析弱来源", Data: map[string]any{"limit": limit}}, nil
}

func (r *fakeActionRunner) RebuildStaleEventAnalysis(ctx context.Context, limit int) (ActionResult, error) {
	r.action = "rebuild_stale_event_analysis"
	r.limit = limit
	return ActionResult{Action: r.action, Message: "已处理过期事件分析", Data: map[string]any{"limit": limit}}, nil
}

func (r *fakeActionRunner) RebuildEvents(ctx context.Context) (ActionResult, error) {
	r.action = "rebuild_events"
	return ActionResult{Action: r.action, Message: "已重建事件"}, nil
}

func (r *fakeActionRunner) RefreshQuality(ctx context.Context) (ActionResult, error) {
	r.action = "refresh_quality"
	return ActionResult{Action: r.action, Message: "已刷新质量"}, nil
}

func (r *fakeActionRunner) RetryLowQualityDetails(ctx context.Context, limit int) (ActionResult, error) {
	r.action = "retry_low_quality_details"
	r.limit = limit
	return ActionResult{Action: r.action, Message: "已重抓低完整详情", Data: map[string]any{"limit": limit}}, nil
}

func (r *fakeActionRunner) ArchiveLowQuality(ctx context.Context) (ActionResult, error) {
	r.action = "archive_low_quality"
	return ActionResult{Action: r.action, Message: "已归档低质量内容"}, nil
}

func (r *fakeActionRunner) ArchiveDuplicateTitles(ctx context.Context) (ActionResult, error) {
	r.action = "archive_duplicate_titles"
	return ActionResult{Action: r.action, Message: "已归档重复标题"}, nil
}

func (s fakeAdminStore) GetOverview(ctx context.Context) (Overview, error) {
	return s.overview, nil
}

func (s fakeAdminStore) ListCrawlRuns(ctx context.Context, limit int) ([]CrawlRunSummary, error) {
	return s.crawlRuns[:min(limit, len(s.crawlRuns))], nil
}

func (s fakeAdminStore) ListChannelHealth(ctx context.Context) ([]ChannelHealth, error) {
	return s.channelHealth, nil
}

func (s fakeAdminStore) ListQualitySnapshots(ctx context.Context, limit int) ([]QualitySnapshot, error) {
	return s.qualitySnapshots[:min(limit, len(s.qualitySnapshots))], nil
}

func (s fakeAdminStore) ListLowQualityInfos(ctx context.Context, limit int) ([]LowQualityInfo, error) {
	return s.lowQualityInfos[:min(limit, len(s.lowQualityInfos))], nil
}

func (s fakeAdminStore) GetDetailJobReport(ctx context.Context, filter DetailJobFilter) (DetailJobReport, error) {
	return s.detailJobReport, nil
}

func (s fakeAdminStore) GetDetailJob(ctx context.Context, id int64) (DetailJobDetail, error) {
	return DetailJobDetail{ID: id, Title: "详情补偿任务"}, nil
}

func (s fakeAdminStore) RetryDetailJob(ctx context.Context, id int64) (ActionResult, error) {
	return ActionResult{Action: "retry_detail_job", Message: "已重新入队详情补偿任务", Data: map[string]any{"detail_job_id": id}}, nil
}

func (s fakeAdminStore) CancelDetailJob(ctx context.Context, id int64) (ActionResult, error) {
	return ActionResult{Action: "cancel_detail_job", Message: "已取消详情补偿任务", Data: map[string]any{"detail_job_id": id}}, nil
}

func (s fakeAdminStore) BatchRetryDetailJobs(ctx context.Context, filter DetailJobFilter) (ActionResult, error) {
	return ActionResult{Action: "batch_retry_detail_jobs", Message: "已批量重新入队详情补偿任务", Data: map[string]any{"matched_count": 0}}, nil
}

func (s fakeAdminStore) BatchCancelDetailJobs(ctx context.Context, filter DetailJobFilter) (ActionResult, error) {
	return ActionResult{Action: "batch_cancel_detail_jobs", Message: "已批量取消详情补偿任务", Data: map[string]any{"matched_count": 0}}, nil
}

func (s fakeAdminStore) ListCrawlTasks(ctx context.Context) ([]CrawlTask, error) {
	return s.crawlTasks, nil
}

func (s fakeAdminStore) ListCategories(ctx context.Context) ([]Category, error) {
	return s.categories, nil
}

func (s fakeAdminStore) CreateCategory(ctx context.Context, payload CategoryPayload) (Category, error) {
	return Category{ID: 3, Name: payload.Name, Code: payload.Code, Description: payload.Description}, nil
}

func (s fakeAdminStore) UpdateCategory(ctx context.Context, id int64, payload CategoryPayload) (Category, error) {
	return Category{ID: id, Name: payload.Name, Code: payload.Code, Description: payload.Description}, nil
}

func (s fakeAdminStore) ListChannels(ctx context.Context) ([]Channel, error) {
	return s.channels, nil
}

func (s fakeAdminStore) CreateChannel(ctx context.Context, payload ChannelPayload) (Channel, error) {
	return Channel{
		ID:            7,
		Name:          payload.Name,
		Code:          payload.Code,
		BaseURL:       payload.BaseURL,
		CategoryID:    payload.CategoryID,
		CrawlInterval: payload.CrawlInterval,
		IsActive:      payload.IsActive,
	}, nil
}

func (s fakeAdminStore) UpdateChannel(ctx context.Context, id int64, payload ChannelPayload) (Channel, error) {
	return Channel{
		ID:            id,
		Name:          payload.Name,
		Code:          payload.Code,
		BaseURL:       payload.BaseURL,
		CategoryID:    payload.CategoryID,
		CrawlInterval: payload.CrawlInterval,
		IsActive:      payload.IsActive,
	}, nil
}

func (s fakeAdminStore) ListAuditLogs(ctx context.Context, limit int) ([]AuditLog, error) {
	return s.auditLogs[:min(limit, len(s.auditLogs))], nil
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
		channelHealth: []ChannelHealth{
			{ChannelCode: "weibo", ChannelName: "微博", HealthScore: 92, HealthLevel: "healthy"},
		},
		qualitySnapshots: []QualitySnapshot{
			{CategoryCode: "all", TotalCount: 611, SeedDetailCount: 2, RealDetailTotal: 20, RealCompleteDetailCount: 8, RealCompleteDetailRatio: 40.0},
		},
		lowQualityInfos: []LowQualityInfo{
			{ID: 1, Title: "正文缺失", IssueReason: "正文为空"},
		},
		crawlTasks: []CrawlTask{
			{TaskCode: "weibo-hot", TaskName: "微博热点", Status: "active"},
		},
		auditLogs: []AuditLog{
			{ID: 1, AdminEmail: "admin@example.com", Action: "GET /api/v1/admin/overview"},
		},
	})

	runs, err := service.ListCrawlRuns(context.Background(), 1)
	if err != nil {
		t.Fatalf("ListCrawlRuns returned error: %v", err)
	}
	if len(runs) != 1 || runs[0].ChannelCode != "weibo" {
		t.Fatalf("runs = %+v", runs)
	}

	healthItems, err := service.ListChannelHealth(context.Background())
	if err != nil {
		t.Fatalf("ListChannelHealth returned error: %v", err)
	}
	if len(healthItems) != 1 || healthItems[0].HealthLevel != "healthy" {
		t.Fatalf("healthItems = %+v", healthItems)
	}

	snapshots, err := service.ListQualitySnapshots(context.Background(), 5)
	if err != nil {
		t.Fatalf("ListQualitySnapshots returned error: %v", err)
	}
	if snapshots[0].TotalCount != 611 {
		t.Fatalf("snapshots = %+v", snapshots)
	}
	if snapshots[0].SeedDetailCount != 2 || snapshots[0].RealCompleteDetailRatio != 40.0 {
		t.Fatalf("snapshots missing real detail metrics: %+v", snapshots)
	}

	lowQualityInfos, err := service.ListLowQualityInfos(context.Background(), 5)
	if err != nil {
		t.Fatalf("ListLowQualityInfos returned error: %v", err)
	}
	if lowQualityInfos[0].IssueReason != "正文为空" {
		t.Fatalf("lowQualityInfos = %+v", lowQualityInfos)
	}

	tasks, err := service.ListCrawlTasks(context.Background())
	if err != nil {
		t.Fatalf("ListCrawlTasks returned error: %v", err)
	}
	if tasks[0].TaskCode != "weibo-hot" {
		t.Fatalf("tasks = %+v", tasks)
	}

	logs, err := service.ListAuditLogs(context.Background(), 5)
	if err != nil {
		t.Fatalf("ListAuditLogs returned error: %v", err)
	}
	if logs[0].Action != "GET /api/v1/admin/overview" {
		t.Fatalf("logs = %+v", logs)
	}
}

func TestServiceManagesCategoriesAndChannels(t *testing.T) {
	service := NewService(fakeAdminStore{
		categories: []Category{
			{ID: 1, Name: "科技", Code: "tech", Description: "科技热点"},
		},
		channels: []Channel{
			{ID: 2, Name: "新浪体育", Code: "sina_sports", BaseURL: "https://sports.sina.com.cn/", CategoryID: 3, CategoryName: "体育", CrawlInterval: 45, IsActive: 1},
		},
	})

	categories, err := service.ListCategories(context.Background())
	if err != nil {
		t.Fatalf("ListCategories returned error: %v", err)
	}
	if len(categories) != 1 || categories[0].Code != "tech" {
		t.Fatalf("categories = %+v", categories)
	}

	createdCategory, err := service.CreateCategory(context.Background(), CategoryPayload{
		Name: " 体育 ",
		Code: " sports ",
	})
	if err != nil {
		t.Fatalf("CreateCategory returned error: %v", err)
	}
	if createdCategory.Name != "体育" || createdCategory.Code != "sports" {
		t.Fatalf("created category = %+v", createdCategory)
	}

	channels, err := service.ListChannels(context.Background())
	if err != nil {
		t.Fatalf("ListChannels returned error: %v", err)
	}
	if len(channels) != 1 || channels[0].Code != "sina_sports" {
		t.Fatalf("channels = %+v", channels)
	}

	updatedChannel, err := service.UpdateChannel(context.Background(), 2, ChannelPayload{
		Name:          " 央视体育网 ",
		Code:          " cctv_sports ",
		BaseURL:       " https://sports.cctv.com/ ",
		CategoryID:    3,
		CrawlInterval: 30,
		IsActive:      1,
	})
	if err != nil {
		t.Fatalf("UpdateChannel returned error: %v", err)
	}
	if updatedChannel.Name != "央视体育网" || updatedChannel.BaseURL != "https://sports.cctv.com/" {
		t.Fatalf("updated channel = %+v", updatedChannel)
	}
}

func TestServiceRejectsInvalidConfigurationPayload(t *testing.T) {
	service := NewService(fakeAdminStore{})

	if _, err := service.CreateCategory(context.Background(), CategoryPayload{Name: " ", Code: "tech"}); err == nil {
		t.Fatal("CreateCategory accepted blank name")
	}
	if _, err := service.CreateChannel(context.Background(), ChannelPayload{Name: "微博", Code: "weibo", CategoryID: 0, CrawlInterval: 60, IsActive: 1}); err == nil {
		t.Fatal("CreateChannel accepted invalid category id")
	}
	if _, err := service.CreateChannel(context.Background(), ChannelPayload{Name: "微博", Code: "weibo", CategoryID: 1, CrawlInterval: 0, IsActive: 1}); err == nil {
		t.Fatal("CreateChannel accepted invalid crawl interval")
	}
}

func TestServiceRunsAdminActions(t *testing.T) {
	runner := &fakeActionRunner{}
	service := NewServiceWithActions(fakeAdminStore{}, runner)

	result, err := service.TriggerCrawl(context.Background(), " weibo ")
	if err != nil {
		t.Fatalf("TriggerCrawl returned error: %v", err)
	}
	if runner.channelCode != "weibo" {
		t.Fatalf("channel code = %q, want weibo", runner.channelCode)
	}
	if result.Action != "trigger_crawl" {
		t.Fatalf("action = %q, want trigger_crawl", result.Action)
	}

	if _, err := service.TriggerCrawl(context.Background(), " "); err == nil {
		t.Fatal("TriggerCrawl accepted blank channel code")
	}

	result, err = service.RefreshQuality(context.Background())
	if err != nil {
		t.Fatalf("RefreshQuality returned error: %v", err)
	}
	if result.Action != "refresh_quality" {
		t.Fatalf("action = %q, want refresh_quality", result.Action)
	}

	result, err = service.RetryLowQualityDetails(context.Background(), 200)
	if err != nil {
		t.Fatalf("RetryLowQualityDetails returned error: %v", err)
	}
	if result.Action != "retry_low_quality_details" {
		t.Fatalf("action = %q, want retry_low_quality_details", result.Action)
	}
	if runner.limit != 50 {
		t.Fatalf("retry limit = %d, want 50", runner.limit)
	}

	report, err := service.GetEventAnalysisQualityReport(context.Background(), 200)
	if err != nil {
		t.Fatalf("GetEventAnalysisQualityReport returned error: %v", err)
	}
	if runner.action != "event_analysis_quality_report" {
		t.Fatalf("action = %q, want event_analysis_quality_report", runner.action)
	}
	if runner.limit != 100 {
		t.Fatalf("event analysis report limit = %d, want 100", runner.limit)
	}
	if report["summary"] == nil {
		t.Fatalf("event analysis report missing summary: %+v", report)
	}

	configs, err := service.ListLLMModelConfigs(context.Background())
	if err != nil {
		t.Fatalf("ListLLMModelConfigs returned error: %v", err)
	}
	if runner.action != "list_llm_model_configs" || configs == nil {
		t.Fatalf("llm configs action=%q configs=%+v", runner.action, configs)
	}

	created, err := service.CreateLLMModelConfig(context.Background(), LLMModelConfigPayload{
		ProviderName: "千问", ProviderCode: "qwen", BaseURL: "http://127.0.0.1:8001/v1", ModelName: "qwen-local", IsEnabled: 1, DailyCallLimit: 10, Priority: 10,
	})
	if err != nil {
		t.Fatalf("CreateLLMModelConfig returned error: %v", err)
	}
	if runner.action != "create_llm_model_config" || created == nil {
		t.Fatalf("created llm config action=%q created=%+v", runner.action, created)
	}

	result, err = service.EnqueueEventAnalysisDetailJobs(context.Background(), 200)
	if err != nil {
		t.Fatalf("EnqueueEventAnalysisDetailJobs returned error: %v", err)
	}
	if result.Action != "event_analysis_detail_jobs" {
		t.Fatalf("action = %q, want event_analysis_detail_jobs", result.Action)
	}
	if runner.limit != 100 {
		t.Fatalf("event analysis enqueue limit = %d, want 100", runner.limit)
	}

	result, err = service.RebuildStaleEventAnalysis(context.Background(), 2000)
	if err != nil {
		t.Fatalf("RebuildStaleEventAnalysis returned error: %v", err)
	}
	if result.Action != "rebuild_stale_event_analysis" {
		t.Fatalf("action = %q, want rebuild_stale_event_analysis", result.Action)
	}
	if runner.limit != 1000 {
		t.Fatalf("stale event analysis limit = %d, want 1000", runner.limit)
	}
}

func min(left int, right int) int {
	if left < right {
		return left
	}
	return right
}
