package admin

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

// RedisActionRunner 通过 Redis Streams 向 info_aggregation 提交采集和分析命令。
type RedisActionRunner struct {
	client       *redis.Client
	stream       string
	resultPrefix string
	waitTimeout  time.Duration
}

type RedisActionRunnerConfig struct {
	Addr         string
	Password     string
	DB           int
	Stream       string
	ResultPrefix string
	WaitTimeout  time.Duration
}

func NewRedisActionRunner(cfg RedisActionRunnerConfig) *RedisActionRunner {
	if cfg.Addr == "" {
		cfg.Addr = "127.0.0.1:6379"
	}
	if cfg.Stream == "" {
		cfg.Stream = "info_ai:aggregation:commands"
	}
	if cfg.ResultPrefix == "" {
		cfg.ResultPrefix = "info_ai:aggregation:results:"
	}
	if cfg.WaitTimeout <= 0 {
		cfg.WaitTimeout = 5 * time.Second
	}
	return &RedisActionRunner{
		client: redis.NewClient(&redis.Options{
			Addr:     cfg.Addr,
			Password: cfg.Password,
			DB:       cfg.DB,
		}),
		stream:       cfg.Stream,
		resultPrefix: cfg.ResultPrefix,
		waitTimeout:  cfg.WaitTimeout,
	}
}

func (r *RedisActionRunner) Close() error {
	if r == nil || r.client == nil {
		return nil
	}
	return r.client.Close()
}

func (r *RedisActionRunner) TriggerCrawl(ctx context.Context, channelCode string) (ActionResult, error) {
	return r.submitAsync(ctx, "trigger_crawl", map[string]any{"channel_code": channelCode}, "采集任务已提交")
}

func (r *RedisActionRunner) EnqueueEventAnalysisDetailJobs(ctx context.Context, limit int) (ActionResult, error) {
	return r.submitAsync(ctx, "enqueue_event_analysis_detail_jobs", map[string]any{"limit": limit}, "事件分析弱来源已提交处理")
}

func (r *RedisActionRunner) PrioritizeWeakSourceGovernance(ctx context.Context, limit int) (ActionResult, error) {
	return r.submitAsync(ctx, "prioritize_source_quality_governance", map[string]any{"limit": limit}, "来源质量风险已提交优先治理")
}

func (r *RedisActionRunner) RebuildStaleEventAnalysis(ctx context.Context, limit int) (ActionResult, error) {
	return r.submitAsync(ctx, "rebuild_stale_event_analysis", map[string]any{"limit": limit}, "过期事件分析已提交处理")
}

func (r *RedisActionRunner) RebuildEvents(ctx context.Context) (ActionResult, error) {
	return r.submitAsync(ctx, "rebuild_events", nil, "事件重建任务已提交")
}

func (r *RedisActionRunner) RefreshQuality(ctx context.Context) (ActionResult, error) {
	return r.submitAsync(ctx, "refresh_quality", nil, "数据质量刷新任务已提交")
}

func (r *RedisActionRunner) RetryLowQualityDetails(ctx context.Context, limit int) (ActionResult, error) {
	return r.submitAsync(ctx, "retry_low_quality_details", map[string]any{"limit": limit}, "低完整详情重抓任务已提交")
}

func (r *RedisActionRunner) ArchiveLowQuality(ctx context.Context) (ActionResult, error) {
	return r.submitAsync(ctx, "archive_low_quality", nil, "低质量内容归档任务已提交")
}

func (r *RedisActionRunner) ArchiveDuplicateTitles(ctx context.Context) (ActionResult, error) {
	return r.submitAsync(ctx, "archive_duplicate_titles", nil, "重复标题归档任务已提交")
}

func (r *RedisActionRunner) TestChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	result, err := r.submitAndWait(ctx, "test_channel_credentials", map[string]any{"channel_code": channelCode}, r.waitTimeout)
	if err != nil {
		return nil, err
	}
	return result.Data, nil
}

func (r *RedisActionRunner) InvalidateCredentials(ctx context.Context, channelCode string) (ActionResult, error) {
	return r.submitAsync(ctx, "invalidate_credentials", map[string]any{"channel_code": channelCode}, "采集凭证缓存刷新命令已提交")
}

