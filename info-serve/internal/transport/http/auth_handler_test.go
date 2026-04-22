package transporthttp

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"info-serve/internal/auth"
)

func TestAuthHandlerRegistersLogsInAndReturnsCurrentUser(t *testing.T) {
	authService := auth.NewService(auth.NewMemoryStore())
	handler := NewAuthHandler(authService)

	registerReq := httptest.NewRequest(http.MethodPost, "/api/auth/register", strings.NewReader(`{"email":"user@example.com","password":"StrongerPass123"}`))
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	handler.Register(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d, want %d", registerRes.Code, http.StatusCreated)
	}

	loginReq := httptest.NewRequest(http.MethodPost, "/api/auth/login", strings.NewReader(`{"email":"user@example.com","password":"StrongerPass123"}`))
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	handler.Login(loginRes, loginReq)
	if loginRes.Code != http.StatusOK {
		t.Fatalf("login status = %d, want %d", loginRes.Code, http.StatusOK)
	}
	var loginBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	if err := json.Unmarshal(loginRes.Body.Bytes(), &loginBody); err != nil {
		t.Fatalf("invalid login json: %v", err)
	}
	if loginBody.Data.Token == "" {
		t.Fatal("token should not be empty")
	}

	meReq := httptest.NewRequest(http.MethodGet, "/api/me", nil)
	meReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	meRes := httptest.NewRecorder()
	handler.Me(meRes, meReq)
	if meRes.Code != http.StatusOK {
		t.Fatalf("me status = %d, want %d", meRes.Code, http.StatusOK)
	}
}

func TestHealthReturnsServiceStatus(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	res := httptest.NewRecorder()

	Health(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
	var body struct {
		Data struct {
			Service string `json:"service"`
			Status  string `json:"status"`
		} `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Data.Service != "info-serve" || body.Data.Status != "running" {
		t.Fatalf("body = %+v", body)
	}
}
