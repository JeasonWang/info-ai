package audit

import "context"

// MemoryStore 是本地开发默认使用的空审计存储。
type MemoryStore struct{}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{}
}

func (s *MemoryStore) CreateAuditLog(ctx context.Context, input RecordInput) error {
	return nil
}
