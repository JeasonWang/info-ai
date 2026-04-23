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

func (s *MemoryStore) ListQualitySnapshots(ctx context.Context, limit int) ([]QualitySnapshot, error) {
	return []QualitySnapshot{}, nil
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
