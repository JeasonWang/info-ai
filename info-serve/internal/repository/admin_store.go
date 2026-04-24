package repository

import (
	"context"
	"database/sql"
	"errors"
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

func (s *MySQLStore) ListQualitySnapshots(ctx context.Context, limit int) ([]admin.QualitySnapshot, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT category_code, total_count, duplicate_title_count, empty_content_count,
       low_detail_score_count, missing_entity_count,
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
       ch.crawl_interval, ch.is_active,
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
			&item.CrawlInterval,
			&item.IsActive,
			&item.CreatedAt,
			&item.UpdatedAt,
		); err != nil {
			return nil, err
		}
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
		`INSERT INTO channel (name, code, base_url, category_id, crawl_interval, is_active) VALUES (?, ?, ?, ?, ?, ?)`,
		payload.Name,
		payload.Code,
		payload.BaseURL,
		payload.CategoryID,
		payload.CrawlInterval,
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
SET name = ?, code = ?, base_url = ?, category_id = ?, crawl_interval = ?, is_active = ?
WHERE id = ?`,
		payload.Name,
		payload.Code,
		payload.BaseURL,
		payload.CategoryID,
		payload.CrawlInterval,
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
       ch.crawl_interval, ch.is_active,
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
		&item.CrawlInterval,
		&item.IsActive,
		&item.CreatedAt,
		&item.UpdatedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return admin.Channel{}, admin.ErrNotFound
	}
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
