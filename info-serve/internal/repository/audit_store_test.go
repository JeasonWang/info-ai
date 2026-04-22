package repository

import (
	"context"
	"database/sql"
	"os"
	"testing"

	_ "github.com/go-sql-driver/mysql"

	"info-serve/internal/audit"
)

func TestMySQLStoreCreatesAuditLog(t *testing.T) {
	dsn := os.Getenv("INFO_SERVE_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Skip("INFO_SERVE_TEST_MYSQL_DSN 未设置，跳过真实 MySQL 集成测试")
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatalf("open mysql: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	store := NewMySQLStore(db)
	err = store.CreateAuditLog(context.Background(), audit.RecordInput{
		AdminUserID: 2,
		Action:      "GET /api/admin/overview",
		TargetType:  "admin_api",
		TargetID:    "/api/admin/overview",
		IPAddress:   "127.0.0.1",
	})
	if err != nil {
		t.Fatalf("CreateAuditLog returned error: %v", err)
	}

	var count int
	err = db.QueryRow(
		`SELECT COUNT(*) FROM admin_audit_log WHERE admin_user_id = ? AND action = ?`,
		2,
		"GET /api/admin/overview",
	).Scan(&count)
	if err != nil {
		t.Fatalf("count audit log: %v", err)
	}
	if count == 0 {
		t.Fatal("expected audit log to be persisted")
	}
}
