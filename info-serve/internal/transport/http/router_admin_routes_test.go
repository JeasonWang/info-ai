package transporthttp_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"info-serve/internal/admin"
	"info-serve/internal/auth"
	transporthttp "info-serve/internal/transport/http"
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

func (s stubAdminStore) ListChannelHealth(ctx context.Context) ([]admin.ChannelHealth, error) {
	return []admin.ChannelHealth{{ChannelCode: "weibo", ChannelName: "微博", HealthScore: 92, HealthLevel: "healthy", SuccessRate: 100}}, nil
}

func (s stubAdminStore) GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error) {
	return map[string]any{"summary": map[string]any{}, "channels": []any{}}, nil
}

func (s stubAdminStore) GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error) {
	return map[string]any{"summary": map[string]any{}, "risk_events": []any{}}, nil
}

func (s stubAdminStore) ListQualitySnapshots(ctx context.Context, limit int) ([]admin.QualitySnapshot, error) {
	return []admin.QualitySnapshot{{CategoryCode: "all", TotalCount: 611, DuplicateTitleCount: 3}}, nil
}

func (s stubAdminStore) ListLowQualityInfos(ctx context.Context, limit int) ([]admin.LowQualityInfo, error) {
	return []admin.LowQualityInfo{{ID: 1, Title: "正文缺失", IssueReason: "正文为空"}}, nil
}

func (s stubAdminStore) GetDetailJobReport(ctx context.Context, filter admin.DetailJobFilter) (admin.DetailJobReport, error) {
	return admin.DetailJobReport{
		Total:         2,
		StatusCounts:  map[string]int{"pending": 1, "failed": 1},
		ChannelCounts: map[string]int{"36kr": 2},
		TopFailureReasons: []admin.DetailJobFailureReason{
			{Reason: "empty_content", Count: 1},
		},
		PendingSamples: []admin.DetailJobSample{{ID: 1, InfoID: 10, Title: "OpenAI 发布新模型", ChannelCode: "36kr", Status: "pending"}},
	}, nil
}

func (s stubAdminStore) GetDetailJob(ctx context.Context, id int64) (admin.DetailJobDetail, error) {
	return admin.DetailJobDetail{ID: id, InfoID: 10, Title: "OpenAI 发布新模型", SourceURL: "https://example.com/a", Content: "完整正文", ChannelCode: "36kr", Status: "failed"}, nil
}

func (s stubAdminStore) RetryDetailJob(ctx context.Context, id int64) (admin.ActionResult, error) {
	return admin.ActionResult{Action: "retry_detail_job", Message: "已重新入队详情补偿任务", Data: map[string]any{"detail_job_id": id}}, nil
}

func (s stubAdminStore) CancelDetailJob(ctx context.Context, id int64) (admin.ActionResult, error) {
	return admin.ActionResult{Action: "cancel_detail_job", Message: "已取消详情补偿任务", Data: map[string]any{"detail_job_id": id}}, nil
}

func (s stubAdminStore) BatchRetryDetailJobs(ctx context.Context, filter admin.DetailJobFilter) (admin.ActionResult, error) {
	return admin.ActionResult{Action: "batch_retry_detail_jobs", Message: "已批量重新入队详情补偿任务", Data: map[string]any{"matched_count": 2}}, nil
}

func (s stubAdminStore) BatchCancelDetailJobs(ctx context.Context, filter admin.DetailJobFilter) (admin.ActionResult, error) {
	return admin.ActionResult{Action: "batch_cancel_detail_jobs", Message: "已批量取消详情补偿任务", Data: map[string]any{"matched_count": 2}}, nil
}

func (s stubAdminStore) ListCrawlTasks(ctx context.Context) ([]admin.CrawlTask, error) {
	return []admin.CrawlTask{{TaskCode: "weibo-hot", TaskName: "微博热点", ChannelID: 1, EffectiveIntervalMinutes: 30, IsActive: 1, Status: "active"}}, nil
}

