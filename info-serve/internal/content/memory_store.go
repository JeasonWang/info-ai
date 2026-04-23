package content

import "context"

// MemoryStore 为测试和无数据库启动提供最小内容数据源。
type MemoryStore struct{}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{}
}

func (s *MemoryStore) ListCategories(ctx context.Context) ([]Category, error) {
	return []Category{}, nil
}

func (s *MemoryStore) ListChannels(ctx context.Context, categoryID int64) ([]Channel, error) {
	return []Channel{}, nil
}

func (s *MemoryStore) ListInfos(ctx context.Context, params ListInfoParams) (InfoPage, error) {
	return InfoPage{Page: params.Page, PageSize: params.PageSize, Items: []InfoItem{}}, nil
}

func (s *MemoryStore) GetInfoDetail(ctx context.Context, id int64) (InfoItem, error) {
	return InfoItem{}, nil
}

func (s *MemoryStore) GetStats(ctx context.Context) (Stats, error) {
	return Stats{Categories: []CategoryStats{}}, nil
}
