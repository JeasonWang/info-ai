package repository

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"sort"
	"strconv"
	"strings"

	"info-serve/internal/admin"
)

func (s *MySQLStore) GetOverview(ctx context.Context) (admin.Overview, error) {
	var overview admin.Overview
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM channel`).Scan(&overview.ChannelCount); err != nil {
		return admin.Overview{}, err
	}
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM event`).Scan(&overview.EventCount); err != nil {
		return admin.Overview{}, err
	}
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM info WHERE is_deleted = 0`).Scan(&overview.InfoCount); err != nil {
		return admin.Overview{}, err
	}
	quality, err := s.qualityOverview(ctx)
	if err != nil {
		return admin.Overview{}, err
	}
	recentRuns, err := s.recentCrawlRuns(ctx)
	if err != nil {
		return admin.Overview{}, err
	}
	overview.Quality = quality
	overview.RecentRuns = recentRuns
	return overview, nil
}

func (s *MySQLStore) qualityOverview(ctx context.Context) (admin.QualityOverview, error) {
	var quality admin.QualityOverview
	err := s.db.QueryRowContext(
		ctx,
		`SELECT
  COALESCE(SUM(duplicate_count), 0) AS duplicate_title_count
FROM (
  SELECT GREATEST(COUNT(*) - 1, 0) AS duplicate_count
  FROM info
  WHERE is_deleted = 0
  GROUP BY title
  HAVING COUNT(*) > 1
) AS duplicated`,
	).Scan(&quality.DuplicateTitleCount)
	if err != nil {
		return admin.QualityOverview{}, err
	}
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM info WHERE is_deleted = 0 AND (content IS NULL OR TRIM(content) = '')`).Scan(&quality.EmptyContentCount); err != nil {
		return admin.QualityOverview{}, err
	}
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM info WHERE is_deleted = 0 AND detail_score < 60`).Scan(&quality.LowDetailScoreCount); err != nil {
		return admin.QualityOverview{}, err
	}
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM info WHERE is_deleted = 0 AND TRIM(core_entity) = ''`).Scan(&quality.MissingEntityCount); err != nil {
		return admin.QualityOverview{}, err
	}
	return quality, nil
}

func (s *MySQLStore) recentCrawlRuns(ctx context.Context) ([]admin.CrawlRunSummary, error) {
	return s.ListCrawlRuns(ctx, 8)
}

