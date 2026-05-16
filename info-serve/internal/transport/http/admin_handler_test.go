package transporthttp

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"info-serve/internal/admin"
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
		Quality:      admin.QualityOverview{DuplicateTitleCount: 3},
		RecentRuns:   []admin.CrawlRunSummary{{ChannelCode: "weibo", Status: "success"}},
	}, nil
}

func (s stubAdminStore) ListCrawlRuns(ctx context.Context, limit int) ([]admin.CrawlRunSummary, error) {
	return []admin.CrawlRunSummary{{ChannelCode: "weibo", Status: "success", SavedCount: 10}}, nil
}

func (s stubAdminStore) ListChannelHealth(ctx context.Context) ([]admin.ChannelHealth, error) {
	return []admin.ChannelHealth{{ChannelCode: "weibo", ChannelName: "微博", HealthScore: 92, HealthLevel: "healthy"}}, nil
}

func (s stubAdminStore) GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error) {
	return map[string]any{"summary": map[string]any{}, "channels": []any{}}, nil
}

func (s stubAdminStore) GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error) {
	return map[string]any{"summary": map[string]any{}, "risk_events": []any{}}, nil
}

func (s stubAdminStore) ListQualitySnapshots(ctx context.Context, limit int) ([]admin.QualitySnapshot, error) {
	return []admin.QualitySnapshot{{CategoryCode: "all", TotalCount: 611}}, nil
}

func (s stubAdminStore) ListLowQualityInfos(ctx context.Context, limit int) ([]admin.LowQualityInfo, error) {
	return []admin.LowQualityInfo{{ID: 1, Title: "正文缺失", IssueReason: "正文为空"}}, nil
}

func (s stubAdminStore) GetDetailJobReport(ctx context.Context, filter admin.DetailJobFilter) (admin.DetailJobReport, error) {
	return admin.DetailJobReport{Total: 1, StatusCounts: map[string]int{"pending": 1}}, nil
}

func (s stubAdminStore) GetDetailJob(ctx context.Context, id int64) (admin.DetailJobDetail, error) {
	return admin.DetailJobDetail{ID: id, Title: "详情补偿任务"}, nil
}

func (s stubAdminStore) RetryDetailJob(ctx context.Context, id int64) (admin.ActionResult, error) {
	return admin.ActionResult{Action: "retry_detail_job", Data: map[string]any{"detail_job_id": id}}, nil
}

func (s stubAdminStore) CancelDetailJob(ctx context.Context, id int64) (admin.ActionResult, error) {
	return admin.ActionResult{Action: "cancel_detail_job", Data: map[string]any{"detail_job_id": id}}, nil
}

func (s stubAdminStore) BatchRetryDetailJobs(ctx context.Context, filter admin.DetailJobFilter) (admin.ActionResult, error) {
	return admin.ActionResult{Action: "batch_retry_detail_jobs", Data: map[string]any{"matched_count": 0}}, nil
}

func (s stubAdminStore) BatchCancelDetailJobs(ctx context.Context, filter admin.DetailJobFilter) (admin.ActionResult, error) {
	return admin.ActionResult{Action: "batch_cancel_detail_jobs", Data: map[string]any{"matched_count": 0}}, nil
}

func (s stubAdminStore) ListCrawlTasks(ctx context.Context) ([]admin.CrawlTask, error) {
	return []admin.CrawlTask{{TaskCode: "weibo-hot", TaskName: "微博热点", ChannelID: 1, EffectiveIntervalMinutes: 30, IsActive: 1, Status: "active"}}, nil
}

func (s stubAdminStore) UpdateCrawlTaskConfig(ctx context.Context, channelCode string, payload admin.CrawlTaskConfigPayload) error {
	return nil
}

func (s stubAdminStore) ListCategories(ctx context.Context) ([]admin.Category, error) {
	return []admin.Category{{ID: 1, Name: "科技", Code: "tech"}}, nil
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
	return []admin.AuditLog{{ID: 1, AdminEmail: "admin@example.com", Action: "GET /api/v1/admin/overview"}}, nil
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

func TestAdminHandlerReturnsOverviewAndConfigurations(t *testing.T) {
	handler := NewAdminHandler(admin.NewService(stubAdminStore{}))

	overviewReq := httptest.NewRequest(http.MethodGet, "/api/admin/overview", nil)
	overviewRes := httptest.NewRecorder()
	handler.Overview(overviewRes, overviewReq)
	if overviewRes.Code != http.StatusOK {
		t.Fatalf("overview status = %d, want %d", overviewRes.Code, http.StatusOK)
	}
	var overviewBody struct {
		Data admin.Overview `json:"data"`
	}
	if err := json.Unmarshal(overviewRes.Body.Bytes(), &overviewBody); err != nil {
		t.Fatalf("invalid overview json: %v", err)
	}
	if overviewBody.Data.EventCount != 199 {
		t.Fatalf("overview = %+v", overviewBody.Data)
	}

	createReq := httptest.NewRequest(http.MethodPost, "/api/admin/categories", strings.NewReader(`{"name":"体育","code":"sports","description":"体育热点"}`))
	createReq.Header.Set("Content-Type", "application/json")
	createRes := httptest.NewRecorder()
	handler.CreateCategory(createRes, createReq)
	if createRes.Code != http.StatusCreated {
		t.Fatalf("create category status = %d, want %d", createRes.Code, http.StatusCreated)
	}
}

func TestAdminHandlerChatsWithLLM(t *testing.T) {
	handler := NewAdminHandler(admin.NewServiceWithActions(stubAdminStore{}, admin.NewMemoryActionRunner()))
	req := httptest.NewRequest(http.MethodPost, "/api/admin/llm-model-configs/chat", strings.NewReader(`{"message":"你好","timeout_seconds":240}`))
	req.Header.Set("Content-Type", "application/json")
	res := httptest.NewRecorder()

	handler.ChatLLM(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("chat llm status = %d, want %d, body=%s", res.Code, http.StatusOK, res.Body.String())
	}
	var body struct {
		Data map[string]any `json:"data"`
	}
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("invalid chat json: %v", err)
	}
	if body.Data["user_text"] != "你好" {
		t.Fatalf("chat data = %+v", body.Data)
	}
}

func TestAdminHandlerReturnsNotFoundForMissingConfiguration(t *testing.T) {
	handler := NewAdminHandler(admin.NewService(notFoundAdminStore{}))
	req := httptest.NewRequest(http.MethodPut, "/api/admin/categories/404", strings.NewReader(`{"name":"不存在","code":"missing","description":""}`))
	req.SetPathValue("id", "404")
	res := httptest.NewRecorder()

	handler.UpdateCategory(res, req)

	if res.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d, body=%s", res.Code, http.StatusNotFound, res.Body.String())
	}
}

func TestAdminHealthReturnsProtectedStatus(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/api/admin/health", nil)
	res := httptest.NewRecorder()

	AdminHealth(res, req)

	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.Code, http.StatusOK)
	}
}
