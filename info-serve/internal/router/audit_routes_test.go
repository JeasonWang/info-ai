package router

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
)

type stubAuditStore struct {
	records []audit.RecordInput
}

func (s *stubAuditStore) CreateAuditLog(ctx context.Context, input audit.RecordInput) error {
	s.records = append(s.records, input)
	return nil
}

func TestAdminRouteWritesAuditLogForAdmin(t *testing.T) {
	authStore := auth.NewMemoryStore()
	authService := auth.NewService(authStore)
	_, err := authStore.CreateUser(context.Background(), auth.CreateUserParams{
		Email:        "admin@example.com",
		PasswordHash: mustHashPassword(t, "Admin123456"),
		Role:         "admin",
	})
	if err != nil {
		t.Fatalf("CreateUser returned error: %v", err)
	}
	auditStore := &stubAuditStore{}
	r := NewWithDependencies(
		authService,
		nil,
		admin.NewService(stubAdminStore{}),
		audit.NewService(auditStore),
	)
	token := loginOnly(t, r, "admin@example.com", "Admin123456")
	req := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
	if len(auditStore.records) != 1 {
		t.Fatalf("audit records len = %d, want 1", len(auditStore.records))
	}
	record := auditStore.records[0]
	if record.AdminUserID == 0 {
		t.Fatal("audit record should include admin user id")
	}
	if record.Action != "GET /api/admin/overview" {
		t.Fatalf("action = %q", record.Action)
	}
}