func (s *MySQLStore) ListCrawlRuns(ctx context.Context, limit int) ([]admin.CrawlRunSummary, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT channel_code, status, raw_count, cleaned_count, saved_count,
       detail_success_count, detail_failed_count,
       COALESCE(DATE_FORMAT(started_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(finished_at, '%Y-%m-%d %H:%i:%s'), '')
FROM crawl_run_log
ORDER BY started_at DESC
LIMIT ?`,
		limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []admin.CrawlRunSummary{}
	for rows.Next() {
		var item admin.CrawlRunSummary
		var finishedAt sql.NullString
		if err := rows.Scan(
			&item.ChannelCode,
			&item.Status,
			&item.RawCount,
			&item.CleanedCount,
			&item.SavedCount,
			&item.DetailSuccessCount,
			&item.DetailFailedCount,
			&item.StartedAt,
			&finishedAt,
		); err != nil {
			return nil, err
		}
		if finishedAt.Valid {
			item.FinishedAt = finishedAt.String
		}
		result = append(result, item)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return result, nil
}

func (s *MySQLStore) ListChannelHealth(ctx context.Context) ([]admin.ChannelHealth, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT ch.code, ch.name, c.name, COALESCE(t.status, 'inactive'),
		       COALESCE(log_stats.recent_run_count, 0),
		       COALESCE(log_stats.success_count, 0),
		       COALESCE(log_stats.failure_count, 0),
		       COALESCE(log_stats.detail_success_count, 0),
		       COALESCE(log_stats.detail_failed_count, 0),
		       COALESCE(log_stats.last_run_at, ''),
		       COALESCE(log_stats.last_issue, ''),
		       COALESCE(info_stats.latest_info_at, ''),
		       COALESCE(event_stats.latest_event_at, ''),
		       COALESCE(info_stats.info_count, 0),
		       COALESCE(event_stats.active_event_count, 0),
		       COALESCE(info_stats.average_content_length, 0),
		       COALESCE(info_stats.incomplete_info_count, 0),
		       COALESCE(info_stats.top_failure_reasons, '')
FROM channel AS ch
JOIN category AS c ON c.id = ch.category_id
LEFT JOIN crawl_task AS t ON t.channel_id = ch.id
LEFT JOIN (
  SELECT channel_code,
         COUNT(id) AS recent_run_count,
         SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
         SUM(CASE WHEN status IN ('failed', 'partial') THEN 1 ELSE 0 END) AS failure_count,
         SUM(detail_success_count) AS detail_success_count,
         SUM(detail_failed_count) AS detail_failed_count,
         DATE_FORMAT(MAX(started_at), '%Y-%m-%d %H:%i:%s') AS last_run_at,
         SUBSTRING_INDEX(GROUP_CONCAT(CASE WHEN status <> 'success' THEN error_message END ORDER BY started_at DESC SEPARATOR '||'), '||', 1) AS last_issue
  FROM crawl_run_log
  GROUP BY channel_code
) AS log_stats ON log_stats.channel_code = ch.code
LEFT JOIN (
  SELECT channel_id,
         DATE_FORMAT(MAX(created_at), '%Y-%m-%d %H:%i:%s') AS latest_info_at,
         COUNT(id) AS info_count,
         ROUND(AVG(detail_content_length)) AS average_content_length,
         COUNT(CASE WHEN detail_fetch_status <> 'complete' OR detail_score < 80 OR detail_content_length < 120 THEN 1 END) AS incomplete_info_count,
         GROUP_CONCAT(NULLIF(detail_fetch_error, '') ORDER BY updated_at DESC SEPARATOR '||') AS top_failure_reasons
  FROM info
  WHERE is_deleted = 0
  GROUP BY channel_id
) AS info_stats ON info_stats.channel_id = ch.id
LEFT JOIN (
  SELECT i.channel_id,
         DATE_FORMAT(MAX(e.last_updated_at), '%Y-%m-%d %H:%i:%s') AS latest_event_at,
         COUNT(DISTINCT e.id) AS active_event_count
  FROM event AS e
  JOIN event_item_link AS link ON link.event_id = e.id
  JOIN info AS i ON i.id = link.item_id
  WHERE e.status = 'active' AND i.is_deleted = 0
  GROUP BY i.channel_id
) AS event_stats ON event_stats.channel_id = ch.id
ORDER BY ch.id ASC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	items := []admin.ChannelHealth{}
	for rows.Next() {
		var item admin.ChannelHealth
		var successCount int
		var detailSuccessCount int
		var detailFailedCount int
		var rawFailureReasons string
		if err := rows.Scan(
			&item.ChannelCode,
			&item.ChannelName,
			&item.CategoryName,
			&item.Status,
			&item.RecentRunCount,
			&successCount,
			&item.FailureCount,
			&detailSuccessCount,
			&detailFailedCount,
			&item.LastRunAt,
			&item.LastIssue,
			&item.LatestInfoAt,
			&item.LatestEventAt,
			&item.InfoCount,
			&item.ActiveEventCount,
			&item.AverageContentLength,
			&item.IncompleteInfoCount,
			&rawFailureReasons,
		); err != nil {
			return nil, err
		}
		item.SuccessRate = percentage(successCount, item.RecentRunCount)
		item.DetailCompleteRate = percentage(detailSuccessCount, detailSuccessCount+detailFailedCount)
		item.HealthScore = calculateHealthScore(item.SuccessRate, item.DetailCompleteRate, item.RecentRunCount, item.Status)
		item.HealthLevel = healthLevel(item.HealthScore)
		item.TopFailureReasons = splitFailureReasons(rawFailureReasons)
		items = append(items, item)
	}
	return items, rows.Err()
}

func (s *MySQLStore) GetChannelQualityReport(ctx context.Context, sampleLimit int) (map[string]any, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT id, code, name FROM channel ORDER BY id ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	channels := []map[string]any{}
	summary := channelQualitySummary{}
	for rows.Next() {
		var channelID int64
		var channelCode string
		var channelName string
		if err := rows.Scan(&channelID, &channelCode, &channelName); err != nil {
			return nil, err
		}
		row, err := s.channelQualityRow(ctx, channelID, channelCode, channelName, sampleLimit)
		if err != nil {
			return nil, err
		}
		summary.add(row)
		channels = append(channels, row)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return map[string]any{
		"summary":  summary.toMap(channels),
		"channels": channels,
	}, nil
}

func (s *MySQLStore) GetEventAnalysisQualityReport(ctx context.Context, limit int) (map[string]any, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT e.id, e.title, e.one_line_summary, e.source_count,
       latest.id, latest.mode, latest.provider, latest.model_name, latest.status,
       latest.quality_score, latest.confidence, latest.fallback_used, latest.failure_reason,
       COALESCE(DATE_FORMAT(latest.finished_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(weak.weak_source_count, 0)
FROM event AS e
LEFT JOIN (
  SELECT run.*
  FROM event_analysis_run AS run
  JOIN (
    SELECT event_id, MAX(id) AS latest_id
    FROM event_analysis_run
    GROUP BY event_id
  ) AS latest_run ON latest_run.latest_id = run.id
) AS latest ON latest.event_id = e.id
LEFT JOIN (
  SELECT link.event_id, COUNT(*) AS weak_source_count
  FROM event_item_link AS link
  JOIN info AS i ON i.id = link.item_id
  WHERE i.is_deleted = 0
    AND LOWER(COALESCE(i.detail_strategy, '')) <> 'seed'
    AND (
      i.detail_fetch_status IN ('pending', 'list_only', 'failed')
      OR i.detail_score < 60
      OR COALESCE(i.detail_content_length, CHAR_LENGTH(COALESCE(i.content, ''))) < 120
    )
  GROUP BY link.event_id
) AS weak ON weak.event_id = e.id
WHERE e.status = 'active'
ORDER BY e.last_updated_at DESC, e.id DESC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	summary := eventAnalysisQualitySummary{}
	riskEvents := []map[string]any{}
	for rows.Next() {
		row, reasons, err := scanEventAnalysisQualityRow(rows)
		if err != nil {
			return nil, err
		}
		summary.add(row, reasons)
		if len(reasons) > 0 {
			riskEvents = append(riskEvents, row)
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	sortRiskEvents(riskEvents)
	if limit > 0 && len(riskEvents) > limit {
		riskEvents = riskEvents[:limit]
	}
	return map[string]any{
		"summary":     summary.toMap(len(riskEvents)),
		"risk_events": riskEvents,
	}, nil
}

func splitFailureReasons(raw string) []string {
	reasons := []string{}
	seen := map[string]bool{}
	for _, part := range strings.Split(raw, "||") {
		reason := strings.TrimSpace(part)
		if reason == "" || seen[reason] {
			continue
		}
		reasons = append(reasons, reason)
		seen[reason] = true
		if len(reasons) >= 3 {
			break
		}
	}
	return reasons
}

func percentage(part int, total int) int {
	if total <= 0 {
		return 0
	}
	return part * 100 / total
}

func calculateHealthScore(successRate int, detailCompleteRate int, runCount int, status string) int {
	score := successRate*7/10 + detailCompleteRate*3/10
	if runCount == 0 {
		score = 40
	}
	if status != "active" {
		score -= 20
	}
	if score < 0 {
		return 0
	}
	if score > 100 {
		return 100
	}
	return score
}

func healthLevel(score int) string {
	switch {
	case score >= 85:
		return "healthy"
	case score >= 60:
		return "warning"
	default:
		return "risk"
	}
}

func (s *MySQLStore) channelQualityRow(ctx context.Context, channelID int64, channelCode string, channelName string, sampleLimit int) (map[string]any, error) {
	var totalCount int
	var realCount int
	var seedCount int
	var completeCount int
	var highValuePartialCount int
	var needsAttentionCount int
	var avgDetailScore float64
	var avgDetailLength float64
	err := s.db.QueryRowContext(
		ctx,
		`SELECT COUNT(*),
       COALESCE(SUM(CASE WHEN LOWER(COALESCE(detail_strategy, '')) <> 'seed' THEN 1 ELSE 0 END), 0),
       COALESCE(SUM(CASE WHEN LOWER(COALESCE(detail_strategy, '')) = 'seed' THEN 1 ELSE 0 END), 0),
       COALESCE(SUM(CASE WHEN LOWER(COALESCE(detail_strategy, '')) <> 'seed' AND detail_fetch_status = 'complete' AND detail_score >= 60 THEN 1 ELSE 0 END), 0),
       COALESCE(SUM(CASE WHEN LOWER(COALESCE(detail_strategy, '')) <> 'seed' AND detail_fetch_status = 'partial' AND detail_score >= 60 THEN 1 ELSE 0 END), 0),
       COALESCE(SUM(CASE WHEN LOWER(COALESCE(detail_strategy, '')) <> 'seed' AND (
         detail_fetch_status IN ('pending', 'list_only', 'failed')
         OR detail_score < 60
         OR COALESCE(detail_content_length, CHAR_LENGTH(COALESCE(content, ''))) < 120
       ) THEN 1 ELSE 0 END), 0),
       COALESCE(AVG(CASE WHEN LOWER(COALESCE(detail_strategy, '')) <> 'seed' THEN detail_score END), 0),
       COALESCE(AVG(CASE WHEN LOWER(COALESCE(detail_strategy, '')) <> 'seed' THEN COALESCE(detail_content_length, CHAR_LENGTH(COALESCE(content, ''))) END), 0)
FROM info
WHERE channel_id = ? AND is_deleted = 0`,
		channelID,
	).Scan(
		&totalCount,
		&realCount,
		&seedCount,
		&completeCount,
		&highValuePartialCount,
		&needsAttentionCount,
		&avgDetailScore,
		&avgDetailLength,
	)
	if err != nil {
		return nil, err
	}
	usableCount := completeCount + highValuePartialCount
	row := map[string]any{
		"channel_id":                channelID,
		"channel_code":              channelCode,
		"channel_name":              channelName,
		"total_count":               totalCount,
		"real_count":                realCount,
		"seed_count":                seedCount,
		"complete_count":            completeCount,
		"complete_ratio":            percentFloat(completeCount, realCount),
		"high_value_partial_count":  highValuePartialCount,
		"usable_count":              usableCount,
		"usable_ratio":              percentFloat(usableCount, realCount),
		"needs_attention_count":     needsAttentionCount,
		"needs_attention_ratio":     percentFloat(needsAttentionCount, realCount),
		"avg_detail_score":          roundFloat(avgDetailScore, 1),
		"avg_detail_content_length": roundFloat(avgDetailLength, 1),
	}
	topFailureReasons, err := s.channelTopFailureReasons(ctx, channelID)
	if err != nil {
		return nil, err
	}
	topStrategies, err := s.channelTopStrategies(ctx, channelID)
	if err != nil {
		return nil, err
	}
	weakSamples, err := s.channelWeakSamples(ctx, channelID, sampleLimit)
	if err != nil {
		return nil, err
	}
	credentialHealth, err := s.channelCredentialHealth(ctx, channelCode)
	if err != nil {
		return nil, err
	}
	row["top_failure_reasons"] = topFailureReasons
	row["top_detail_strategies"] = topStrategies
	row["credential_health"] = credentialHealth
	row["weak_samples"] = weakSamples
	row["quality_rank_score"] = channelQualityRankScore(row)
	row["governance_advice"] = channelGovernanceAdvice(row)
	return row, nil
}

func (s *MySQLStore) channelTopFailureReasons(ctx context.Context, channelID int64) ([]map[string]any, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT COALESCE(NULLIF(detail_fetch_error, ''), detail_fetch_status, 'unknown') AS reason, COUNT(*) AS count
FROM info
WHERE channel_id = ? AND is_deleted = 0
  AND LOWER(COALESCE(detail_strategy, '')) <> 'seed'
  AND (
    detail_fetch_status IN ('pending', 'list_only', 'failed')
    OR detail_score < 60
    OR COALESCE(detail_content_length, CHAR_LENGTH(COALESCE(content, ''))) < 120
  )
GROUP BY reason
ORDER BY count DESC, reason ASC
LIMIT 5`,
		channelID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []map[string]any{}
	for rows.Next() {
		var reason string
		var count int
		if err := rows.Scan(&reason, &count); err != nil {
			return nil, err
		}
		result = append(result, map[string]any{"reason": reason, "count": count})
	}
	return result, rows.Err()
}

func (s *MySQLStore) channelTopStrategies(ctx context.Context, channelID int64) ([]map[string]any, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT COALESCE(NULLIF(detail_strategy, ''), 'unknown') AS strategy, COUNT(*) AS count
FROM info
WHERE channel_id = ? AND is_deleted = 0 AND LOWER(COALESCE(detail_strategy, '')) <> 'seed'
GROUP BY strategy
ORDER BY count DESC, strategy ASC
LIMIT 5`,
		channelID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []map[string]any{}
	for rows.Next() {
		var strategy string
		var count int
		if err := rows.Scan(&strategy, &count); err != nil {
			return nil, err
		}
		result = append(result, map[string]any{"strategy": strategy, "count": count})
	}
	return result, rows.Err()
}

func (s *MySQLStore) channelWeakSamples(ctx context.Context, channelID int64, sampleLimit int) ([]map[string]any, error) {
	if sampleLimit < 1 {
		sampleLimit = 5
	}
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT id, title, source_url, detail_fetch_status, detail_strategy, detail_score,
       COALESCE(detail_content_length, CHAR_LENGTH(COALESCE(content, ''))),
       detail_fetch_error
FROM info
WHERE channel_id = ? AND is_deleted = 0
  AND LOWER(COALESCE(detail_strategy, '')) <> 'seed'
  AND (
    detail_fetch_status IN ('pending', 'list_only', 'failed')
    OR detail_score < 60
    OR COALESCE(detail_content_length, CHAR_LENGTH(COALESCE(content, ''))) < 120
  )
ORDER BY detail_score ASC, COALESCE(detail_content_length, CHAR_LENGTH(COALESCE(content, ''))) ASC, id DESC
LIMIT ?`,
		channelID,
		sampleLimit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []map[string]any{}
	for rows.Next() {
		var id int64
		var title string
		var sourceURL string
		var status string
		var strategy string
		var score int
		var length int
		var fetchError string
		if err := rows.Scan(&id, &title, &sourceURL, &status, &strategy, &score, &length, &fetchError); err != nil {
			return nil, err
		}
		result = append(result, map[string]any{
			"id":                    id,
			"title":                 title,
			"source_url":            sourceURL,
			"detail_fetch_status":   status,
			"detail_strategy":       strategy,
			"detail_score":          score,
			"detail_content_length": length,
			"detail_fetch_error":    fetchError,
			"quality_level":         qualityLevel(score, length, status),
			"risk_reasons":          qualityRiskReasons(score, length, status),
			"recommended_action":    "建议重抓详情或检查渠道解析规则。",
			"quality_summary":       qualitySummary(score, length, status),
		})
	}
	return result, rows.Err()
}

func (s *MySQLStore) channelCredentialHealth(ctx context.Context, channelCode string) (map[string]any, error) {
	info, err := s.GetChannelCredentials(ctx, channelCode)
	if err != nil {
		return nil, err
	}
	required := credentialRequired(channelCode)
	configured, _ := info["cookie_configured"].(bool)
	health := "not_required"
	missing := []string{}
	if required {
		if configured {
			health = "ready"
		} else {
			health = "missing_required"
			missing = []string{strings.ToUpper(strings.ReplaceAll(channelCode, "-", "_")) + "_COOKIE"}
		}
	}
	return map[string]any{
		"channel_code":      channelCode,
		"health":            health,
		"missing_required":  missing,
		"credentials":       []any{},
		"cookie_status":     info["cookie_status"],
		"cookie_configured": configured,
	}, nil
}

func credentialRequired(channelCode string) bool {
	switch channelCode {
	case "weibo", "zhihu", "xiaohongshu":
		return true
	default:
		return false
	}
}

type channelQualitySummary struct {
	realCount             int
	completeCount         int
	highValuePartialCount int
	usableCount           int
	needsAttentionCount   int
}

func (s *channelQualitySummary) add(row map[string]any) {
	s.realCount += intFromAny(row["real_count"])
	s.completeCount += intFromAny(row["complete_count"])
	s.highValuePartialCount += intFromAny(row["high_value_partial_count"])
	s.usableCount += intFromAny(row["usable_count"])
	s.needsAttentionCount += intFromAny(row["needs_attention_count"])
}

func (s channelQualitySummary) toMap(channels []map[string]any) map[string]any {
	weakChannels := []map[string]any{}
	sorted := append([]map[string]any(nil), channels...)
	sort.SliceStable(sorted, func(i, j int) bool {
		return floatFromAny(sorted[i]["usable_ratio"]) < floatFromAny(sorted[j]["usable_ratio"])
	})
	for _, row := range sorted {
		if intFromAny(row["real_count"]) == 0 {
			continue
		}
		weakChannels = append(weakChannels, map[string]any{
			"channel_code":          row["channel_code"],
			"channel_name":          row["channel_name"],
			"usable_ratio":          row["usable_ratio"],
			"needs_attention_ratio": row["needs_attention_ratio"],
		})
		if len(weakChannels) >= 5 {
			break
		}
	}
	return map[string]any{
		"real_count":               s.realCount,
		"complete_count":           s.completeCount,
		"high_value_partial_count": s.highValuePartialCount,
		"usable_count":             s.usableCount,
		"needs_attention_count":    s.needsAttentionCount,
		"complete_ratio":           percentFloat(s.completeCount, s.realCount),
		"usable_ratio":             percentFloat(s.usableCount, s.realCount),
		"needs_attention_ratio":    percentFloat(s.needsAttentionCount, s.realCount),
		"weak_channels":            weakChannels,
	}
}

func channelQualityRankScore(row map[string]any) float64 {
	score := 100 - floatFromAny(row["usable_ratio"])
	score += floatFromAny(row["needs_attention_ratio"]) * 0.8
	if health, ok := row["credential_health"].(map[string]any); ok && health["health"] == "missing_required" {
		score += 25
	}
	if floatFromAny(row["avg_detail_content_length"]) < 120 && intFromAny(row["real_count"]) > 0 {
		score += 12
	}
	return roundFloat(score, 1)
}

func channelGovernanceAdvice(row map[string]any) []string {
	advice := []string{}
	if health, ok := row["credential_health"].(map[string]any); ok && health["health"] == "missing_required" {
		advice = append(advice, "配置渠道 Cookie 后执行重抓低完整详情。")
	}
	if floatFromAny(row["usable_ratio"]) < 45 {
		advice = append(advice, "优先治理该渠道详情页解析和二跳补偿策略。")
	}
	if floatFromAny(row["avg_detail_content_length"]) < 120 && intFromAny(row["real_count"]) > 0 {
		advice = append(advice, "平均正文偏短，建议抽样对比原站详情页并提升正文抽取规则。")
	}
	if floatFromAny(row["needs_attention_ratio"]) >= 40 {
		advice = append(advice, "待治理比例偏高，建议先批量重抓低完整详情。")
	}
	if len(advice) == 0 {
		advice = append(advice, "当前质量可用，继续保持定时采集和质量监控。")
	}
	return advice
}

func scanEventAnalysisQualityRow(rows *sql.Rows) (map[string]any, []string, error) {
	var eventID int64
	var title string
	var oneLineSummary string
	var sourceCount int
	var runID sql.NullInt64
	var mode sql.NullString
	var provider sql.NullString
	var modelName sql.NullString
	var status sql.NullString
	var qualityScore sql.NullFloat64
	var confidence sql.NullFloat64
	var fallbackUsed sql.NullInt64
	var failureReason sql.NullString
	var lastAnalyzedAt string
	var weakSourceCount int
	if err := rows.Scan(
		&eventID,
		&title,
		&oneLineSummary,
		&sourceCount,
		&runID,
		&mode,
		&provider,
		&modelName,
		&status,
		&qualityScore,
		&confidence,
		&fallbackUsed,
		&failureReason,
		&lastAnalyzedAt,
		&weakSourceCount,
	); err != nil {
		return nil, nil, err
	}
	reasons := eventAnalysisIssueReasons(runID.Valid, status.String, failureReason.String, qualityScore.Float64, confidence.Float64, fallbackUsed.Int64 == 1, weakSourceCount, oneLineSummary)
	riskScore := eventAnalysisRiskScore(runID.Valid, qualityScore.Float64, confidence.Float64, fallbackUsed.Int64 == 1, status.String, weakSourceCount, reasons)
	row := map[string]any{
		"event_id":          eventID,
		"title":             title,
		"one_line_summary":  oneLineSummary,
		"source_count":      sourceCount,
		"weak_source_count": weakSourceCount,
		"issue_reasons":     reasons,
		"governance_advice": eventAnalysisGovernanceAdvice(reasons, weakSourceCount),
		"risk_score":        riskScore,
		"run_id":            nil,
		"mode":              "",
		"provider":          "",
		"model_name":        "",
		"status":            "missing",
		"quality_score":     0.0,
		"confidence":        0.0,
		"fallback_used":     false,
		"failure_reason":    "",
		"last_analyzed_at":  "",
	}
	if runID.Valid {
		row["run_id"] = runID.Int64
		row["mode"] = mode.String
		row["provider"] = provider.String
		row["model_name"] = modelName.String
		row["status"] = status.String
		row["quality_score"] = roundFloat(qualityScore.Float64, 2)
		row["confidence"] = roundFloat(confidence.Float64, 4)
		row["fallback_used"] = fallbackUsed.Int64 == 1
		row["failure_reason"] = failureReason.String
		row["last_analyzed_at"] = lastAnalyzedAt
	}
	return row, reasons, nil
}

func eventAnalysisIssueReasons(hasRun bool, status string, failureReason string, qualityScore float64, confidence float64, fallbackUsed bool, weakSourceCount int, oneLineSummary string) []string {
	if !hasRun {
		return []string{"missing_analysis"}
	}
	reasons := []string{}
	if (status == "failed" || status == "fallback") && failureReason != "" {
		reasons = append(reasons, "llm_or_analysis_fallback")
	}
	if confidence < 0.6 {
		reasons = append(reasons, "low_confidence")
	}
	if qualityScore < 60 {
		reasons = append(reasons, "low_quality_score")
	}
	if fallbackUsed {
		reasons = append(reasons, "fallback_used")
	}
	if weakSourceCount > 0 {
		reasons = append(reasons, "weak_sources")
	}
	if strings.TrimSpace(oneLineSummary) == "" {
		reasons = append(reasons, "empty_one_line_summary")
	}
	return reasons
}

func eventAnalysisGovernanceAdvice(reasons []string, weakSourceCount int) []string {
	advice := []string{}
	for _, reason := range reasons {
		switch reason {
		case "missing_analysis":
			advice = append(advice, "先执行事件重建，补齐事件分析运行记录。")
		case "weak_sources":
			advice = append(advice, "该事件有 "+strconv.Itoa(weakSourceCount)+" 条弱来源，建议优先执行详情补偿后重新分析。")
		case "low_confidence", "low_quality_score":
			advice = append(advice, "分析置信度偏低，建议增加可用来源或启用大模型增强。")
		case "fallback_used", "llm_or_analysis_fallback":
			advice = append(advice, "大模型增强发生回退，检查模型服务地址、超时和模型输出格式。")
		case "empty_one_line_summary":
			advice = append(advice, "一句话摘要为空，建议重新构建事件分析结果。")
		}
	}
	if len(advice) == 0 {
		return []string{"当前事件分析质量稳定，继续观察即可。"}
	}
	return uniqueStrings(advice)
}

func eventAnalysisRiskScore(hasRun bool, qualityScore float64, confidence float64, fallbackUsed bool, status string, weakSourceCount int, reasons []string) float64 {
	if !hasRun {
		return 100
	}
	score := maxFloat(0, 60-qualityScore)
	score += maxFloat(0, 0.6-confidence) * 100
	score += minFloat(30, float64(weakSourceCount)*12)
	if fallbackUsed {
		score += 15
	}
	if status == "failed" {
		score += 20
	}
	for _, reason := range reasons {
		if reason == "empty_one_line_summary" {
			score += 10
			break
		}
	}
	return roundFloat(score, 2)
}

type eventAnalysisQualitySummary struct {
	activeEventCount      int
	analyzedCount         int
	missingAnalysisCount  int
	lowConfidenceCount    int
	fallbackCount         int
	weakSourceEventCount  int
	totalConfidence       float64
	totalQualityScore     float64
	totalRiskEventsBefore int
}

func (s *eventAnalysisQualitySummary) add(row map[string]any, reasons []string) {
	s.activeEventCount++
	if row["run_id"] == nil {
		s.missingAnalysisCount++
	} else {
		s.analyzedCount++
		s.totalConfidence += floatFromAny(row["confidence"])
		s.totalQualityScore += floatFromAny(row["quality_score"])
		if floatFromAny(row["confidence"]) < 0.6 {
			s.lowConfidenceCount++
		}
		if fallback, _ := row["fallback_used"].(bool); fallback || row["status"] == "fallback" {
			s.fallbackCount++
		}
	}
	if intFromAny(row["weak_source_count"]) > 0 {
		s.weakSourceEventCount++
	}
	if len(reasons) > 0 {
		s.totalRiskEventsBefore++
	}
}

func (s eventAnalysisQualitySummary) toMap(returnedRiskEventCount int) map[string]any {
	return map[string]any{
		"active_event_count":        s.activeEventCount,
		"analyzed_count":            s.analyzedCount,
		"missing_analysis_count":    s.missingAnalysisCount,
		"low_confidence_count":      s.lowConfidenceCount,
		"fallback_count":            s.fallbackCount,
		"weak_source_event_count":   s.weakSourceEventCount,
		"avg_confidence":            averageFloat(s.totalConfidence, s.analyzedCount, 4),
		"avg_quality_score":         averageFloat(s.totalQualityScore, s.analyzedCount, 2),
		"risk_event_count":          s.totalRiskEventsBefore,
		"returned_risk_event_count": returnedRiskEventCount,
	}
}

func sortRiskEvents(items []map[string]any) {
	sort.SliceStable(items, func(i, j int) bool {
		leftScore := floatFromAny(items[i]["risk_score"])
		rightScore := floatFromAny(items[j]["risk_score"])
		if leftScore == rightScore {
			return intFromAny(items[i]["event_id"]) < intFromAny(items[j]["event_id"])
		}
		return leftScore > rightScore
	})
}

func percentFloat(part int, total int) float64 {
	if total <= 0 {
		return 0
	}
	return roundFloat(float64(part)*100/float64(total), 1)
}

func averageFloat(total float64, count int, places int) float64 {
	if count <= 0 {
		return 0
	}
	return roundFloat(total/float64(count), places)
}

func roundFloat(value float64, places int) float64 {
	if places <= 0 {
		if value >= 0 {
			return float64(int(value + 0.5))
		}
		return float64(int(value - 0.5))
	}
	multiplier := 1.0
	for i := 0; i < places; i++ {
		multiplier *= 10
	}
	if value >= 0 {
		return float64(int(value*multiplier+0.5)) / multiplier
	}
	return float64(int(value*multiplier-0.5)) / multiplier
}

func intFromAny(value any) int {
	switch typed := value.(type) {
	case int:
		return typed
	case int64:
		return int(typed)
	case float64:
		return int(typed)
	default:
		return 0
	}
}

func floatFromAny(value any) float64 {
	switch typed := value.(type) {
	case float64:
		return typed
	case int:
		return float64(typed)
	case int64:
		return float64(typed)
	default:
		return 0
	}
}

func minFloat(left float64, right float64) float64 {
	if left < right {
		return left
	}
	return right
}

func maxFloat(left float64, right float64) float64 {
	if left > right {
		return left
	}
	return right
}

func uniqueStrings(values []string) []string {
	seen := map[string]bool{}
	result := []string{}
	for _, value := range values {
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		result = append(result, value)
	}
	return result
}

func qualityLevel(score int, length int, status string) string {
	if status == "complete" && score >= 80 && length >= 300 {
		return "complete"
	}
	if score >= 60 {
		return "partial"
	}
	return "weak"
}

func qualityRiskReasons(score int, length int, status string) []string {
	reasons := []string{}
	if status == "pending" || status == "list_only" || status == "failed" {
		reasons = append(reasons, status)
	}
	if score < 60 {
		reasons = append(reasons, "low_detail_score")
	}
	if length < 120 {
		reasons = append(reasons, "short_content")
	}
	return reasons
}

func qualitySummary(score int, length int, status string) string {
	if status == "complete" && score >= 80 {
		return "详情完整，可稳定展示。"
	}
	if score >= 60 {
		return "详情可用但仍建议继续补强。"
	}
	if length < 120 {
		return "正文偏短，建议重抓详情。"
	}
	return "详情质量偏低，建议检查解析规则。"
}

func (s *MySQLStore) ListQualitySnapshots(ctx context.Context, limit int) ([]admin.QualitySnapshot, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT category_code, total_count, duplicate_title_count, empty_content_count,
       low_detail_score_count, missing_entity_count,
       COALESCE(CAST(JSON_UNQUOTE(JSON_EXTRACT(snapshot_payload, '$.info.seed_detail_count')) AS UNSIGNED), 0),
       COALESCE(CAST(JSON_UNQUOTE(JSON_EXTRACT(snapshot_payload, '$.info.real_detail_total')) AS UNSIGNED), 0),
       COALESCE(CAST(JSON_UNQUOTE(JSON_EXTRACT(snapshot_payload, '$.info.real_complete_detail_count')) AS UNSIGNED), 0),
       COALESCE(CAST(JSON_UNQUOTE(JSON_EXTRACT(snapshot_payload, '$.info.real_complete_detail_ratio')) AS DECIMAL(6,2)), 0),
       COALESCE(DATE_FORMAT(snapshot_at, '%Y-%m-%d %H:%i:%s'), '')
FROM data_quality_snapshot
ORDER BY snapshot_at DESC
LIMIT ?`,
		limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []admin.QualitySnapshot{}
	for rows.Next() {
		var item admin.QualitySnapshot
		if err := rows.Scan(
			&item.CategoryCode,
			&item.TotalCount,
			&item.DuplicateTitleCount,
			&item.EmptyContentCount,
			&item.LowDetailScoreCount,
			&item.MissingEntityCount,
			&item.SeedDetailCount,
			&item.RealDetailTotal,
			&item.RealCompleteDetailCount,
			&item.RealCompleteDetailRatio,
			&item.SnapshotAt,
		); err != nil {
			return nil, err
		}
		result = append(result, item)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return result, nil
}

func (s *MySQLStore) ListLowQualityInfos(ctx context.Context, limit int) ([]admin.LowQualityInfo, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT i.id, i.title, ch.name, c.name, i.detail_fetch_status,
		       i.detail_score, i.detail_content_length,
		       CASE
		         WHEN COALESCE(i.content, '') = '' THEN '正文为空'
		         WHEN i.detail_score < 60 THEN '详情评分偏低'
		         WHEN i.tech_entities = '' THEN '关键实体缺失'
		         ELSE '需要复核'
		       END AS issue_reason,
		       DATE_FORMAT(i.updated_at, '%Y-%m-%d %H:%i:%s')
FROM info AS i
JOIN channel AS ch ON ch.id = i.channel_id
JOIN category AS c ON c.id = i.category_id
WHERE i.is_deleted = 0
  AND (COALESCE(i.content, '') = '' OR i.detail_score < 60 OR i.tech_entities = '')
ORDER BY i.detail_score ASC, i.detail_content_length ASC, i.updated_at DESC
LIMIT ?`,
		limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []admin.LowQualityInfo{}
	for rows.Next() {
		var item admin.LowQualityInfo
		if err := rows.Scan(
			&item.ID,
			&item.Title,
			&item.ChannelName,
			&item.CategoryName,
			&item.DetailFetchStatus,
			&item.DetailScore,
			&item.DetailContentLength,
			&item.IssueReason,
			&item.UpdatedAt,
		); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (s *MySQLStore) GetDetailJobReport(ctx context.Context, filter admin.DetailJobFilter) (admin.DetailJobReport, error) {
	report := admin.DetailJobReport{
		StatusCounts:  map[string]int{},
		ChannelCounts: map[string]int{},
	}
	whereClause, args := detailJobWhereClause(filter, "WHERE")
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM detail_job `+whereClause, args...).Scan(&report.Total); err != nil {
		return admin.DetailJobReport{}, err
	}
	statusCounts, err := s.countByString(ctx, `SELECT status, COUNT(*) FROM detail_job `+whereClause+` GROUP BY status`, args...)
	if err != nil {
		return admin.DetailJobReport{}, err
	}
	report.StatusCounts = statusCounts
	channelWhereClause, channelArgs := detailJobWhereClause(filter, "WHERE")
	if channelWhereClause == "" {
		channelWhereClause = "WHERE channel_code <> ''"
	} else {
		channelWhereClause += " AND channel_code <> ''"
	}
	channelCounts, err := s.countByString(ctx, `SELECT channel_code, COUNT(*) FROM detail_job `+channelWhereClause+` GROUP BY channel_code`, channelArgs...)
	if err != nil {
		return admin.DetailJobReport{}, err
	}
	report.ChannelCounts = channelCounts
	reasons, err := s.listDetailJobFailureReasons(ctx, filter)
	if err != nil {
		return admin.DetailJobReport{}, err
	}
	report.TopFailureReasons = reasons
	pendingSamples, err := s.listDetailJobSamples(ctx, "pending", filter)
	if err != nil {
		return admin.DetailJobReport{}, err
	}
	report.PendingSamples = pendingSamples
	failedSamples, err := s.listDetailJobSamples(ctx, "failed", filter)
	if err != nil {
		return admin.DetailJobReport{}, err
	}
	report.FailedSamples = failedSamples
	return report, nil
}

func (s *MySQLStore) BatchRetryDetailJobs(ctx context.Context, filter admin.DetailJobFilter) (admin.ActionResult, error) {
	whereClause, args := detailJobWhereClause(filter, "WHERE")
	if whereClause == "" {
		return admin.ActionResult{}, admin.ErrInvalidInput
	}
	args = append(args, filter.SampleLimit)
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE detail_job
SET status = 'pending',
    next_run_at = NOW(),
    last_failure_reason = '',
    updated_at = NOW()
`+whereClause+` AND status IN ('pending', 'running', 'failed')
ORDER BY priority DESC, updated_at DESC, id DESC
LIMIT ?`,
		args...,
	)
	if err != nil {
		return admin.ActionResult{}, err
	}
	changed, err := result.RowsAffected()
	if err != nil {
		return admin.ActionResult{}, err
	}
	return admin.ActionResult{
		Action:  "batch_retry_detail_jobs",
		Message: "已批量重新入队详情补偿任务",
		Data: map[string]any{
			"matched_count":  changed,
			"channel_code":   filter.ChannelCode,
			"failure_reason": filter.FailureReason,
		},
	}, nil
}

func (s *MySQLStore) BatchCancelDetailJobs(ctx context.Context, filter admin.DetailJobFilter) (admin.ActionResult, error) {
	whereClause, args := detailJobWhereClause(filter, "WHERE")
	if whereClause == "" {
		return admin.ActionResult{}, admin.ErrInvalidInput
	}
	args = append(args, filter.SampleLimit)
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE detail_job
SET status = 'cancelled',
    updated_at = NOW()
`+whereClause+` AND status IN ('pending', 'running', 'failed')
ORDER BY priority DESC, updated_at DESC, id DESC
LIMIT ?`,
		args...,
	)
	if err != nil {
		return admin.ActionResult{}, err
	}
	changed, err := result.RowsAffected()
	if err != nil {
		return admin.ActionResult{}, err
	}
	return admin.ActionResult{
		Action:  "batch_cancel_detail_jobs",
		Message: "已批量取消详情补偿任务",
		Data: map[string]any{
			"matched_count":  changed,
			"channel_code":   filter.ChannelCode,
			"failure_reason": filter.FailureReason,
		},
	}, nil
}

func (s *MySQLStore) GetDetailJob(ctx context.Context, id int64) (admin.DetailJobDetail, error) {
	var item admin.DetailJobDetail
	err := s.db.QueryRowContext(
		ctx,
		`SELECT job.id, job.info_id, i.title, i.source_url, i.content,
       job.channel_code, job.status, job.priority, job.attempt_count, job.max_attempts,
       job.last_failure_reason, COALESCE(DATE_FORMAT(job.next_run_at, '%Y-%m-%d %H:%i:%s'), ''),
       i.detail_score, i.detail_fetch_status, i.detail_strategy,
       COALESCE(DATE_FORMAT(job.created_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(job.updated_at, '%Y-%m-%d %H:%i:%s'), '')
FROM detail_job AS job
JOIN info AS i ON i.id = job.info_id
WHERE job.id = ?`,
		id,
	).Scan(
		&item.ID,
		&item.InfoID,
		&item.Title,
		&item.SourceURL,
		&item.Content,
		&item.ChannelCode,
		&item.Status,
		&item.Priority,
		&item.AttemptCount,
		&item.MaxAttempts,
		&item.LastFailureReason,
		&item.NextRunAt,
		&item.DetailScore,
		&item.DetailFetchStatus,
		&item.DetailStrategy,
		&item.CreatedAt,
		&item.UpdatedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return admin.DetailJobDetail{}, admin.ErrNotFound
	}
	if err != nil {
		return admin.DetailJobDetail{}, err
	}
	return item, nil
}

func (s *MySQLStore) RetryDetailJob(ctx context.Context, id int64) (admin.ActionResult, error) {
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE detail_job
SET status = 'pending',
    next_run_at = NOW(),
    last_failure_reason = '',
    updated_at = NOW()
WHERE id = ? AND status IN ('pending', 'running', 'failed')`,
		id,
	)
	if err != nil {
		return admin.ActionResult{}, err
	}
	if changed, err := result.RowsAffected(); err != nil {
		return admin.ActionResult{}, err
	} else if changed == 0 {
		return admin.ActionResult{}, admin.ErrNotFound
	}
	return admin.ActionResult{
		Action:  "retry_detail_job",
		Message: "已重新入队详情补偿任务",
		Data:    map[string]any{"detail_job_id": id},
	}, nil
}

func (s *MySQLStore) CancelDetailJob(ctx context.Context, id int64) (admin.ActionResult, error) {
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE detail_job
SET status = 'cancelled',
    updated_at = NOW()
WHERE id = ? AND status IN ('pending', 'running', 'failed')`,
		id,
	)
	if err != nil {
		return admin.ActionResult{}, err
	}
	if changed, err := result.RowsAffected(); err != nil {
		return admin.ActionResult{}, err
	} else if changed == 0 {
		return admin.ActionResult{}, admin.ErrNotFound
	}
	return admin.ActionResult{
		Action:  "cancel_detail_job",
		Message: "已取消详情补偿任务",
		Data:    map[string]any{"detail_job_id": id},
	}, nil
}

func (s *MySQLStore) countByString(ctx context.Context, query string, args ...any) (map[string]int, error) {
	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := map[string]int{}
	for rows.Next() {
		var key string
		var count int
		if err := rows.Scan(&key, &count); err != nil {
			return nil, err
		}
		result[key] = count
	}
	return result, rows.Err()
}

func (s *MySQLStore) listDetailJobFailureReasons(ctx context.Context, filter admin.DetailJobFilter) ([]admin.DetailJobFailureReason, error) {
	whereClause, args := detailJobWhereClause(filter, "WHERE")
	if whereClause == "" {
		whereClause = "WHERE last_failure_reason <> ''"
	} else {
		whereClause += " AND last_failure_reason <> ''"
	}
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT last_failure_reason, COUNT(*)
FROM detail_job
`+whereClause+`
GROUP BY last_failure_reason
ORDER BY COUNT(*) DESC, last_failure_reason ASC
LIMIT 10`,
		args...,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []admin.DetailJobFailureReason{}
	for rows.Next() {
		var item admin.DetailJobFailureReason
		if err := rows.Scan(&item.Reason, &item.Count); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (s *MySQLStore) listDetailJobSamples(ctx context.Context, status string, filter admin.DetailJobFilter) ([]admin.DetailJobSample, error) {
	whereClause, args := detailJobWhereClause(filter, "WHERE")
	if whereClause == "" {
		whereClause = "WHERE job.status = ?"
	} else {
		whereClause += " AND job.status = ?"
	}
	args = append(args, status, filter.SampleLimit)
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT job.id, job.info_id, i.title, job.channel_code, job.status,
       job.priority, job.attempt_count, job.max_attempts, job.last_failure_reason,
       COALESCE(DATE_FORMAT(job.next_run_at, '%Y-%m-%d %H:%i:%s'), ''),
       i.detail_score, i.detail_fetch_status
FROM detail_job AS job
JOIN info AS i ON i.id = job.info_id
`+whereClause+`
ORDER BY job.priority DESC, job.next_run_at ASC, job.id ASC
LIMIT ?`,
		args...,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []admin.DetailJobSample{}
	for rows.Next() {
		var item admin.DetailJobSample
		if err := rows.Scan(
			&item.ID,
			&item.InfoID,
			&item.Title,
			&item.ChannelCode,
			&item.Status,
			&item.Priority,
			&item.AttemptCount,
			&item.MaxAttempts,
			&item.LastFailureReason,
			&item.NextRunAt,
			&item.DetailScore,
			&item.DetailFetchStatus,
		); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func detailJobWhereClause(filter admin.DetailJobFilter, prefix string) (string, []any) {
	conditions := []string{}
	args := []any{}
	if filter.ChannelCode != "" {
		conditions = append(conditions, "channel_code = ?")
		args = append(args, filter.ChannelCode)
	}
	if filter.FailureReason != "" {
		conditions = append(conditions, "last_failure_reason = ?")
		args = append(args, filter.FailureReason)
	}
	if len(conditions) == 0 {
		return "", args
	}
	return prefix + " " + strings.Join(conditions, " AND "), args
}

func (s *MySQLStore) ListCrawlTasks(ctx context.Context) ([]admin.CrawlTask, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT t.task_code, t.task_name, ch.code, ch.name,
       t.schedule_type, t.schedule_value, t.status,
       COALESCE(DATE_FORMAT(t.last_run_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(t.next_run_at, '%Y-%m-%d %H:%i:%s'), '')
FROM crawl_task AS t
JOIN channel AS ch ON ch.id = t.channel_id
ORDER BY t.status ASC, t.id ASC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []admin.CrawlTask{}
	for rows.Next() {
		var item admin.CrawlTask
		if err := rows.Scan(
			&item.TaskCode,
			&item.TaskName,
			&item.ChannelCode,
			&item.ChannelName,
			&item.ScheduleType,
			&item.ScheduleValue,
			&item.Status,
			&item.LastRunAt,
			&item.NextRunAt,
		); err != nil {
			return nil, err
		}
		result = append(result, item)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return result, nil
}

func (s *MySQLStore) ListCategories(ctx context.Context) ([]admin.Category, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT id, name, code, description,
       COALESCE(DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s'), '')
FROM category
ORDER BY id ASC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []admin.Category{}
	for rows.Next() {
		var item admin.Category
		if err := rows.Scan(&item.ID, &item.Name, &item.Code, &item.Description, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, err
		}
		result = append(result, item)
	}
	return result, rows.Err()
}

func (s *MySQLStore) CreateCategory(ctx context.Context, payload admin.CategoryPayload) (admin.Category, error) {
	result, err := s.db.ExecContext(
		ctx,
		`INSERT INTO category (name, code, description) VALUES (?, ?, ?)`,
		payload.Name,
		payload.Code,
		payload.Description,
	)
	if err != nil {
		if isDuplicateError(err) {
			return admin.Category{}, admin.ErrDuplicated
		}
		return admin.Category{}, err
	}
	id, err := result.LastInsertId()
	if err != nil {
		return admin.Category{}, err
	}
	return s.getCategoryByID(ctx, id)
}

func (s *MySQLStore) UpdateCategory(ctx context.Context, id int64, payload admin.CategoryPayload) (admin.Category, error) {
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE category SET name = ?, code = ?, description = ? WHERE id = ?`,
		payload.Name,
		payload.Code,
		payload.Description,
		id,
	)
	if err != nil {
		if isDuplicateError(err) {
			return admin.Category{}, admin.ErrDuplicated
		}
		return admin.Category{}, err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return admin.Category{}, err
	}
	if affected == 0 {
		return admin.Category{}, admin.ErrNotFound
	}
	return s.getCategoryByID(ctx, id)
}

func (s *MySQLStore) ListChannels(ctx context.Context) ([]admin.Channel, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT ch.id, ch.name, ch.code, ch.base_url, ch.category_id, c.name,
       ch.base_interval_minutes, ch.hot_interval_minutes,
       ch.min_interval_minutes, ch.max_interval_minutes, ch.manual_interval_enabled,
       ch.effective_interval_minutes, ch.schedule_version, ch.is_active,
       COALESCE(DATE_FORMAT(ch.created_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(ch.updated_at, '%Y-%m-%d %H:%i:%s'), '')
FROM channel AS ch
JOIN category AS c ON c.id = ch.category_id
ORDER BY ch.id ASC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []admin.Channel{}
	for rows.Next() {
		var item admin.Channel
		if err := rows.Scan(
			&item.ID,
			&item.Name,
			&item.Code,
			&item.BaseURL,
			&item.CategoryID,
			&item.CategoryName,
			&item.BaseIntervalMinutes,
			&item.HotIntervalMinutes,
			&item.MinIntervalMinutes,
			&item.MaxIntervalMinutes,
			&item.ManualIntervalEnabled,
			&item.EffectiveIntervalMinutes,
			&item.ScheduleVersion,
			&item.IsActive,
			&item.CreatedAt,
			&item.UpdatedAt,
		); err != nil {
			return nil, err
		}
		item.CrawlInterval = item.BaseIntervalMinutes
		result = append(result, item)
	}
	return result, rows.Err()
}

func (s *MySQLStore) CreateChannel(ctx context.Context, payload admin.ChannelPayload) (admin.Channel, error) {
	if err := s.ensureCategoryExists(ctx, payload.CategoryID); err != nil {
		return admin.Channel{}, err
	}
	result, err := s.db.ExecContext(
		ctx,
		`INSERT INTO channel (
	name, code, base_url, category_id,
	base_interval_minutes, hot_interval_minutes, min_interval_minutes, max_interval_minutes,
	manual_interval_enabled, effective_interval_minutes, schedule_version, is_active
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`,
		payload.Name,
		payload.Code,
		payload.BaseURL,
		payload.CategoryID,
		payload.BaseIntervalMinutes,
		payload.HotIntervalMinutes,
		payload.MinIntervalMinutes,
		payload.MaxIntervalMinutes,
		payload.ManualIntervalEnabled,
		payload.EffectiveIntervalMinutes,
		payload.IsActive,
	)
	if err != nil {
		if isDuplicateError(err) {
			return admin.Channel{}, admin.ErrDuplicated
		}
		return admin.Channel{}, err
	}
	id, err := result.LastInsertId()
	if err != nil {
		return admin.Channel{}, err
	}
	return s.getChannelByID(ctx, id)
}

func (s *MySQLStore) UpdateChannel(ctx context.Context, id int64, payload admin.ChannelPayload) (admin.Channel, error) {
	if err := s.ensureCategoryExists(ctx, payload.CategoryID); err != nil {
		return admin.Channel{}, err
	}
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE channel
SET name = ?, code = ?, base_url = ?, category_id = ?,
    base_interval_minutes = ?, hot_interval_minutes = ?, min_interval_minutes = ?, max_interval_minutes = ?,
    manual_interval_enabled = ?, effective_interval_minutes = ?, schedule_version = schedule_version + 1,
    is_active = ?
WHERE id = ?`,
		payload.Name,
		payload.Code,
		payload.BaseURL,
		payload.CategoryID,
		payload.BaseIntervalMinutes,
		payload.HotIntervalMinutes,
		payload.MinIntervalMinutes,
		payload.MaxIntervalMinutes,
		payload.ManualIntervalEnabled,
		payload.EffectiveIntervalMinutes,
		payload.IsActive,
		id,
	)
	if err != nil {
		if isDuplicateError(err) {
			return admin.Channel{}, admin.ErrDuplicated
		}
		return admin.Channel{}, err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return admin.Channel{}, err
	}
	if affected == 0 {
		return admin.Channel{}, admin.ErrNotFound
	}
	return s.getChannelByID(ctx, id)
}

func (s *MySQLStore) ListLLMModelConfigs(ctx context.Context) (any, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT cfg.id, cfg.provider_name, cfg.provider_code, cfg.base_url, cfg.api_key,
       cfg.model_name, cfg.is_enabled, cfg.daily_call_limit, cfg.daily_call_count,
       COALESCE(DATE_FORMAT(cfg.last_call_date, '%Y-%m-%d'), ''),
       cfg.priority, cfg.consecutive_failure_count,
       COALESCE(DATE_FORMAT(cfg.circuit_open_until, '%Y-%m-%d %H:%i:%s'), ''),
       cfg.last_failure_reason,
       COALESCE(stats.success_count, 0),
       COALESCE(stats.failure_count, 0),
       COALESCE(ROUND(stats.avg_latency_ms), 0),
       COALESCE(stats.last_error_message, ''),
       COALESCE(DATE_FORMAT(cfg.created_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(cfg.updated_at, '%Y-%m-%d %H:%i:%s'), '')
FROM llm_model_config AS cfg
LEFT JOIN (
  SELECT base.config_id,
         SUM(CASE WHEN base.status = 'succeeded' THEN 1 ELSE 0 END) AS success_count,
         SUM(CASE WHEN base.status = 'failed' THEN 1 ELSE 0 END) AS failure_count,
         AVG(base.latency_ms) AS avg_latency_ms,
         SUBSTRING_INDEX(
           GROUP_CONCAT(CASE WHEN base.status = 'failed' AND base.error_message <> '' THEN base.error_message END ORDER BY base.created_at DESC, base.id DESC SEPARATOR '\n'),
           '\n',
           1
         ) AS last_error_message
  FROM (
    SELECT log.*
    FROM llm_call_log AS log
    WHERE (
      SELECT COUNT(*)
      FROM llm_call_log AS newer
      WHERE newer.config_id = log.config_id
        AND (newer.created_at > log.created_at OR (newer.created_at = log.created_at AND newer.id >= log.id))
    ) <= 100
  ) AS base
  GROUP BY base.config_id
) AS stats ON stats.config_id = cfg.id
ORDER BY cfg.priority ASC, cfg.id ASC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := []map[string]any{}
	for rows.Next() {
		var item llmModelConfigRow
		if err := rows.Scan(
			&item.ID,
			&item.ProviderName,
			&item.ProviderCode,
			&item.BaseURL,
			&item.APIKey,
			&item.ModelName,
			&item.IsEnabled,
			&item.DailyCallLimit,
			&item.DailyCallCount,
			&item.LastCallDate,
			&item.Priority,
			&item.ConsecutiveFailureCount,
			&item.CircuitOpenUntil,
			&item.LastFailureReason,
			&item.SuccessCount,
			&item.FailureCount,
			&item.AvgLatencyMS,
			&item.LastErrorMessage,
			&item.CreatedAt,
			&item.UpdatedAt,
		); err != nil {
			return nil, err
		}
		result = append(result, item.toMap(true))
	}
	return result, rows.Err()
}

func (s *MySQLStore) CreateLLMModelConfig(ctx context.Context, payload map[string]any) (any, error) {
	result, err := s.db.ExecContext(
		ctx,
		`INSERT INTO llm_model_config (
  provider_name, provider_code, base_url, api_key, model_name,
  is_enabled, daily_call_limit, daily_call_count, last_call_date, priority,
  consecutive_failure_count, circuit_open_until, last_failure_reason
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_DATE, ?, 0, NULL, '')`,
		stringPayloadValue(payload, "provider_name"),
		stringPayloadValue(payload, "provider_code"),
		stringPayloadValue(payload, "base_url"),
		stringPayloadValue(payload, "api_key"),
		stringPayloadValue(payload, "model_name"),
		intPayloadValue(payload, "is_enabled"),
		intPayloadValue(payload, "daily_call_limit"),
		intPayloadValue(payload, "daily_call_count"),
		intPayloadValue(payload, "priority"),
	)
	if err != nil {
		if isDuplicateError(err) {
			return nil, admin.ErrDuplicated
		}
		return nil, err
	}
	id, err := result.LastInsertId()
	if err != nil {
		return nil, err
	}
	return s.getLLMModelConfigByID(ctx, id)
}

func (s *MySQLStore) UpdateLLMModelConfig(ctx context.Context, id int64, payload map[string]any) (any, error) {
	current, err := s.getLLMModelConfigRowByID(ctx, id)
	if err != nil {
		return nil, err
	}
	apiKey := stringPayloadValue(payload, "api_key")
	if apiKey == "" || apiKey == "******" || apiKey == "********" {
		apiKey = current.APIKey
	}
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE llm_model_config
SET provider_name = ?, provider_code = ?, base_url = ?, api_key = ?, model_name = ?,
    is_enabled = ?, daily_call_limit = ?, daily_call_count = ?, priority = ?
WHERE id = ?`,
		stringPayloadValue(payload, "provider_name"),
		stringPayloadValue(payload, "provider_code"),
		stringPayloadValue(payload, "base_url"),
		apiKey,
		stringPayloadValue(payload, "model_name"),
		intPayloadValue(payload, "is_enabled"),
		intPayloadValue(payload, "daily_call_limit"),
		intPayloadValue(payload, "daily_call_count"),
		intPayloadValue(payload, "priority"),
		id,
	)
	if err != nil {
		if isDuplicateError(err) {
			return nil, admin.ErrDuplicated
		}
		return nil, err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return nil, err
	}
	if affected == 0 {
		return nil, admin.ErrNotFound
	}
	return s.getLLMModelConfigByID(ctx, id)
}

func (s *MySQLStore) GetChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	credential, err := s.getChannelCredentialRow(ctx, channelCode)
	if err != nil {
		return nil, err
	}
	cookiesData := parseStoredCookies(credential.Cookies)
	cookieValue := stringFromMap(cookiesData, "cookie")
	cookieStatus := stringFromMap(cookiesData, "status")
	if cookieStatus == "" {
		cookieStatus = "not_configured"
	}
	cookieConfigured := cookieValue != "" && !isSampleCredentialStatus(cookieStatus)
	return map[string]any{
		"channel_code":      channelCode,
		"cookie_configured": cookieConfigured,
		"cookie_preview":    maskSecret(cookieValue),
		"cookie_status":     cookieStatus,
		"extra_credentials": parseJSONObject(credential.ExtraCredentials),
		"updated_at":        credential.UpdatedAt,
		"updated_by":        credential.UpdatedBy,
	}, nil
}

func (s *MySQLStore) UpdateChannelCredentials(ctx context.Context, channelCode string, payload admin.ChannelCredentialPayload) (map[string]any, error) {
	credential, err := s.getChannelCredentialRow(ctx, channelCode)
	if err != nil {
		return nil, err
	}
	cookies := credential.Cookies
	if payload.Cookies != "" {
		existing := parseStoredCookies(credential.Cookies)
		newCookieData := parseCookiePayload(payload.Cookies)
		for key, value := range newCookieData {
			existing[key] = value
		}
		if stringFromMap(existing, "cookie") != "" && isSampleCredentialStatus(stringFromMap(existing, "status")) {
			existing["status"] = "active"
		}
		if stringFromMap(existing, "status") == "" {
			existing["status"] = "active"
		}
		if _, ok := existing["last_verified_at"]; !ok {
			existing["last_verified_at"] = nil
		}
		cookies, err = marshalJSONObject(existing)
		if err != nil {
			return nil, err
		}
	}
	extraCredentials := credential.ExtraCredentials
	if payload.ExtraCredentials != nil {
		normalizeExtraCredentialStatus(channelCode, payload.ExtraCredentials)
		extraCredentials, err = marshalJSONObject(payload.ExtraCredentials)
		if err != nil {
			return nil, err
		}
	}
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE channel
SET cookies = ?, extra_credentials = ?, credentials_updated_at = CURRENT_TIMESTAMP, credentials_updated_by = ?
WHERE code = ?`,
		cookies,
		extraCredentials,
		payload.UpdatedBy,
		channelCode,
	)
	if err != nil {
		return nil, err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return nil, err
	}
	if affected == 0 {
		return nil, admin.ErrNotFound
	}
	return map[string]any{"channel_code": channelCode}, nil
}

func (s *MySQLStore) DeleteChannelCredentials(ctx context.Context, channelCode string) (map[string]any, error) {
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE channel
SET cookies = '', extra_credentials = '{}', credentials_updated_at = CURRENT_TIMESTAMP, credentials_updated_by = ''
WHERE code = ?`,
		channelCode,
	)
	if err != nil {
		return nil, err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return nil, err
	}
	if affected == 0 {
		return nil, admin.ErrNotFound
	}
	return map[string]any{"channel_code": channelCode}, nil
}

func (s *MySQLStore) ListAuditLogs(ctx context.Context, limit int) ([]admin.AuditLog, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT log.id, log.admin_user_id, user.email, log.action,
		       log.target_type, log.target_id, log.ip_address,
		       DATE_FORMAT(log.created_at, '%Y-%m-%d %H:%i:%s')
FROM admin_audit_log AS log
JOIN user_account AS user ON user.id = log.admin_user_id
ORDER BY log.created_at DESC, log.id DESC
LIMIT ?`,
		limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []admin.AuditLog{}
	for rows.Next() {
		var item admin.AuditLog
		if err := rows.Scan(
			&item.ID,
			&item.AdminUserID,
			&item.AdminEmail,
			&item.Action,
			&item.TargetType,
			&item.TargetID,
			&item.IPAddress,
			&item.CreatedAt,
		); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (s *MySQLStore) getCategoryByID(ctx context.Context, id int64) (admin.Category, error) {
	row := s.db.QueryRowContext(
		ctx,
		`SELECT id, name, code, description,
       COALESCE(DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s'), '')
FROM category
WHERE id = ?`,
		id,
	)
	var item admin.Category
	err := row.Scan(&item.ID, &item.Name, &item.Code, &item.Description, &item.CreatedAt, &item.UpdatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return admin.Category{}, admin.ErrNotFound
	}
	return item, err
}

func (s *MySQLStore) getChannelByID(ctx context.Context, id int64) (admin.Channel, error) {
	row := s.db.QueryRowContext(
		ctx,
		`SELECT ch.id, ch.name, ch.code, ch.base_url, ch.category_id, c.name,
       ch.base_interval_minutes, ch.hot_interval_minutes,
       ch.min_interval_minutes, ch.max_interval_minutes, ch.manual_interval_enabled,
       ch.effective_interval_minutes, ch.schedule_version, ch.is_active,
       COALESCE(DATE_FORMAT(ch.created_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(ch.updated_at, '%Y-%m-%d %H:%i:%s'), '')
FROM channel AS ch
JOIN category AS c ON c.id = ch.category_id
WHERE ch.id = ?`,
		id,
	)
	var item admin.Channel
	err := row.Scan(
		&item.ID,
		&item.Name,
		&item.Code,
		&item.BaseURL,
		&item.CategoryID,
		&item.CategoryName,
		&item.BaseIntervalMinutes,
		&item.HotIntervalMinutes,
		&item.MinIntervalMinutes,
		&item.MaxIntervalMinutes,
		&item.ManualIntervalEnabled,
		&item.EffectiveIntervalMinutes,
		&item.ScheduleVersion,
		&item.IsActive,
		&item.CreatedAt,
		&item.UpdatedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return admin.Channel{}, admin.ErrNotFound
	}
	item.CrawlInterval = item.BaseIntervalMinutes
	return item, err
}

func (s *MySQLStore) ensureCategoryExists(ctx context.Context, categoryID int64) error {
	var exists int
	err := s.db.QueryRowContext(ctx, `SELECT 1 FROM category WHERE id = ? LIMIT 1`, categoryID).Scan(&exists)
	if errors.Is(err, sql.ErrNoRows) {
		return admin.ErrNotFound
	}
	return err
}

func (s *MySQLStore) getLLMModelConfigByID(ctx context.Context, id int64) (any, error) {
	item, err := s.getLLMModelConfigRowByID(ctx, id)
	if err != nil {
		return nil, err
	}
	return item.toMap(true), nil
}

func (s *MySQLStore) getLLMModelConfigRowByID(ctx context.Context, id int64) (llmModelConfigRow, error) {
	row := s.db.QueryRowContext(
		ctx,
		`SELECT id, provider_name, provider_code, base_url, api_key,
       model_name, is_enabled, daily_call_limit, daily_call_count,
       COALESCE(DATE_FORMAT(last_call_date, '%Y-%m-%d'), ''),
       priority, consecutive_failure_count,
       COALESCE(DATE_FORMAT(circuit_open_until, '%Y-%m-%d %H:%i:%s'), ''),
       last_failure_reason,
       COALESCE(DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s'), '')
FROM llm_model_config
WHERE id = ?`,
		id,
	)
	var item llmModelConfigRow
	err := row.Scan(
		&item.ID,
		&item.ProviderName,
		&item.ProviderCode,
		&item.BaseURL,
		&item.APIKey,
		&item.ModelName,
		&item.IsEnabled,
		&item.DailyCallLimit,
		&item.DailyCallCount,
		&item.LastCallDate,
		&item.Priority,
		&item.ConsecutiveFailureCount,
		&item.CircuitOpenUntil,
		&item.LastFailureReason,
		&item.CreatedAt,
		&item.UpdatedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return llmModelConfigRow{}, admin.ErrNotFound
	}
	return item, err
}

func (s *MySQLStore) getChannelCredentialRow(ctx context.Context, channelCode string) (channelCredentialRow, error) {
	row := s.db.QueryRowContext(
		ctx,
		`SELECT code, COALESCE(cookies, ''), COALESCE(CAST(extra_credentials AS CHAR), '{}'),
       COALESCE(DATE_FORMAT(credentials_updated_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(credentials_updated_by, '')
FROM channel
WHERE code = ?`,
		channelCode,
	)
	var item channelCredentialRow
	err := row.Scan(&item.ChannelCode, &item.Cookies, &item.ExtraCredentials, &item.UpdatedAt, &item.UpdatedBy)
	if errors.Is(err, sql.ErrNoRows) {
		return channelCredentialRow{}, admin.ErrNotFound
	}
	return item, err
}

type channelCredentialRow struct {
	ChannelCode      string
	Cookies          string
	ExtraCredentials string
	UpdatedAt        string
	UpdatedBy        string
}

type llmModelConfigRow struct {
	ID                      int64
	ProviderName            string
	ProviderCode            string
	BaseURL                 string
	APIKey                  string
	ModelName               string
	IsEnabled               int
	DailyCallLimit          int
	DailyCallCount          int
	LastCallDate            string
	Priority                int
	ConsecutiveFailureCount int
	CircuitOpenUntil        string
	LastFailureReason       string
	SuccessCount            int
	FailureCount            int
	AvgLatencyMS            int
	LastErrorMessage        string
	CreatedAt               string
	UpdatedAt               string
}

func (r llmModelConfigRow) toMap(maskSecret bool) map[string]any {
	apiKey := r.APIKey
	if maskSecret {
		apiKey = maskAPIKey(apiKey)
	}
	return map[string]any{
		"id":                        r.ID,
		"provider_name":             r.ProviderName,
		"provider_code":             r.ProviderCode,
		"base_url":                  r.BaseURL,
		"api_key":                   apiKey,
		"model_name":                r.ModelName,
		"is_enabled":                r.IsEnabled,
		"daily_call_limit":          r.DailyCallLimit,
		"daily_call_count":          r.DailyCallCount,
		"last_call_date":            r.LastCallDate,
		"priority":                  r.Priority,
		"consecutive_failure_count": r.ConsecutiveFailureCount,
		"circuit_open_until":        r.CircuitOpenUntil,
		"last_failure_reason":       r.LastFailureReason,
		"success_count":             r.SuccessCount,
		"failure_count":             r.FailureCount,
		"avg_latency_ms":            r.AvgLatencyMS,
		"last_error_message":        r.LastErrorMessage,
		"created_at":                r.CreatedAt,
		"updated_at":                r.UpdatedAt,
	}
}

func maskAPIKey(apiKey string) string {
	if apiKey == "" {
		return ""
	}
	if len(apiKey) <= 8 {
		return strings.Repeat("*", len(apiKey))
	}
	return apiKey[:4] + "..." + apiKey[len(apiKey)-4:]
}

func stringPayloadValue(payload map[string]any, key string) string {
	if payload == nil {
		return ""
	}
	value, ok := payload[key]
	if !ok || value == nil {
		return ""
	}
	if text, ok := value.(string); ok {
		return text
	}
	return ""
}

func intPayloadValue(payload map[string]any, key string) int {
	if payload == nil {
		return 0
	}
	switch value := payload[key].(type) {
	case int:
		return value
	case int64:
		return int(value)
	case float64:
		return int(value)
	default:
		return 0
	}
}

func parseCookiePayload(value string) map[string]any {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return map[string]any{}
	}
	if strings.HasPrefix(trimmed, "{") {
		parsed := parseJSONObject(trimmed)
		if len(parsed) > 0 {
			return parsed
		}
	}
	return map[string]any{"cookie": value}
}

func parseStoredCookies(value string) map[string]any {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return map[string]any{}
	}
	if strings.HasPrefix(trimmed, "{") {
		parsed := parseJSONObject(trimmed)
		if len(parsed) > 0 {
			return parsed
		}
	}
	return map[string]any{"cookie": value, "status": "invalid"}
}

func parseJSONObject(value string) map[string]any {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return map[string]any{}
	}
	var parsed map[string]any
	if err := json.Unmarshal([]byte(trimmed), &parsed); err != nil {
		return map[string]any{}
	}
	if parsed == nil {
		return map[string]any{}
	}
	return parsed
}

func marshalJSONObject(value map[string]any) (string, error) {
	if value == nil {
		value = map[string]any{}
	}
	bytes, err := json.Marshal(value)
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}

func normalizeExtraCredentialStatus(channelCode string, extraCredentials map[string]any) {
	if channelCode != "zhihu" {
		return
	}
	raw, ok := extraCredentials["zhihu"]
	if !ok {
		return
	}
	zhihu, ok := raw.(map[string]any)
	if !ok {
		return
	}
	if (stringFromMap(zhihu, "zse_93") != "" || stringFromMap(zhihu, "zse_96") != "") && isSampleCredentialStatus(stringFromMap(zhihu, "status")) {
		zhihu["status"] = "active"
	}
}

func stringFromMap(value map[string]any, key string) string {
	raw, ok := value[key]
	if !ok || raw == nil {
		return ""
	}
	text, ok := raw.(string)
	if !ok {
		return ""
	}
	return text
}

func isSampleCredentialStatus(status string) bool {
	switch strings.ToLower(strings.TrimSpace(status)) {
	case "sample", "placeholder", "example":
		return true
	default:
		return false
	}
}

func maskSecret(value string) string {
	if value == "" {
		return ""
	}
	if len(value) <= 12 {
		return "***"
	}
	return value[:4] + "..." + value[len(value)-4:]
}

func (s *MySQLStore) GetEventAnalysisRuns(ctx context.Context, eventID int64) (admin.EventAnalysisRunsResult, error) {
	// 获取事件标题
	var eventTitle string
	err := s.db.QueryRowContext(ctx, `SELECT title FROM event WHERE id = ?`, eventID).Scan(&eventTitle)
	if errors.Is(err, sql.ErrNoRows) {
		return admin.EventAnalysisRunsResult{}, admin.ErrNotFound
	}
	if err != nil {
		return admin.EventAnalysisRunsResult{}, err
	}

	// 获取分析运行记录
	rows, err := s.db.QueryContext(ctx, `
		SELECT
			id, analysis_version, mode, provider, model_name,
			status, input_item_count, quality_score, confidence,
			fallback_used, failure_reason,
			COALESCE(DATE_FORMAT(started_at, '%Y-%m-%d %H:%i:%s'), ''),
			COALESCE(DATE_FORMAT(finished_at, '%Y-%m-%d %H:%i:%s'), ''),
			COALESCE(DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s'), '')
		FROM event_analysis_run
		WHERE event_id = ?
		ORDER BY created_at DESC
	`, eventID)
	if err != nil {
		return admin.EventAnalysisRunsResult{}, err
	}
	defer rows.Close()

	var runs []admin.AnalysisRun
	for rows.Next() {
		var run admin.AnalysisRun
		var fallbackUsed int
		if err := rows.Scan(
			&run.RunID, &run.AnalysisVersion, &run.Mode, &run.Provider, &run.ModelName,
			&run.Status, &run.InputItemCount, &run.QualityScore, &run.Confidence,
			&fallbackUsed, &run.FailureReason,
			&run.StartedAt, &run.FinishedAt, &run.CreatedAt,
		); err != nil {
			return admin.EventAnalysisRunsResult{}, err
		}
		run.FallbackUsed = fallbackUsed == 1
		runs = append(runs, run)
	}
	if runs == nil {
		runs = []admin.AnalysisRun{}
	}

	return admin.EventAnalysisRunsResult{
		EventID:    eventID,
		EventTitle: eventTitle,
		Runs:       runs,
	}, rows.Err()
}

func (s *MySQLStore) GetEventAnalysisSources(ctx context.Context, eventID int64, runID int64) (admin.EventAnalysisSourcesResult, error) {
	// 获取事件标题
	var eventTitle string
	err := s.db.QueryRowContext(ctx, `SELECT title FROM event WHERE id = ?`, eventID).Scan(&eventTitle)
	if errors.Is(err, sql.ErrNoRows) {
		return admin.EventAnalysisSourcesResult{}, admin.ErrNotFound
	}
	if err != nil {
		return admin.EventAnalysisSourcesResult{}, err
	}

	// 获取分析运行详情
	var run admin.AnalysisRun
	var fallbackUsed int
	err = s.db.QueryRowContext(ctx, `
		SELECT
			id, analysis_version, mode, provider, model_name,
			status, input_item_count, quality_score, confidence,
			fallback_used, failure_reason,
			COALESCE(DATE_FORMAT(started_at, '%Y-%m-%d %H:%i:%s'), ''),
			COALESCE(DATE_FORMAT(finished_at, '%Y-%m-%d %H:%i:%s'), ''),
			COALESCE(DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s'), '')
		FROM event_analysis_run
		WHERE id = ? AND event_id = ?
	`, runID, eventID).Scan(
		&run.RunID, &run.AnalysisVersion, &run.Mode, &run.Provider, &run.ModelName,
		&run.Status, &run.InputItemCount, &run.QualityScore, &run.Confidence,
		&fallbackUsed, &run.FailureReason,
		&run.StartedAt, &run.FinishedAt, &run.CreatedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return admin.EventAnalysisSourcesResult{}, admin.ErrNotFound
	}
	if err != nil {
		return admin.EventAnalysisSourcesResult{}, err
	}
	run.FallbackUsed = fallbackUsed == 1

	// 获取来源明细
	rows, err := s.db.QueryContext(ctx, `
		SELECT
			s.id, s.info_id, COALESCE(i.title, s.info_title), s.role, s.weight, s.quality_score,
			COALESCE(c.name, '') AS channel_name,
			COALESCE(i.source_url, '') AS source_url,
			COALESCE(DATE_FORMAT(i.event_time, '%Y-%m-%d %H:%i:%s'), '') AS event_time
		FROM event_analysis_source s
		LEFT JOIN info i ON i.id = s.info_id
		LEFT JOIN channel c ON c.id = i.channel_id
		WHERE s.run_id = ?
		ORDER BY s.weight DESC
	`, runID)
	if err != nil {
		return admin.EventAnalysisSourcesResult{}, err
	}
	defer rows.Close()

	var sources []admin.AnalysisSource
	for rows.Next() {
		var source admin.AnalysisSource
		if err := rows.Scan(
			&source.SourceID, &source.InfoID, &source.Title, &source.Role, &source.Weight, &source.QualityScore,
			&source.ChannelName, &source.SourceURL, &source.EventTime,
		); err != nil {
			return admin.EventAnalysisSourcesResult{}, err
		}
		sources = append(sources, source)
	}
	if sources == nil {
		sources = []admin.AnalysisSource{}
	}

	return admin.EventAnalysisSourcesResult{
		EventID:    eventID,
		EventTitle: eventTitle,
		Run:        run,
		Sources:    sources,
	}, rows.Err()
}
