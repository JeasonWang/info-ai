package middleware

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"info-serve/internal/audit"
	"info-serve/internal/auth"
)

type auditStore struct {
	records []audit.RecordInput
}

func (s *auditStore) CreateAuditLog(ctx context.Context, input audit.RecordInput) error {
	s.records = append(s.records, input)
	return nil
}

func TestRequireAdminWithAuditRejectsAnonymousAndRegularUsers(t *testing.T) {
	authService := auth.NewService(auth.NewMemoryStore())
	next := RequireAdminWithAudit(authService, audit.NewService(&auditStore{}), func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})

	anonymousRes := httptest.NewRecorder()
	next(anonymousRes, httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil))
	if anonymousRes.Code != http.StatusUnauthorized {
		t.Fatalf("anonymous status = %d, want %d", anonymousRes.Code, http.StatusUnauthorized)
	}

	_, err := authService.Register(context.Background(), auth.RegisterInput{Email: "user@example.com", Password: "StrongerPass123"})
	if err != nil {
		t.Fatalf("Register returned error: %v", err)
	}
	login, err := authService.Login(context.Background(), auth.LoginInput{Email: "user@example.com", Password: "StrongerPass123"})
	if err != nil {
		t.Fatalf("Login returned error: %v", err)
	}
	userReq := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	userReq.Header.Set("Authorization", "Bearer "+login.Token)
	userRes := httptest.NewRecorder()
	next(userRes, userReq)
	if userRes.Code != http.StatusForbidden {
		t.Fatalf("regular user status = %d, want %d", userRes.Code, http.StatusForbidden)
	}
}

func TestRequireAdminWithAuditAllowsAdminAndRecordsAuditLog(t *testing.T) {
	store := auth.NewMemoryStore()
	authService := auth.NewService(store)
	hash, err := auth.HashPassword("Admin123456")
	if err != nil {
		t.Fatalf("HashPassword returned error: %v", err)
	}
	_, err = store.CreateUser(context.Background(), auth.CreateUserParams{
		Email:        "admin@example.com",
		PasswordHash: hash,
		Role:         "admin",
	})
	if err != nil {
		t.Fatalf("CreateUser returned error: %v", err)
	}
	login, err := authService.Login(context.Background(), auth.LoginInput{Email: "admin@example.com", Password: "Admin123456"})
	if err != nil {
		t.Fatalf("Login returned error: %v", err)
	}

	audits := &auditStore{}
	nextCalled := false
	next := RequireAdminWithAudit(authService, audit.NewService(audits), func(w http.ResponseWriter, r *http.Request) {
		nextCalled = true
		w.WriteHeader(http.StatusNoContent)
	})
	req := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	req.Header.Set("Authorization", "Bearer "+login.Token)
	req.Header.Set("X-Forwarded-For", "10.0.0.8, 10.0.0.9")
	res := httptest.NewRecorder()

	next(res, req)

	if res.Code != http.StatusNoContent || !nextCalled {
		t.Fatalf("status = %d nextCalled=%v, want 204 and true", res.Code, nextCalled)
	}
	if len(audits.records) != 1 {
		t.Fatalf("audit records len = %d, want 1", len(audits.records))
	}
	if audits.records[0].IPAddress != "10.0.0.8" {
		t.Fatalf("audit ip = %q, want 10.0.0.8", audits.records[0].IPAddress)
	}
}
