package audit

import "context"

// Store 定义审计日志写入能力。
type Store interface {
	CreateAuditLog(ctx context.Context, input RecordInput) error
}

// RecordInput 是写入 admin_audit_log 的业务入参。
type RecordInput struct {
	AdminUserID int64
	Action      string
	TargetType  string
	TargetID    string
	IPAddress   string
}

// Service 封装管理后台审计规则。
type Service struct {
	store Store
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

func (s *Service) Record(ctx context.Context, input RecordInput) error {
	if s == nil || s.store == nil || input.AdminUserID == 0 {
		return nil
	}
	return s.store.CreateAuditLog(ctx, input)
}
