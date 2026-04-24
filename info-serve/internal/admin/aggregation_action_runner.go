package admin

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// AggregationActionRunner 通过 info_aggregation 执行真实采集和质量治理动作。
type AggregationActionRunner struct {
	baseURL string
	client  *http.Client
}

func NewAggregationActionRunner(baseURL string) *AggregationActionRunner {
	return &AggregationActionRunner{
		baseURL: strings.TrimRight(baseURL, "/"),
		client:  &http.Client{Timeout: 60 * time.Second},
	}
}

func (r *AggregationActionRunner) TriggerCrawl(ctx context.Context, channelCode string) (ActionResult, error) {
	path := "/api/crawl/trigger?channel_code=" + url.QueryEscape(channelCode)
	return r.post(ctx, "trigger_crawl", path)
}

func (r *AggregationActionRunner) RebuildEvents(ctx context.Context) (ActionResult, error) {
	return r.post(ctx, "rebuild_events", "/api/admin/rebuild-events")
}

func (r *AggregationActionRunner) RefreshQuality(ctx context.Context) (ActionResult, error) {
	return r.post(ctx, "refresh_quality", "/api/admin/refresh-quality")
}

func (r *AggregationActionRunner) RetryLowQualityDetails(ctx context.Context, limit int) (ActionResult, error) {
	path := fmt.Sprintf("/api/admin/retry-low-quality-details?limit=%d", limit)
	return r.post(ctx, "retry_low_quality_details", path)
}

func (r *AggregationActionRunner) ArchiveLowQuality(ctx context.Context) (ActionResult, error) {
	return r.post(ctx, "archive_low_quality", "/api/admin/archive-low-quality")
}

func (r *AggregationActionRunner) ArchiveDuplicateTitles(ctx context.Context) (ActionResult, error) {
	return r.post(ctx, "archive_duplicate_titles", "/api/admin/archive-duplicate-titles")
}

func (r *AggregationActionRunner) post(ctx context.Context, action string, path string) (ActionResult, error) {
	if r.baseURL == "" {
		return ActionResult{}, fmt.Errorf("采集服务地址未配置")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, r.baseURL+path, bytes.NewReader(nil))
	if err != nil {
		return ActionResult{}, err
	}
	req.Header.Set("Content-Type", "application/json")
	res, err := r.client.Do(req)
	if err != nil {
		return ActionResult{}, err
	}
	defer res.Body.Close()

	var body struct {
		Code    int            `json:"code"`
		Message string         `json:"message"`
		Data    map[string]any `json:"data"`
	}
	if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
		return ActionResult{}, err
	}
	if res.StatusCode < 200 || res.StatusCode >= 300 || body.Code != 0 {
		if body.Message == "" {
			body.Message = "采集服务执行失败"
		}
		return ActionResult{}, errors.New(body.Message)
	}
	if body.Data == nil {
		body.Data = map[string]any{}
	}
	return ActionResult{
		Action:  action,
		Message: body.Message,
		Data:    body.Data,
	}, nil
}
