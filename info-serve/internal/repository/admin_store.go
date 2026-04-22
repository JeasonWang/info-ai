package repository

import (
	"context"
	"database/sql"
	"errors"

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
