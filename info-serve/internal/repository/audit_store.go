package repository

import (
	"context"

	"info-serve/internal/audit"
)

func (s *MySQLStore) CreateAuditLog(ctx context.Context, input audit.RecordInput) error {
	_, err := s.db.ExecContext(
		ctx,
		`INSERT INTO admin_audit_log (admin_user_id, action, target_type, target_id, ip_address)
VALUES (?, ?, ?, ?, ?)`,
		input.AdminUserID,
		input.Action,
		input.TargetType,
		input.TargetID,
		input.IPAddress,
	)
	return err
}