func (s stubAdminStore) UpdateCrawlTaskConfig(ctx context.Context, channelCode string, payload admin.CrawlTaskConfigPayload) error {
	return nil
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
	return []admin.Channel{{
		ID: 1, Name: "微博", Code: "weibo", CategoryID: 1, CategoryName: "全网", CrawlInterval: 30,
		BaseIntervalMinutes: 20, HotIntervalMinutes: 5, MinIntervalMinutes: 3, MaxIntervalMinutes: 120,
		ManualIntervalEnabled: 1, EffectiveIntervalMinutes: 5, ScheduleVersion: 4, IsActive: 1,
	}}, nil
}

func (s stubAdminStore) CreateChannel(ctx context.Context, payload admin.ChannelPayload) (admin.Channel, error) {
	return admin.Channel{
		ID: 2, Name: payload.Name, Code: payload.Code, CategoryID: payload.CategoryID, CrawlInterval: payload.CrawlInterval,
		BaseIntervalMinutes: payload.BaseIntervalMinutes, HotIntervalMinutes: payload.HotIntervalMinutes,
		MinIntervalMinutes: payload.MinIntervalMinutes, MaxIntervalMinutes: payload.MaxIntervalMinutes,
		ManualIntervalEnabled: payload.ManualIntervalEnabled, EffectiveIntervalMinutes: payload.EffectiveIntervalMinutes,
		ScheduleVersion: 1, IsActive: payload.IsActive,
	}, nil
}

func (s stubAdminStore) UpdateChannel(ctx context.Context, id int64, payload admin.ChannelPayload) (admin.Channel, error) {
	return admin.Channel{
		ID: id, Name: payload.Name, Code: payload.Code, CategoryID: payload.CategoryID, CrawlInterval: payload.CrawlInterval,
		BaseIntervalMinutes: payload.BaseIntervalMinutes, HotIntervalMinutes: payload.HotIntervalMinutes,
		MinIntervalMinutes: payload.MinIntervalMinutes, MaxIntervalMinutes: payload.MaxIntervalMinutes,
		ManualIntervalEnabled: payload.ManualIntervalEnabled, EffectiveIntervalMinutes: payload.EffectiveIntervalMinutes,
		ScheduleVersion: 5, IsActive: payload.IsActive,
	}, nil
}

func (s stubAdminStore) ListLLMModelConfigs(ctx context.Context) (any, error) {
	return []any{map[string]any{"provider_code": "qwen"}}, nil
}

func (s stubAdminStore) CreateLLMModelConfig(ctx context.Context, payload map[string]any) (any, error) {
	payload["id"] = int64(1)
	return payload, nil
}

func (s stubAdminStore) UpdateLLMModelConfig(ctx context.Context, id int64, payload map[string]any) (any, error) {
	payload["id"] = id
	return payload, nil
}

func (s stubAdminStore) GetChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	return map[string]any{"channel_code": channelCode, "cookie_configured": false}, nil
}

func (s stubAdminStore) UpdateChannelCredentials(ctx context.Context, channelCode string, payload admin.ChannelCredentialPayload) (map[string]any, error) {
	return map[string]any{"channel_code": channelCode, "updated_by": payload.UpdatedBy}, nil
}

func (s stubAdminStore) DeleteChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	return map[string]any{"channel_code": channelCode}, nil
}

func (s stubAdminStore) ListAuditLogs(ctx context.Context, limit int) ([]admin.AuditLog, error) {
	return []admin.AuditLog{{ID: 1, AdminUserID: 1, AdminEmail: "admin@example.com", Action: "GET /api/v1/admin/overview", CreatedAt: "2026-04-23 10:00:00"}}, nil
}

func (s stubAdminStore) GetEventAnalysisRuns(ctx context.Context, eventID int64) (admin.EventAnalysisRunsResult, error) {
	return admin.EventAnalysisRunsResult{EventID: eventID, EventTitle: "测试事件", Runs: []admin.AnalysisRun{}}, nil
}