func (r *RedisActionRunner) TestLLMChat(ctx context.Context, payload LLMChatTestPayload) (map[string]any, error) {
	return nil, errors.New("大模型测试需要通过采集服务 HTTP 接口执行")
}

func (r *RedisActionRunner) ChatLLM(ctx context.Context, payload LLMChatPayload) (map[string]any, error) {
	return nil, errors.New("大模型聊天需要通过采集服务 HTTP 接口执行")
}

func (r *RedisActionRunner) submitAsync(ctx context.Context, action string, payload map[string]any, message string) (ActionResult, error) {
	requestID, err := r.enqueue(ctx, action, payload)
	if err != nil {
		return ActionResult{}, err
	}
	return ActionResult{
		Action:  action,
		Message: message,
		Data: map[string]any{
			"request_id": requestID,
			"status":     "queued",
		},
	}, nil
}

func (r *RedisActionRunner) submitAndWait(ctx context.Context, action string, payload map[string]any, timeout time.Duration) (aggregationResult, error) {
	requestID, err := r.enqueue(ctx, action, payload)
	if err != nil {
		return aggregationResult{}, err
	}
	started := time.Now()
	ticker := time.NewTicker(200 * time.Millisecond)
	defer ticker.Stop()
	deadline := time.NewTimer(timeout)
	defer deadline.Stop()
	key := r.resultPrefix + requestID
	for {
		select {
		case <-ctx.Done():
			return aggregationResult{}, ctx.Err()
		case <-deadline.C:
			log.Printf("aggregation command wait timeout action=%s request_id=%s timeout=%s", action, requestID, timeout)
			return aggregationResult{
				RequestID: requestID,
				Action:    action,
				Status:    "queued",
				Message:   "命令已提交，采集服务仍在处理中",
				Data:      map[string]any{"request_id": requestID, "status": "queued"},
			}, nil
		case <-ticker.C:
			raw, err := r.client.Get(ctx, key).Result()
			if errors.Is(err, redis.Nil) {
				continue
			}
			if err != nil {
				return aggregationResult{}, err
			}
			var result aggregationResult
			if err := json.Unmarshal([]byte(raw), &result); err != nil {
				return aggregationResult{}, err
			}
			log.Printf("aggregation command result action=%s request_id=%s status=%s elapsed_ms=%d", action, requestID, result.Status, time.Since(started).Milliseconds())
			if result.Status == "failed" {
				if result.Message == "" {
					result.Message = "采集服务执行失败"
				}
				return result, errors.New(result.Message)
			}
			return result, nil
		}
	}
}

func (r *RedisActionRunner) enqueue(ctx context.Context, action string, payload map[string]any) (string, error) {
	if r == nil || r.client == nil {
		return "", errors.New("Redis action runner 未初始化")
	}
	requestID := newRequestID()
	if payload == nil {
		payload = map[string]any{}
	}
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	fields := map[string]any{
		"request_id": requestID,
		"action":     action,
		"payload":    string(payloadBytes),
		"created_at": time.Now().Format(time.RFC3339),
	}
	started := time.Now()
	messageID, err := r.client.XAdd(ctx, &redis.XAddArgs{
		Stream: r.stream,
		Values: fields,
	}).Result()
	if err != nil {
		log.Printf("aggregation command enqueue failed action=%s request_id=%s error=%v", action, requestID, err)
		return "", err
	}
	log.Printf("aggregation command enqueued action=%s request_id=%s stream=%s message_id=%s elapsed_ms=%d", action, requestID, r.stream, messageID, time.Since(started).Milliseconds())
	return requestID, nil
}

type aggregationResult struct {
	RequestID string         `json:"request_id"`
	Action    string         `json:"action"`
	Status    string         `json:"status"`
	Message   string         `json:"message"`
	Data      map[string]any `json:"data"`
}

func newRequestID() string {
	var buf [16]byte
	if _, err := rand.Read(buf[:]); err != nil {
		return fmt.Sprintf("%d", time.Now().UnixNano())
	}
	return hex.EncodeToString(buf[:])
}

func RedisDBFromString(value string) int {
	db, err := strconv.Atoi(value)
	if err != nil || db < 0 {
		return 0
	}
	return db
}

func RedisWaitTimeoutFromString(value string) time.Duration {
	ms, err := strconv.Atoi(value)
	if err != nil || ms <= 0 {
		return 5 * time.Second
	}
	return time.Duration(ms) * time.Millisecond
}
