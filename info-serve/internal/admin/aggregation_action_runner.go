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

func (r *AggregationActionRunner) GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error) {
	if sampleLimit < 1 {
		sampleLimit = 5
	}
	if sampleLimit > 20 {
		sampleLimit = 20
	}
	path := fmt.Sprintf("/api/admin/channel-quality-report?sample_limit=%d", sampleLimit)
	return r.get(ctx, path)
}

func (r *AggregationActionRunner) GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	path := fmt.Sprintf("/api/admin/event-analysis-quality-report?limit=%d", limit)
	return r.get(ctx, path)
}

func (r *AggregationActionRunner) ListLLMModelConfigs(ctx context.Context) (any, error) {
	return r.getAny(ctx, "/api/admin/llm-model-configs")
}

func (r *AggregationActionRunner) CreateLLMModelConfig(ctx context.Context, payload map[string]any) (any, error) {
	return r.sendAny(ctx, http.MethodPost, "/api/admin/llm-model-configs", payload)
}

func (r *AggregationActionRunner) UpdateLLMModelConfig(ctx context.Context, id int64, payload map[string]any) (any, error) {
	return r.sendAny(ctx, http.MethodPut, fmt.Sprintf("/api/admin/llm-model-configs/%d", id), payload)
}

func (r *AggregationActionRunner) EnqueueEventAnalysisDetailJobs(ctx context.Context, limit int) (ActionResult, error) {
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	path := fmt.Sprintf("/api/admin/event-analysis-detail-jobs?limit=%d", limit)
	return r.post(ctx, "event_analysis_detail_jobs", path)
}

func (r *AggregationActionRunner) RebuildStaleEventAnalysis(ctx context.Context, limit int) (ActionResult, error) {
	if limit < 1 {
		limit = 200
	}
	if limit > 1000 {
		limit = 1000
	}
	path := fmt.Sprintf("/api/admin/rebuild-stale-event-analysis?limit=%d", limit)
	return r.post(ctx, "rebuild_stale_event_analysis", path)
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

func (r *AggregationActionRunner) GetChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	path := "/api/admin/channels/" + url.QueryEscape(channelCode) + "/credentials"
	return r.get(ctx, path)
}

func (r *AggregationActionRunner) UpdateChannelCredentials(ctx context.Context, channelCode string, payload ChannelCredentialPayload) (map[string]any, error) {
	path := "/api/admin/channels/" + url.QueryEscape(channelCode) + "/credentials"
	data, err := r.sendAny(ctx, http.MethodPut, path, map[string]any{
		"cookies":           payload.Cookies,
		"extra_credentials": payload.ExtraCredentials,
		"updated_by":        payload.UpdatedBy,
	})
	if err != nil {
		return nil, err
	}
	if result, ok := data.(map[string]any); ok {
		return result, nil
	}
	return nil, errors.New("返回格式异常")
}

func (r *AggregationActionRunner) TestChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	path := "/api/admin/channels/" + url.QueryEscape(channelCode) + "/credentials/test"
	data, err := r.sendAny(ctx, http.MethodPost, path, nil)
	if err != nil {
		return nil, err
	}
	if result, ok := data.(map[string]any); ok {
		return result, nil
	}
	return nil, errors.New("返回格式异常")
}

func (r *AggregationActionRunner) DeleteChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	path := "/api/admin/channels/" + url.QueryEscape(channelCode) + "/credentials"
	data, err := r.sendAny(ctx, http.MethodDelete, path, nil)
	if err != nil {
		return nil, err
	}
	if result, ok := data.(map[string]any); ok {
		return result, nil
	}
	return nil, errors.New("返回格式异常")
}

func (r *AggregationActionRunner) TestLLMChat(ctx context.Context, payload LLMChatTestPayload) (map[string]any, error) {
	return NewAggregationLLMRunner(r.baseURL, 4*time.Minute).TestLLMChat(ctx, payload)
}

func (r *AggregationActionRunner) ChatLLM(ctx context.Context, payload LLMChatPayload) (map[string]any, error) {
	return NewAggregationLLMRunner(r.baseURL, 4*time.Minute).ChatLLM(ctx, payload)
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

func (r *AggregationActionRunner) get(ctx context.Context, path string) (map[string]any, error) {
	data, err := r.getAny(ctx, path)
	if err != nil {
		return nil, err
	}
	if mapped, ok := data.(map[string]any); ok {
		return mapped, nil
	}
	return nil, errors.New("采集服务返回格式异常")
}

func (r *AggregationActionRunner) getAny(ctx context.Context, path string) (any, error) {
	if r.baseURL == "" {
		return nil, fmt.Errorf("采集服务地址未配置")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, r.baseURL+path, nil)
	if err != nil {
		return nil, err
	}
	res, err := r.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()

	var body struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
		Data    any    `json:"data"`
	}
	if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
		return nil, err
	}
	if res.StatusCode < 200 || res.StatusCode >= 300 || body.Code != 0 {
		if body.Message == "" {
			body.Message = "采集服务查询失败"
		}
		return nil, errors.New(body.Message)
	}
	return body.Data, nil
}

func (r *AggregationActionRunner) sendAny(ctx context.Context, method string, path string, payload map[string]any) (any, error) {
	if r.baseURL == "" {
		return nil, fmt.Errorf("采集服务地址未配置")
	}
	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, method, r.baseURL+path, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	res, err := r.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	var body struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
		Data    any    `json:"data"`
	}
	if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
		return nil, err
	}
	if res.StatusCode < 200 || res.StatusCode >= 300 || body.Code != 0 {
		if body.Message == "" {
			body.Message = "采集服务执行失败"
		}
		return nil, errors.New(body.Message)
	}
	return body.Data, nil
}
