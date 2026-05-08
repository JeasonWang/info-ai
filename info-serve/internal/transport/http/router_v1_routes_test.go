package transporthttp_test

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"info-serve/internal/admin"
	"info-serve/internal/audit"
	"info-serve/internal/auth"
	"info-serve/internal/events"
	transporthttp "info-serve/internal/transport/http"
)

func TestV1AuthRoutesMirrorLegacyAuthContract(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{})
	registerPayload := bytes.NewBufferString(`{"email":"v1-user@example.com","password":"StrongerPass123"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d, want %d", registerRes.Code, http.StatusCreated)
	}
	var registerBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	if err := json.Unmarshal(registerRes.Body.Bytes(), &registerBody); err != nil {
		t.Fatalf("invalid register json: %v", err)
	}
	if registerBody.Data.Token == "" {
		t.Fatal("register token should not be empty")
	}

	loginPayload := bytes.NewBufferString(`{"email":"v1-user@example.com","password":"StrongerPass123"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", loginPayload)
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

	meReq := httptest.NewRequest(http.MethodGet, "/api/v1/me", nil)
	meReq.Header.Set("Authorization", "Bearer "+loginBody.Data.Token)
	meRes := httptest.NewRecorder()
	r.ServeHTTP(meRes, meReq)
	if meRes.Code != http.StatusOK {
		t.Fatalf("me status = %d, want %d", meRes.Code, http.StatusOK)
	}
}

func TestV1EventRoutesMirrorLegacyEventContract(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{Events: events.NewService(stubEventStore{})})

	categoriesReq := httptest.NewRequest(http.MethodGet, "/api/v1/event-categories", nil)
	categoriesRes := httptest.NewRecorder()
	r.ServeHTTP(categoriesRes, categoriesReq)
	if categoriesRes.Code != http.StatusOK {
		t.Fatalf("categories status = %d, want %d", categoriesRes.Code, http.StatusOK)
	}

	listReq := httptest.NewRequest(http.MethodGet, "/api/v1/events?category_code=tech&sort=latest&page=2&page_size=5", nil)
	listRes := httptest.NewRecorder()
	r.ServeHTTP(listRes, listReq)
	if listRes.Code != http.StatusOK {
		t.Fatalf("list status = %d, want %d", listRes.Code, http.StatusOK)
	}
	var listBody struct {
		Data events.EventPage `json:"data"`
	}
	if err := json.Unmarshal(listRes.Body.Bytes(), &listBody); err != nil {
		t.Fatalf("invalid list json: %v", err)
	}
	if listBody.Data.Page != 2 || listBody.Data.PageSize != 5 {
		t.Fatalf("pagination = %+v", listBody.Data)
	}

	detailReq := httptest.NewRequest(http.MethodGet, "/api/v1/events/7", nil)
	detailRes := httptest.NewRecorder()
	r.ServeHTTP(detailRes, detailReq)
	if detailRes.Code != http.StatusOK {
		t.Fatalf("detail status = %d, want %d", detailRes.Code, http.StatusOK)
	}
}

func TestV1AdminRoutesRequireAdminAndWriteAuditLog(t *testing.T) {
	authStore := auth.NewMemoryStore()
	authService := auth.NewService(authStore)
	_, err := authStore.CreateUser(context.Background(), auth.CreateUserParams{
		Email:        "v1-admin@example.com",
		PasswordHash: mustHashPassword(t, "Admin123456"),
		Role:         "admin",
	})
	if err != nil {
		t.Fatalf("CreateUser returned error: %v", err)
	}
	auditStore := &stubAuditStore{}
	r := transporthttp.NewRouter(transporthttp.Services{
		Auth:  authService,
		Admin: admin.NewService(stubAdminStore{}),
		Audit: audit.NewService(auditStore),
	})
	token := loginOnly(t, r, "v1-admin@example.com", "Admin123456")

	overviewReq := httptest.NewRequest(http.MethodGet, "/api/v1/admin/overview", nil)
	overviewReq.Header.Set("Authorization", "Bearer "+token)
	overviewRes := httptest.NewRecorder()
	r.ServeHTTP(overviewRes, overviewReq)
	if overviewRes.Code != http.StatusOK {
		t.Fatalf("overview status = %d, want %d", overviewRes.Code, http.StatusOK)
	}

	updateReq := httptest.NewRequest(http.MethodPut, "/api/v1/admin/categories/1", stringsReader(`{"name":"科技","code":"tech","description":"科技热点"}`))
	updateReq.Header.Set("Authorization", "Bearer "+token)
	updateReq.Header.Set("Content-Type", "application/json")
	updateRes := httptest.NewRecorder()
	r.ServeHTTP(updateRes, updateReq)
	if updateRes.Code != http.StatusOK {
		t.Fatalf("update status = %d, want %d", updateRes.Code, http.StatusOK)
	}

	if len(auditStore.records) != 2 {
		t.Fatalf("audit records len = %d, want 2", len(auditStore.records))
	}
	if auditStore.records[0].Action != "GET /api/v1/admin/overview" {
		t.Fatalf("first audit action = %q", auditStore.records[0].Action)
	}
	if auditStore.records[1].Action != "PUT /api/v1/admin/categories/1" {
		t.Fatalf("second audit action = %q", auditStore.records[1].Action)
	}
}
