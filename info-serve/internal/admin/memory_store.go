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
