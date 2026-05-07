package app

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/events"
)

func TestNewHTTPHandlerWiresServicesWithMemoryStores(t *testing.T) {
	handler := NewHTTPHandler(Stores{
		Auth:   auth.NewMemoryStore(),
		Events: events.NewMemoryStore(),
		Admin:  admin.NewMemoryStore(),
		Audit:  audit.NewMemoryStore(),
	})
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	res := httptest.NewRecorder()

	handler.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
	var body struct {
		Code int `json:"code"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Code != 0 {
		t.Fatalf("code = %d, want 0", body.Code)
	}
}
