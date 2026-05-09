package admin

import "context"

// ActionResult 是管理动作统一返回结构，便于后台展示执行结果。
type ActionResult struct {
	Action  string         `json:"action"`
	Message string         `json:"message"`
	Data    map[string]any `json:"data"`
}

// ActionRunner 定义管理后台可触发的采集和治理动作。
type ActionRunner interface {
	TriggerCrawl(ctx context.Context, channelCode string) (ActionResult, error)
	GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error)
	GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error)
	ListLLMModelConfigs(ctx context.Context) (any, error)
	CreateLLMModelConfig(ctx context.Context, payload map[string]any) (any, error)
	UpdateLLMModelConfig(ctx context.Context, id int64, payload map[string]any) (any, error)
	EnqueueEventAnalysisDetailJobs(ctx context.Context, limit int) (ActionResult, error)
	RebuildStaleEventAnalysis(ctx context.Context, limit int) (ActionResult, error)
	RebuildEvents(ctx context.Context) (ActionResult, error)
	RefreshQuality(ctx context.Context) (ActionResult, error)
	RetryLowQualityDetails(ctx context.Context, limit int) (ActionResult, error)
	ArchiveLowQuality(ctx context.Context) (ActionResult, error)
	ArchiveDuplicateTitles(ctx context.Context) (ActionResult, error)
}

// MemoryActionRunner 是测试和本地空依赖模式使用的动作执行器。
type MemoryActionRunner struct{}

func NewMemoryActionRunner() *MemoryActionRunner {
	return &MemoryActionRunner{}
}

func (r *MemoryActionRunner) TriggerCrawl(ctx context.Context, channelCode string) (ActionResult, error) {
	return ActionResult{
		Action:  "trigger_crawl",
		Message: "本地测试模式已模拟触发采集",
		Data:    map[string]any{"channel_code": channelCode},
	}, nil
}

func (r *MemoryActionRunner) GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error) {
	return map[string]any{
		"summary": map[string]any{
			"real_count":               2,
			"complete_count":           1,
			"high_value_partial_count": 1,
			"usable_count":             2,
			"needs_attention_count":    0,
			"complete_ratio":           50.0,
			"usable_ratio":             100.0,
			"needs_attention_ratio":    0.0,
			"weak_channels":            []any{},
		},
		"channels": []any{
			map[string]any{
				"channel_code":              "weibo",
				"channel_name":              "微博",
				"real_count":                2,
				"complete_count":            1,
				"complete_ratio":            50.0,
				"high_value_partial_count":  1,
				"usable_count":              2,
				"usable_ratio":              100.0,
				"needs_attention_count":     0,
				"needs_attention_ratio":     0.0,
				"avg_detail_score":          82.5,
				"avg_detail_content_length": 320.0,
				"top_failure_reasons":       []any{},
				"top_detail_strategies":     []any{map[string]any{"strategy": "mobile_search", "count": 2}},
				"credential_health":         map[string]any{"health": "ready"},
				"weak_samples":              []any{},
			},
		},
	}, nil
}

func (r *MemoryActionRunner) GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error) {
	return map[string]any{
		"summary": map[string]any{
			"active_event_count":      1,
			"analyzed_count":          1,
			"missing_analysis_count":  0,
			"low_confidence_count":    0,
			"fallback_count":          0,
			"weak_source_event_count": 0,
			"avg_confidence":          0.86,
			"avg_quality_score":       82.0,
			"risk_event_count":        0,
		},
		"risk_events": []any{},
	}, nil
}

func (r *MemoryActionRunner) ListLLMModelConfigs(ctx context.Context) (any, error) {
	return []any{
		map[string]any{
			"id":               1,
			"provider_name":    "千问",
			"provider_code":    "qwen",
			"base_url":         "http://127.0.0.1:8001/v1",
			"api_key":          "",
			"model_name":       "qwen2.5-14b-instruct",
			"is_enabled":       0,
			"daily_call_limit": 1000,
			"daily_call_count": 0,
			"priority":         10,
		},
	}, nil
}

func (r *MemoryActionRunner) CreateLLMModelConfig(ctx context.Context, payload map[string]any) (any, error) {
	payload["id"] = 1
	return payload, nil
}

func (r *MemoryActionRunner) UpdateLLMModelConfig(ctx context.Context, id int64, payload map[string]any) (any, error) {
	payload["id"] = id
	return payload, nil
}

func (r *MemoryActionRunner) EnqueueEventAnalysisDetailJobs(ctx context.Context, limit int) (ActionResult, error) {
	return ActionResult{
		Action:  "event_analysis_detail_jobs",
		Message: "本地测试模式已模拟入队事件分析弱来源",
		Data:    map[string]any{"limit": limit, "created_count": 0, "skipped_count": 0},
	}, nil
}

func (r *MemoryActionRunner) RebuildStaleEventAnalysis(ctx context.Context, limit int) (ActionResult, error) {
	return ActionResult{
		Action:  "rebuild_stale_event_analysis",
		Message: "本地测试模式已模拟处理过期事件分析",
		Data:    map[string]any{"limit": limit, "rebuilt": false},
	}, nil
}

func (r *MemoryActionRunner) RebuildEvents(ctx context.Context) (ActionResult, error) {
	return ActionResult{Action: "rebuild_events", Message: "本地测试模式已模拟重建事件", Data: map[string]any{}}, nil
}

func (r *MemoryActionRunner) RefreshQuality(ctx context.Context) (ActionResult, error) {
	return ActionResult{Action: "refresh_quality", Message: "本地测试模式已模拟刷新质量", Data: map[string]any{}}, nil
}

func (r *MemoryActionRunner) RetryLowQualityDetails(ctx context.Context, limit int) (ActionResult, error) {
	return ActionResult{
		Action:  "retry_low_quality_details",
		Message: "本地测试模式已模拟重抓低完整详情",
		Data:    map[string]any{"limit": limit},
	}, nil
}

func (r *MemoryActionRunner) ArchiveLowQuality(ctx context.Context) (ActionResult, error) {
	return ActionResult{Action: "archive_low_quality", Message: "本地测试模式已模拟归档低质量内容", Data: map[string]any{}}, nil
}

func (r *MemoryActionRunner) ArchiveDuplicateTitles(ctx context.Context) (ActionResult, error) {
	return ActionResult{Action: "archive_duplicate_titles", Message: "本地测试模式已模拟归档重复标题", Data: map[string]any{}}, nil
}
