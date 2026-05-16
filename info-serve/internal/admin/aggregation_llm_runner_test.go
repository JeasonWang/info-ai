package admin

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestAggregationLLMRunnerPostsChatTestToAggregation(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/internal/llm/chat-test" {
			t.Fatalf("path = %q", r.URL.Path)
		}
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("decode payload: %v", err)
		}
		if payload["prompt"] != "ping" {
			t.Fatalf("prompt = %v", payload["prompt"])
		}
		if payload["config_id"] != float64(7) || payload["timeout_seconds"] != float64(240) {
			t.Fatalf("payload = %+v", payload)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"code":    0,
			"message": "success",
			"data": map[string]any{
				"ok":       true,
				"model":    "qwen-local",
				"latency":  float64(1234),
				"provider": "qwen",
			},
		})
	}))
	defer server.Close()

	runner := NewAggregationLLMRunner(server.URL, time.Second)
	result, err := runner.TestLLMChat(context.Background(), LLMChatTestPayload{
		ConfigID:       7,
		Prompt:         "ping",
		TimeoutSeconds: 240,
	})
	if err != nil {
		t.Fatalf("TestLLMChat returned error: %v", err)
	}
	if result["ok"] != true {
		t.Fatalf("result = %+v", result)
	}
}

func TestAggregationLLMRunnerOmitsEmptyConfigID(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("decode payload: %v", err)
		}
		if _, ok := payload["config_id"]; ok {
			t.Fatalf("config_id should be omitted when empty: %+v", payload)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"code":    0,
			"message": "success",
			"data":    map[string]any{"ok": true},
		})
	}))
	defer server.Close()

	runner := NewAggregationLLMRunner(server.URL, time.Second)
	if _, err := runner.TestLLMChat(context.Background(), LLMChatTestPayload{Prompt: "ping"}); err != nil {
		t.Fatalf("TestLLMChat returned error: %v", err)
	}
}

func TestAggregationLLMRunnerReturnsModelFailurePayloadWithoutError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{
			"code":    1,
			"message": "model timeout",
			"data": map[string]any{
				"ok":      false,
				"status":  "failed",
				"message": "model timeout",
			},
		})
	}))
	defer server.Close()

	runner := NewAggregationLLMRunner(server.URL, time.Second)
	result, err := runner.TestLLMChat(context.Background(), LLMChatTestPayload{Prompt: "ping"})
	if err != nil {
		t.Fatalf("TestLLMChat returned error: %v", err)
	}
	if result["ok"] != false || result["status"] != "failed" {
		t.Fatalf("result = %+v", result)
	}
}

func TestAggregationLLMRunnerPostsChatToAggregation(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/internal/llm/chat" {
			t.Fatalf("path = %q", r.URL.Path)
		}
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatalf("decode payload: %v", err)
		}
		if payload["message"] != "你好" {
			t.Fatalf("message = %v", payload["message"])
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"code":    0,
			"message": "success",
			"data": map[string]any{
				"ok":     true,
				"answer": "你好，我是信息达人助手。",
			},
		})
	}))
	defer server.Close()

	runner := NewAggregationLLMRunner(server.URL, time.Second)
	result, err := runner.ChatLLM(context.Background(), LLMChatPayload{
		ConfigID:       7,
		Message:        "你好",
		TimeoutSeconds: 240,
	})
	if err != nil {
		t.Fatalf("ChatLLM returned error: %v", err)
	}
	if result["answer"] != "你好，我是信息达人助手。" {
		t.Fatalf("result = %+v", result)
	}
}
