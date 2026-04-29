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
	return []admin.CrawlTask{{TaskCode: "weibo-hot", TaskName: "微博热点", Status: "active"}}, nil
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

func (s stubAdminStore) ListAuditLogs(ctx context.Context, limit int) ([]admin.AuditLog, error) {
	return []admin.AuditLog{{ID: 1, AdminEmail: "admin@example.com", Action: "GET /api/v1/admin/overview"}}, nil
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