func (s stubAdminStore) GetEventAnalysisSources(ctx context.Context, eventID int64, runID int64) (admin.EventAnalysisSourcesResult, error) {
	return admin.EventAnalysisSourcesResult{
		EventID:    eventID,
		EventTitle: "测试事件",
		Run:        admin.AnalysisRun{RunID: runID, Status: "succeeded"},
		Sources:    []admin.AnalysisSource{},
	}, nil
}

func (s notFoundAdminStore) UpdateCategory(ctx context.Context, id int64, payload admin.CategoryPayload) (admin.Category, error) {
	return admin.Category{}, admin.ErrNotFound
}

func TestAdminOverviewRequiresLogin(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{Admin: admin.NewService(stubAdminStore{})})
	req := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	res := httptest.NewRecorder()

	r.ServeHTTP(res, req)

	if res.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusUnauthorized)
	}
}

func TestAdminOverviewRequiresAdminRole(t *testing.T) {
	r := transporthttp.NewRouter(transporthttp.Services{Admin: admin.NewService(stubAdminStore{})})
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

	r := transporthttp.NewRouter(transporthttp.Services{Auth: service, Admin: admin.NewService(stubAdminStore{})})
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
	r := transporthttp.NewRouter(transporthttp.Services{Auth: service, Admin: admin.NewService(stubAdminStore{})})
	token := loginOnly(t, r, "admin@example.com", "Admin123456")

	cases := []struct {
		path string
		key  string
	}{
		{path: "/api/admin/crawl-runs", key: "channel_code"},
		{path: "/api/admin/channel-health", key: "health_level"},
		{path: "/api/admin/quality-snapshots", key: "category_code"},
		{path: "/api/admin/low-quality-infos", key: "issue_reason"},
		{path: "/api/admin/crawl-tasks", key: "task_code"},
		{path: "/api/admin/audit-logs", key: "action"},
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

func TestAdminDetailJobsRouteReturnsReport(t *testing.T) {
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
	r := transporthttp.NewRouter(transporthttp.Services{Auth: service, Admin: admin.NewService(stubAdminStore{})})
	token := loginOnly(t, r, "admin@example.com", "Admin123456")

	req := httptest.NewRequest(http.MethodGet, "/api/admin/detail-jobs?limit=5&channel_code=36kr&failure_reason=empty_content", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	res := httptest.NewRecorder()
	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d, body=%s", res.Code, http.StatusOK, res.Body.String())
	}
	var body struct {
		Data admin.DetailJobReport `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Data.Total != 2 || body.Data.StatusCounts["pending"] != 1 {
		t.Fatalf("detail job report = %+v", body.Data)
	}
	if len(body.Data.PendingSamples) != 1 || body.Data.PendingSamples[0].Title == "" {
		t.Fatalf("missing pending samples: %+v", body.Data.PendingSamples)
	}
}

func TestAdminDetailJobRouteReturnsDetail(t *testing.T) {
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
	r := transporthttp.NewRouter(transporthttp.Services{Auth: service, Admin: admin.NewService(stubAdminStore{})})
	token := loginOnly(t, r, "admin@example.com", "Admin123456")

	req := httptest.NewRequest(http.MethodGet, "/api/v1/admin/detail-jobs/11", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	res := httptest.NewRecorder()
	r.ServeHTTP(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d, body=%s", res.Code, http.StatusOK, res.Body.String())
	}
	var body struct {
		Data admin.DetailJobDetail `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid json: %v", err)
	}
	if body.Data.SourceURL == "" || body.Data.Content == "" {
		t.Fatalf("missing detail content: %+v", body.Data)
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
	r := transporthttp.NewRouter(transporthttp.Services{Auth: service, Admin: admin.NewService(stubAdminStore{})})
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
		{method: http.MethodPost, path: "/api/admin/channels", body: `{"name":"新浪体育","code":"sina_sports","base_url":"https://sports.sina.com.cn/","category_id":1,"crawl_interval":30,"base_interval_minutes":30,"hot_interval_minutes":5,"min_interval_minutes":3,"max_interval_minutes":120,"manual_interval_enabled":1,"effective_interval_minutes":5,"is_active":1}`, key: "code", status: http.StatusCreated},
		{method: http.MethodPut, path: "/api/admin/channels/1", body: `{"name":"微博","code":"weibo","base_url":"https://weibo.com/","category_id":1,"crawl_interval":45,"base_interval_minutes":45,"hot_interval_minutes":5,"min_interval_minutes":3,"max_interval_minutes":180,"manual_interval_enabled":1,"effective_interval_minutes":5,"is_active":1}`, key: "code", status: http.StatusOK},
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
		raw, _ := json.Marshal(body.Data)
		if strings.Contains(item.path, "/channels") && !strings.Contains(string(raw), "effective_interval_minutes") {
			t.Fatalf("%s %s missing schedule fields: %s", item.method, item.path, string(raw))
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
	r := transporthttp.NewRouter(transporthttp.Services{Auth: service, Admin: admin.NewService(notFoundAdminStore{})})
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

func TestAdminActionRoutesReturnResultForAdmin(t *testing.T) {
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
	r := transporthttp.NewRouter(transporthttp.Services{
		Auth:  service,
		Admin: admin.NewServiceWithActions(stubAdminStore{}, admin.NewMemoryActionRunner()),
	})
	token := loginOnly(t, r, "admin@example.com", "Admin123456")

	cases := []struct {
		path   string
		action string
	}{
		{path: "/api/v1/admin/crawl-tasks/weibo/trigger", action: "trigger_crawl"},
		{path: "/api/v1/admin/rebuild-events", action: "rebuild_events"},
		{path: "/api/v1/admin/refresh-quality", action: "refresh_quality"},
		{path: "/api/v1/admin/retry-low-quality-details?limit=5", action: "retry_low_quality_details"},
		{path: "/api/v1/admin/prioritize-weak-source-governance?limit=5", action: "prioritize_weak_source_governance"},
		{path: "/api/v1/admin/detail-jobs/retry?channel_code=36kr&failure_reason=empty_content&limit=20", action: "batch_retry_detail_jobs"},
		{path: "/api/v1/admin/detail-jobs/cancel?channel_code=36kr&failure_reason=empty_content&limit=20", action: "batch_cancel_detail_jobs"},
		{path: "/api/v1/admin/detail-jobs/11/retry", action: "retry_detail_job"},
		{path: "/api/v1/admin/detail-jobs/11/cancel", action: "cancel_detail_job"},
		{path: "/api/v1/admin/archive-low-quality", action: "archive_low_quality"},
		{path: "/api/v1/admin/archive-duplicate-titles", action: "archive_duplicate_titles"},
	}

	for _, item := range cases {
		req := httptest.NewRequest(http.MethodPost, item.path, nil)
		req.Header.Set("Authorization", "Bearer "+token)
		res := httptest.NewRecorder()
		r.ServeHTTP(res, req)
		if res.Code != http.StatusOK {
			t.Fatalf("%s status = %d, want %d, body=%s", item.path, res.Code, http.StatusOK, res.Body.String())
		}
		var body struct {
			Data admin.ActionResult `json:"data"`
		}
		if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
			t.Fatalf("invalid json for %s: %v", item.path, err)
		}
		if body.Data.Action != item.action {
			t.Fatalf("%s action = %q, want %q", item.path, body.Data.Action, item.action)
		}
	}

	req := httptest.NewRequest(http.MethodPost, "/api/v1/admin/llm-model-configs/chat", stringsReader(`{"message":"你好","timeout_seconds":240}`))
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")
	res := httptest.NewRecorder()
	r.ServeHTTP(res, req)
	if res.Code != http.StatusOK {
		t.Fatalf("llm chat status = %d, want %d, body=%s", res.Code, http.StatusOK, res.Body.String())
	}
	var body struct {
		Data map[string]any `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid llm chat json: %v", err)
	}
	if body.Data["user_text"] != "你好" {
		t.Fatalf("llm chat body = %+v", body.Data)
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
