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
	RebuildEvents(ctx context.Context) (ActionResult, error)
	RefreshQuality(ctx context.Context) (ActionResult, error)
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

func (r *MemoryActionRunner) RebuildEvents(ctx context.Context) (ActionResult, error) {
	return ActionResult{Action: "rebuild_events", Message: "本地测试模式已模拟重建事件", Data: map[string]any{}}, nil
}

func (r *MemoryActionRunner) RefreshQuality(ctx context.Context) (ActionResult, error) {
	return ActionResult{Action: "refresh_quality", Message: "本地测试模式已模拟刷新质量", Data: map[string]any{}}, nil
}

func (r *MemoryActionRunner) ArchiveLowQuality(ctx context.Context) (ActionResult, error) {
	return ActionResult{Action: "archive_low_quality", Message: "本地测试模式已模拟归档低质量内容", Data: map[string]any{}}, nil
}

func (r *MemoryActionRunner) ArchiveDuplicateTitles(ctx context.Context) (ActionResult, error) {
	return ActionResult{Action: "archive_duplicate_titles", Message: "本地测试模式已模拟归档重复标题", Data: map[string]any{}}, nil
}
