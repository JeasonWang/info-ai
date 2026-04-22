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

type notFoundAdminStore struct {
	stubAdminStore
}

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

func (s stubAdminStore) ListCategories(ctx context.Context) ([]admin.Category, error) {
	return []admin.Category{{ID: 1, Name: "科技", Code: "tech", Description: "科技热点"}}, nil
}

func (s stubAdminStore) CreateCategory(ctx context.Context, payload admin.CategoryPayload) (admin.Category, error) {
	return admin.Category{ID: 2, Name: payload.Name, Code: payload.Code, Description: payload.Description}, nil
}

func (s stubAdminStore) UpdateCategory(ctx context.Context, id int64, payload admin.CategoryPayload) (admin.Category, error) {
	return admin.Category{ID: id, Name: payload.Name, Code: payload.Code, Description: payload.Description}, nil
}

func (s stubAdminStore) ListChannels(ctx context.Context) ([]admin.Channel, error) {
	return []admin.Channel{{ID: 1, Name: "微博", Code: "weibo", CategoryID: 1, CategoryName: "全网", CrawlInterval: 30, IsActive: 1}}, nil
}

func (s stubAdminStore) CreateChannel(ctx context.Context, payload admin.ChannelPayload) (admin.Channel, error) {
	return admin.Channel{ID: 2, Name: payload.Name, Code: payload.Code, CategoryID: payload.CategoryID, CrawlInterval: payload.CrawlInterval, IsActive: payload.IsActive}, nil
}

func (s stubAdminStore) UpdateChannel(ctx context.Context, id int64, payload admin.ChannelPayload) (admin.Channel, error) {
	return admin.Channel{ID: id, Name: payload.Name, Code: payload.Code, CategoryID: payload.CategoryID, CrawlInterval: payload.CrawlInterval, IsActive: payload.IsActive}, nil
}

func (s notFoundAdminStore) UpdateCategory(ctx context.Context, id int64, payload admin.CategoryPayload) (admin.Category, error) {
	return admin.Category{}, admin.ErrNotFound
}

func TestAdminOverviewRequiresLogin(t *testing.T) {
	r := NewWithDependencies(nil, nil, admin.NewService(stubAdminStore{}), nil)
	req := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusUnauthorized)
	}
}

func TestAdminOverviewRequiresAdminRole(t *testing.T) {
	r := NewWithDependencies(nil, nil, admin.NewService(stubAdminStore{}), nil)
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

	r := NewWithDependencies(service, nil, admin.NewService(stubAdminStore{}), nil)
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
	r := NewWithDependencies(service, nil, admin.NewService(stubAdminStore{}), nil)
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

func TestAdminConfigurationRoutesManageCategoriesAndChannels(t *testing.T) {
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
	r := NewWithDependencies(service, nil, admin.NewService(stubAdminStore{}), nil)
	token := loginOnly(t, r, "admin@example.com", "Admin123456")

	cases := []struct {
		method string
		path   string
		body   string
		key    string
		status int
	}{
		{method: http.MethodGet, path: "/api/admin/categories", key: "code", status: http.StatusOK},
		{method: http.MethodPost, path: "/api/admin/categories", body: `{"name":"体育","code":"sports","description":"体育热点"}`, key: "code", status: http.StatusCreated},
		{method: http.MethodPut, path: "/api/admin/categories/1", body: `{"name":"科技","code":"tech","description":"科技热点"}`, key: "code", status: http.StatusOK},
		{method: http.MethodGet, path: "/api/admin/channels", key: "code", status: http.StatusOK},
		{method: http.MethodPost, path: "/api/admin/channels", body: `{"name":"新浪体育","code":"sina_sports","base_url":"https://sports.sina.com.cn/","category_id":1,"crawl_interval":30,"is_active":1}`, key: "code", status: http.StatusCreated},
		{method: http.MethodPut, path: "/api/admin/channels/1", body: `{"name":"微博","code":"weibo","base_url":"https://weibo.com/","category_id":1,"crawl_interval":45,"is_active":1}`, key: "code", status: http.StatusOK},
	}

	for _, item := range cases {
		req := httptest.NewRequest(item.method, item.path, stringsReader(item.body))
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("Content-Type", "application/json")
		res := httptest.NewRecorder()
		r.ServeHTTP(res, req)
		if res.Code != item.status {
			t.Fatalf("%s %s status = %d, want %d, body=%s", item.method, item.path, res.Code, item.status, res.Body.String())
		}
		var body struct {
			Data any `json:"data"`
		}
		if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
			t.Fatalf("invalid json for %s %s: %v", item.method, item.path, err)
		}
		if body.Data == nil {
			t.Fatalf("%s %s returned empty data", item.method, item.path)
		}
	}
}

func TestAdminConfigurationUpdateReturnsNotFound(t *testing.T) {
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
	r := NewWithDependencies(service, nil, admin.NewService(notFoundAdminStore{}), nil)
	token := loginOnly(t, r, "admin@example.com", "Admin123456")

	req := httptest.NewRequest(http.MethodPut, "/api/admin/categories/404", stringsReader(`{"name":"不存在","code":"missing","description":""}`))
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")
	res := httptest.NewRecorder()
	r.ServeHTTP(res, req)

	if res.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d, body=%s", res.Code, http.StatusNotFound, res.Body.String())
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
