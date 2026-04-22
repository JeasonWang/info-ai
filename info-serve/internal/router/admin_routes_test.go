package router

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"info-serve/internal/admin"
	"info-serve/internal/auth"
)

type stubAdminStore struct{}

func (s stubAdminStore) GetOverview(ctx context.Context) (admin.Overview, error) {
	return admin.Overview{
		ChannelCount: 12,
		EventCount:   199,
		InfoCount:    611,
		Quality: admin.QualityOverview{
			DuplicateTitleCount: 3,
			EmptyContentCount:   4,
		},
		RecentRuns: []admin.CrawlRunSummary{
			{ChannelCode: "weibo", Status: "success", SavedCount: 10},
		},
	}, nil
}

func (s stubAdminStore) ListCrawlRuns(ctx context.Context, limit int) ([]admin.CrawlRunSummary, error) {
	return []admin.CrawlRunSummary{{ChannelCode: "weibo", Status: "success", SavedCount: 10}}, nil
}

func (s stubAdminStore) ListQualitySnapshots(ctx context.Context, limit int) ([]admin.QualitySnapshot, error) {
	return []admin.QualitySnapshot{{CategoryCode: "all", TotalCount: 611, DuplicateTitleCount: 3}}, nil
}

func (s stubAdminStore) ListCrawlTasks(ctx context.Context) ([]admin.CrawlTask, error) {
	return []admin.CrawlTask{{TaskCode: "weibo-hot", TaskName: "微博热点", Status: "active"}}, nil
}

func TestAdminOverviewRequiresLogin(t *testing.T) {
	r := NewWithDependencies(nil, nil, admin.NewService(stubAdminStore{}))
	req := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusUnauthorized)
	}
}

func TestAdminOverviewRequiresAdminRole(t *testing.T) {
	r := NewWithDependencies(nil, nil, admin.NewService(stubAdminStore{}))
	token := registerAndLogin(t, r, "user@example.com", "StrongerPass123")
	req := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusForbidden)
	}
}

func TestAdminOverviewReturnsMetricsForAdmin(t *testing.T) {
	store := auth.NewMemoryStore()
	service := auth.NewService(store)
	_, err := store.CreateUser(context.Background(), auth.CreateUserParams{
		Email:        "admin@example.com",
		PasswordHash: mustHashPassword(t, "Admin123456"),
		Role:         "admin",
	})
	if err != nil {
		t.Fatalf("CreateUser returned error: %v", err)
	}

	r := NewWithDependencies(service, nil, admin.NewService(stubAdminStore{}))
	token := loginOnly(t, r, "admin@example.com", "Admin123456")
	req := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
	var body struct {
		Data admin.Overview `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Data.EventCount != 199 {
		t.Fatalf("event_count = %d, want 199", body.Data.EventCount)
	}
	if body.Data.RecentRuns[0].ChannelCode != "weibo" {
		t.Fatalf("recent run = %+v", body.Data.RecentRuns[0])
	}
}

func TestAdminMonitoringRoutesReturnListsForAdmin(t *testing.T) {
	store := auth.NewMemoryStore()
	service := auth.NewService(store)
	_, err := store.CreateUser(context.Background(), auth.CreateUserParams{
		Email:        "admin@example.com",
		PasswordHash: mustHashPassword(t, "Admin123456"),
		Role:         "admin",
	})
	if err != nil {
		t.Fatalf("CreateUser returned error: %v", err)
	}
	r := NewWithDependencies(service, nil, admin.NewService(stubAdminStore{}))
	token := loginOnly(t, r, "admin@example.com", "Admin123456")

	cases := []struct {
		path string
		key  string
	}{
		{path: "/api/admin/crawl-runs", key: "channel_code"},
		{path: "/api/admin/quality-snapshots", key: "category_code"},
		{path: "/api/admin/crawl-tasks", key: "task_code"},
	}

	for _, item := range cases {
		req := httptest.NewRequest(http.MethodGet, item.path, nil)
		req.Header.Set("Authorization", "Bearer "+token)
		res := httptest.NewRecorder()
		r.ServeHTTP(res, req)
		if res.Code != http.StatusOK {
			t.Fatalf("%s status = %d, want %d", item.path, res.Code, http.StatusOK)
		}
		var body struct {
			Data []map[string]any `json:"data"`
		}
		if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
			t.Fatalf("invalid json for %s: %v", item.path, err)
		}
		if len(body.Data) != 1 || body.Data[0][item.key] == "" {
			t.Fatalf("%s body = %+v", item.path, body.Data)
		}
	}
}

func registerAndLogin(t *testing.T, r http.Handler, email string, password string) string {
	t.Helper()
	registerPayload := stringsReader(`{"email":"` + email + `","password":"` + password + `"}`)
	registerReq := httptest.NewRequest(http.MethodPost, "/api/auth/register", registerPayload)
	registerReq.Header.Set("Content-Type", "application/json")
	registerRes := httptest.NewRecorder()
	r.ServeHTTP(registerRes, registerReq)
	if registerRes.Code != http.StatusCreated {
		t.Fatalf("register status = %d", registerRes.Code)
	}
	return loginOnly(t, r, email, password)
}

func loginOnly(t *testing.T, r http.Handler, email string, password string) string {
	t.Helper()
	loginPayload := stringsReader(`{"email":"` + email + `","password":"` + password + `"}`)
	loginReq := httptest.NewRequest(http.MethodPost, "/api/auth/login", loginPayload)
	loginReq.Header.Set("Content-Type", "application/json")
	loginRes := httptest.NewRecorder()
	r.ServeHTTP(loginRes, loginReq)
	if loginRes.Code != http.StatusOK {
		t.Fatalf("login status = %d", loginRes.Code)
	}
	var loginBody struct {
		Data struct {
			Token string `json:"token"`
		} `json:"data"`
	}
	if err := json.Unmarshal(loginRes.Body.Bytes(), &loginBody); err != nil {
		t.Fatalf("invalid login json: %v", err)
	}
	return loginBody.Data.Token
}

func mustHashPassword(t *testing.T, password string) string {
	t.Helper()
	hash, err := auth.HashPassword(password)
	if err != nil {
		t.Fatalf("HashPassword returned error: %v", err)
	}
	return hash
}

func stringsReader(value string) *strings.Reader {
	return strings.NewReader(value)
}
