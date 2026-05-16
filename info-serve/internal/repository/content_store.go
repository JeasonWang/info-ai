package repository

import (
	"context"
	"database/sql"
	"errors"
	"strings"

	"info-serve/internal/content"
)

type ContentMySQLStore struct {
	db *sql.DB
}

func NewContentMySQLStore(db *sql.DB) *ContentMySQLStore {
	return &ContentMySQLStore{db: db}
}

func (s *ContentMySQLStore) ListCategories(ctx context.Context) ([]content.Category, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT id, name, code, description,
		       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s'),
		       DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s')
FROM category
ORDER BY id ASC`,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	categories := []content.Category{}
	for rows.Next() {
		var item content.Category
		if err := rows.Scan(&item.ID, &item.Name, &item.Code, &item.Description, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, err
		}
		categories = append(categories, item)
	}
	return categories, rows.Err()
}

func (s *ContentMySQLStore) ListChannels(ctx context.Context, categoryID int64) ([]content.Channel, error) {
	whereSQL := "WHERE ch.is_active = 1"
	args := []any{}
	if categoryID > 0 {
		whereSQL += " AND ch.category_id = ?"
		args = append(args, categoryID)
	}
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT ch.id, ch.name, ch.code, ch.base_url, ch.category_id, c.name,
		       ch.base_interval_minutes, ch.is_active,
		       DATE_FORMAT(ch.created_at, '%Y-%m-%d %H:%i:%s'),
		       DATE_FORMAT(ch.updated_at, '%Y-%m-%d %H:%i:%s')
FROM channel AS ch
JOIN category AS c ON c.id = ch.category_id `+whereSQL+`
ORDER BY ch.id ASC`,
		args...,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	channels := []content.Channel{}
	for rows.Next() {
		var item content.Channel
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
		channels = append(channels, item)
	}
	return channels, rows.Err()
}

func (s *ContentMySQLStore) ListInfos(ctx context.Context, params content.ListInfoParams) (content.InfoPage, error) {
	whereSQL, args := buildInfoWhere(params)
	var total int
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM info AS i `+whereSQL, args...).Scan(&total); err != nil {
		return content.InfoPage{}, err
	}

	offset := (params.Page - 1) * params.PageSize
	listArgs := append(args, params.PageSize, offset)
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT i.id, i.title, COALESCE(i.content, ''), i.category_id, c.name,
		       i.channel_id, ch.name, i.source_id, i.source_url,
		       DATE_FORMAT(i.event_time, '%Y-%m-%d %H:%i:%s'),
		       i.core_entity, i.location, i.indicator_name, i.indicator_value,
		       i.detail_fetch_status, i.detail_fetch_error, i.detail_strategy,
		       i.detail_score, i.detail_content_length,
		       DATE_FORMAT(i.detail_fetched_at, '%Y-%m-%d %H:%i:%s'),
		       i.tech_topic_type, i.tech_entities, i.tech_keywords,
		       DATE_FORMAT(i.created_at, '%Y-%m-%d %H:%i:%s'),
		       DATE_FORMAT(i.updated_at, '%Y-%m-%d %H:%i:%s')
FROM info AS i
JOIN category AS c ON c.id = i.category_id
JOIN channel AS ch ON ch.id = i.channel_id `+whereSQL+`
ORDER BY COALESCE(i.event_time, i.created_at) DESC, i.id DESC
LIMIT ? OFFSET ?`,
		listArgs...,
	)
	if err != nil {
		return content.InfoPage{}, err
	}
	defer rows.Close()

	items := []content.InfoItem{}
	for rows.Next() {
		item, err := scanInfoItem(rows)
		if err != nil {
			return content.InfoPage{}, err
		}
		content.ApplyInfoQuality(&item)
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return content.InfoPage{}, err
	}
	return content.InfoPage{Total: total, Page: params.Page, PageSize: params.PageSize, Items: items}, nil
}

