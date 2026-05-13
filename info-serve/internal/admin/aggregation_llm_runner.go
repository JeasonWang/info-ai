package admin

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"
)

type AggregationLLMRunner struct {
	baseURL string
	client  *http.Client
}

func NewAggregationLLMRunner(baseURL string, timeout time.Duration) *AggregationLLMRunner {
	if timeout <= 0 {
		timeout = 4 * time.Minute
	}
	return &AggregationLLMRunner{
		baseURL: strings.TrimRight(baseURL, "/"),
		client:  &http.Client{Timeout: timeout},
	}
}

func (r *AggregationLLMRunner) TestLLMChat(ctx context.Context, payload LLMChatTestPayload) (map[string]any, error) {
	if r == nil || r.baseURL == "" {
		return nil, errors.New("采集服务 HTTP 地址未配置")
	}
	requestPayload := map[string]any{
		"prompt":          payload.Prompt,
		"timeout_seconds": payload.TimeoutSeconds,
	}
	if payload.ConfigID > 0 {
		requestPayload["config_id"] = payload.ConfigID
	}
	bodyBytes, err := json.Marshal(requestPayload)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, r.baseURL+"/api/internal/llm/chat-test", bytes.NewReader(bodyBytes))
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
		Code    int            `json:"code"`
		Message string         `json:"message"`
		Data    map[string]any `json:"data"`
	}
	if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
		return nil, err
	}
	if res.StatusCode < 200 || res.StatusCode >= 300 {
		if body.Message == "" {
			body.Message = "大模型调用失败"
		}
		return nil, errors.New(body.Message)
	}
	if body.Code != 0 {
		if body.Message == "" {
			body.Message = "大模型调用失败"
		}
		if body.Data == nil {
			body.Data = map[string]any{}
		}
		if _, ok := body.Data["ok"]; !ok {
			body.Data["ok"] = false
		}
		if _, ok := body.Data["message"]; !ok {
			body.Data["message"] = body.Message
		}
		return body.Data, nil
	}
	if body.Data == nil {
		return nil, fmt.Errorf("采集服务返回空结果")
	}
	return body.Data, nil
}

func (r *AggregationLLMRunner) ChatLLM(ctx context.Context, payload LLMChatPayload) (map[string]any, error) {
	if r == nil || r.baseURL == "" {
		return nil, errors.New("采集服务 HTTP 地址未配置")
	}
	requestPayload := map[string]any{
		"message":         payload.Message,
		"timeout_seconds": payload.TimeoutSeconds,
	}
	if payload.ConfigID > 0 {
		requestPayload["config_id"] = payload.ConfigID
	}
	return r.postLLM(ctx, "/api/internal/llm/chat", requestPayload)
}

func (r *AggregationLLMRunner) postLLM(ctx context.Context, path string, requestPayload map[string]any) (map[string]any, error) {
	bodyBytes, err := json.Marshal(requestPayload)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, r.baseURL+path, bytes.NewReader(bodyBytes))
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
		Code    int            `json:"code"`
		Message string         `json:"message"`
		Data    map[string]any `json:"data"`
	}
	if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
		return nil, err
	}
	if res.StatusCode < 200 || res.StatusCode >= 300 {
		if body.Message == "" {
			body.Message = "大模型调用失败"
		}
		return nil, errors.New(body.Message)
	}
	if body.Code != 0 {
		if body.Message == "" {
			body.Message = "大模型调用失败"
		}
		if body.Data == nil {
			body.Data = map[string]any{}
		}
		if _, ok := body.Data["ok"]; !ok {
			body.Data["ok"] = false
		}
		if _, ok := body.Data["message"]; !ok {
			body.Data["message"] = body.Message
		}
		return body.Data, nil
	}
	if body.Data == nil {
		return nil, fmt.Errorf("采集服务返回空结果")
	}
	return body.Data, nil
}

func DurationFromMilliseconds(value string, fallback time.Duration) time.Duration {
	ms, err := strconv.Atoi(value)
	if err != nil || ms <= 0 {
		return fallback
	}
	return time.Duration(ms) * time.Millisecond
}
