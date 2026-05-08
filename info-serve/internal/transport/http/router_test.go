package transporthttp

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/events"
)

func TestRouterServesHealthAndAuthRoutes(t *testing.T) {
	router := NewRouter(Services{
		Auth:   auth.NewService(auth.NewMemoryStore()),
		Events: events.NewService(events.NewMemoryStore()),
		Admin:  admin.NewService(admin.NewMemoryStore()),
		Audit:  audit.NewService(audit.NewMemoryStore()),
	})

	healthReq := httptest.NewRequest(http.MethodGet, "/health", nil)
	healthRes := httptest.NewRecorder()
	router.ServeHTTP(healthRes, healthReq)
	if healthRes.Code != http.StatusOK {
		t.Fatalf("health status = %d, want %d", healthRes.Code, http.StatusOK)
	}

	registerReq := httptest.NewRequest(http.MethodPost, "/api/auth/register", bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`))
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	router.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d, want %d", registerRes.Code, http.StatusCreated)
	}
	var body struct {
		Code int `json:"code"`
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	if err := json.Unmarshal(registerRes.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Code != 0 {
		t.Fatalf("code = %d, want 0", body.Code)
	}
	if body.Data.Token == "" {
		t.Fatal("register should return login token")
	}
}
