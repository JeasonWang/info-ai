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
	EnqueueEventAnalysisDetailJobs(ctx context.Context, limit int) (ActionResult, error)
	PrioritizeWeakSourceGovernance(ctx context.Context, limit int) (ActionResult, error)
	RebuildStaleEventAnalysis(ctx context.Context, limit int) (ActionResult, error)
	RebuildEvents(ctx context.Context) (ActionResult, error)
	RefreshQuality(ctx context.Context) (ActionResult, error)
	RetryLowQualityDetails(ctx context.Context, limit int) (ActionResult, error)
	ArchiveLowQuality(ctx context.Context) (ActionResult, error)
	ArchiveDuplicateTitles(ctx context.Context) (ActionResult, error)
	TestChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error)
	InvalidateCredentials(ctx context.Context, channelCode string) (ActionResult, error)
	TestLLMChat(ctx context.Context, payload LLMChatTestPayload) (map[string]any, error)
	ChatLLM(ctx context.Context, payload LLMChatPayload) (map[string]any, error)
}

type LLMActionRunner interface {
	TestLLMChat(ctx context.Context, payload LLMChatTestPayload) (map[string]any, error)
	ChatLLM(ctx context.Context, payload LLMChatPayload) (map[string]any, error)
}

type CompositeActionRunner struct {
	ActionRunner
	llmRunner LLMActionRunner
}

func NewCompositeActionRunner(base ActionRunner, llmRunner LLMActionRunner) *CompositeActionRunner {
	if base == nil {
		base = NewMemoryActionRunner()
	}
	return &CompositeActionRunner{ActionRunner: base, llmRunner: llmRunner}
}

func (r *CompositeActionRunner) TestLLMChat(ctx context.Context, payload LLMChatTestPayload) (map[string]any, error) {
	if r.llmRunner != nil {
		return r.llmRunner.TestLLMChat(ctx, payload)
	}
	return r.ActionRunner.TestLLMChat(ctx, payload)
}

func (r *CompositeActionRunner) ChatLLM(ctx context.Context, payload LLMChatPayload) (map[string]any, error) {
	if r.llmRunner != nil {
		return r.llmRunner.ChatLLM(ctx, payload)
	}
	return r.ActionRunner.ChatLLM(ctx, payload)
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

func (r *MemoryActionRunner) EnqueueEventAnalysisDetailJobs(ctx context.Context, limit int) (ActionResult, error) {
	return ActionResult{
		Action:  "event_analysis_detail_jobs",
		Message: "本地测试模式已模拟入队事件分析弱来源",
		Data:    map[string]any{"limit": limit, "created_count": 0, "skipped_count": 0},
	}, nil
}

func (r *MemoryActionRunner) PrioritizeWeakSourceGovernance(ctx context.Context, limit int) (ActionResult, error) {
	return ActionResult{
		Action:  "prioritize_weak_source_governance",
		Message: "本地测试模式已模拟优先治理弱来源事件",
		Data:    map[string]any{"limit": limit, "enqueue": map[string]any{}, "process": map[string]any{}, "fact_source": map[string]any{}},
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

func (r *MemoryActionRunner) TestChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	return map[string]any{
		"channel_code":  channelCode,
		"success":       false,
		"response_code": 0,
		"message":       "本地测试模式：需要连接真实采集服务验证凭证",
	}, nil
}

func (r *MemoryActionRunner) InvalidateCredentials(ctx context.Context, channelCode string) (ActionResult, error) {
	return ActionResult{
		Action:  "invalidate_credentials",
		Message: "本地测试模式已模拟刷新采集凭证缓存",
		Data:    map[string]any{"channel_code": channelCode},
	}, nil
}

func (r *MemoryActionRunner) TestLLMChat(ctx context.Context, payload LLMChatTestPayload) (map[string]any, error) {
	return map[string]any{
		"ok":        false,
		"status":    "local_stub",
		"message":   "本地测试模式：需要连接真实采集服务验证大模型",
		"prompt":    payload.Prompt,
		"config_id": payload.ConfigID,
	}, nil
}

func (r *MemoryActionRunner) ChatLLM(ctx context.Context, payload LLMChatPayload) (map[string]any, error) {
	return map[string]any{
		"ok":        false,
		"status":    "local_stub",
		"message":   "本地测试模式：需要连接真实采集服务调用大模型",
		"user_text": payload.Message,
		"config_id": payload.ConfigID,
	}, nil
}