func (s *ContentMySQLStore) GetInfoDetail(ctx context.Context, id int64) (content.InfoItem, error) {
	row := s.db.QueryRowContext(
		ctx,
		`SELECT i.id, i.title, COALESCE(i.content, ''), i.category_id, c.name,
		       i.channel_id, ch.name, i.source_id, i.source_url,
		       DATE_FORMAT(i.event_time, '%Y-%m-%d %H:%i:%s'),
		       i.core_entity, i.location, i.indicator_name, i.indicator_value,
		       i.detail_fetch_status, i.detail_fetch_error, i.detail_strategy,
		       i.detail_score, i.detail_content_length,
		       DATE_FORMAT(i.detail_fetched_at, '%Y-%m-%d %H:%i:%s'),
		       i.tech_topic_type, i.tech_entities, i.tech_keywords,
		       DATE_FORMAT(i.created_at, '%Y-%m-%d %H:%i:%s'),
		       DATE_FORMAT(i.updated_at, '%Y-%m-%d %H:%i:%s')
FROM info AS i
JOIN category AS c ON c.id = i.category_id
JOIN channel AS ch ON ch.id = i.channel_id
WHERE i.id = ? AND i.is_deleted = 0
LIMIT 1`,
		id,
	)
	item, err := scanInfoItem(row)
	if errors.Is(err, sql.ErrNoRows) {
		return content.InfoItem{}, err
	}
	if err != nil {
		return content.InfoItem{}, err
	}
	content.ApplyInfoQuality(&item)
	return item, nil
}

type infoItemScanner interface {
	Scan(dest ...any) error
}

func scanInfoItem(scanner infoItemScanner) (content.InfoItem, error) {
	var item content.InfoItem
	var eventTime sql.NullString
	var detailFetchedAt sql.NullString
	var rawEntities string
	var rawKeywords string
	err := scanner.Scan(
		&item.ID,
		&item.Title,
		&item.Content,
		&item.CategoryID,
		&item.CategoryName,
		&item.ChannelID,
		&item.ChannelName,
		&item.SourceID,
		&item.SourceURL,
		&eventTime,
		&item.CoreEntity,
		&item.Location,
		&item.IndicatorName,
		&item.IndicatorValue,
		&item.DetailFetchStatus,
		&item.DetailFetchError,
		&item.DetailStrategy,
		&item.DetailScore,
		&item.DetailContentLength,
		&detailFetchedAt,
		&item.TechTopicType,
		&rawEntities,
		&rawKeywords,
		&item.CreatedAt,
		&item.UpdatedAt,
	)
	if err != nil {
		return content.InfoItem{}, err
	}
	if eventTime.Valid {
		item.EventTime = eventTime.String
	}
	if detailFetchedAt.Valid {
		item.DetailFetchedAt = detailFetchedAt.String
	}
	item.TechEntities = content.SplitCSV(rawEntities)
	item.TechKeywords = content.SplitCSV(rawKeywords)
	return item, nil
}

func buildInfoWhere(params content.ListInfoParams) (string, []any) {
	clauses := []string{"i.is_deleted = 0"}
	args := []any{}
	if params.CategoryID > 0 {
		clauses = append(clauses, "i.category_id = ?")
		args = append(args, params.CategoryID)
	}
	if params.ChannelID > 0 {
		clauses = append(clauses, "i.channel_id = ?")
		args = append(args, params.ChannelID)
	}
	if strings.TrimSpace(params.Keyword) != "" {
		keyword := "%" + strings.TrimSpace(params.Keyword) + "%"
		clauses = append(clauses, "(i.title LIKE ? OR i.content LIKE ?)")
		args = append(args, keyword, keyword)
	}
	return "WHERE " + strings.Join(clauses, " AND "), args
}

func (s *ContentMySQLStore) GetStats(ctx context.Context) (content.Stats, error) {
	var stats content.Stats
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM info WHERE is_deleted = 0`).Scan(&stats.Total); err != nil {
		return content.Stats{}, err
	}
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT c.name, COUNT(i.id)
FROM category AS c
LEFT JOIN info AS i ON i.category_id = c.id AND i.is_deleted = 0
GROUP BY c.id, c.name
ORDER BY c.id ASC`,
	)
	if err != nil {
		return content.Stats{}, err
	}
	defer rows.Close()
	stats.Categories = []content.CategoryStats{}
	for rows.Next() {
		var item content.CategoryStats
		if err := rows.Scan(&item.Name, &item.Count); err != nil {
			return content.Stats{}, err
		}
		stats.Categories = append(stats.Categories, item)
	}
	return stats, rows.Err()
}
