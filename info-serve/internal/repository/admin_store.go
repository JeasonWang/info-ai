package repository

import (
	"context"
	"database/sql"

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
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT channel_code, status, raw_count, cleaned_count, saved_count,
       detail_success_count, detail_failed_count,
       COALESCE(DATE_FORMAT(started_at, '%Y-%m-%d %H:%i:%s'), ''),
       COALESCE(DATE_FORMAT(finished_at, '%Y-%m-%d %H:%i:%s'), '')
FROM crawl_run_log
ORDER BY started_at DESC
LIMIT 8`,
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
