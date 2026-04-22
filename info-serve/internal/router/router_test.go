package router

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthRoute(t *testing.T) {
	r := New()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}

	var body map[string]any
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json response: %v", err)
	}
	if body["code"] != float64(0) {
		t.Fatalf("code = %v, want 0", body["code"])
	}
}

func TestRegisterRejectsInvalidEmail(t *testing.T) {
	r := New()
	payload := bytes.NewBufferString(`{"email":"not-email","password":"StrongerPass123"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/auth/register", payload)
	req.Header.Set("Content-Type", "application/json")
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusBadRequest)
	}
}

func TestRegisterAcceptsEmailAndPasswordContract(t *testing.T) {
	r := New()
	payload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/auth/register", payload)
	req.Header.Set("Content-Type", "application/json")
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusCreated {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusCreated)
	}

	var body map[string]any
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json response: %v", err)
	}
	if body["code"] != float64(0) {
		t.Fatalf("code = %v, want 0", body["code"])
	}
}

func TestLoginAndMeUseBearerSession(t *testing.T) {
	r := New()
	registerPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d, want %d", registerRes.Code, http.StatusCreated)
	}

	loginPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/auth/login", loginPayload)
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	r.ServeHTTP(loginRes, loginReq)
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
		t.Fatal("login token should not be empty")
	}

	meReq := httptest.NewRequest(http.MethodGet, "/api/me", nil)
	meReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	meRes := httptest.NewRecorder()
	r.ServeHTTP(meRes, meReq)
	if meRes.Code != http.StatusOK {
		t.Fatalf("me status = %d, want %d", meRes.Code, http.StatusOK)
	}
}

func TestAdminHealthRequiresAdminRole(t *testing.T) {
	r := New()
	registerPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d, want %d", registerRes.Code, http.StatusCreated)
	}

	loginPayload := bytes.NewBufferString(`{"email":"user@example.com","password":"StrongerPass123"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/auth/login", loginPayload)
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	r.ServeHTTP(loginRes, loginReq)

	var loginBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	_ = json.Unmarshal(loginRes.Body.Bytes(), &loginBody)

	adminReq := httptest.NewRequest(http.MethodGet, "/api/admin/health", nil)
	adminReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	adminRes := httptest.NewRecorder()
	r.ServeHTTP(adminRes, adminReq)
	if adminRes.Code != http.StatusForbidden {
		t.Fatalf("admin health status = %d, want %d", adminRes.Code, http.StatusForbidden)
	}
}
