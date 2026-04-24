package repository

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"info-serve/internal/user"
)

func (s *MySQLStore) ListFavoriteEventIDs(ctx context.Context, userID int64) ([]int64, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT event_id
FROM user_favorite_event
WHERE user_id = ?
ORDER BY created_at DESC, id DESC`,
		userID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	ids := []int64{}
	for rows.Next() {
		var id int64
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		ids = append(ids, id)
	}
	return ids, rows.Err()
}

func (s *MySQLStore) AddFavoriteEvent(ctx context.Context, userID int64, eventID int64) error {
	_, err := s.db.ExecContext(
		ctx,
		`INSERT INTO user_favorite_event (user_id, event_id)
VALUES (?, ?)
ON DUPLICATE KEY UPDATE created_at = created_at`,
		userID,
		eventID,
	)
	return err
}

func (s *MySQLStore) RemoveFavoriteEvent(ctx context.Context, userID int64, eventID int64) error {
	_, err := s.db.ExecContext(
		ctx,
		`DELETE FROM user_favorite_event WHERE user_id = ? AND event_id = ?`,
		userID,
		eventID,
	)
	if err != nil {
		return err
	}
	return nil
}

func (s *MySQLStore) GetPreference(ctx context.Context, userID int64, key string) (string, error) {
	var value string
	err := s.db.QueryRowContext(
		ctx,
		`SELECT preference_value FROM user_preference WHERE user_id = ? AND preference_key = ? LIMIT 1`,
		userID,
		key,
	).Scan(&value)
	if errors.Is(err, sql.ErrNoRows) {
		return "", user.ErrPreferenceNotFound
	}
	return value, err
}

func (s *MySQLStore) SetPreference(ctx context.Context, userID int64, key string, value string) error {
	_, err := s.db.ExecContext(
		ctx,
		`INSERT INTO user_preference (user_id, preference_key, preference_value)
VALUES (?, ?, ?)
ON DUPLICATE KEY UPDATE preference_value = VALUES(preference_value)`,
		userID,
		key,
		value,
	)
	return err
}

func (s *MySQLStore) ListReadHistory(ctx context.Context, userID int64, limit int) ([]user.ReadHistoryItem, error) {
	rows, err := s.db.QueryContext(
		ctx,
		`SELECT
  urh.event_id,
  urh.info_id,
  urh.read_at,
  COALESCE(e.title, i.title, '') AS title,
  CASE
    WHEN urh.event_id IS NOT NULL THEN COALESCE(c.name, '')
    ELSE COALESCE(ic.name, '')
  END AS subtitle,
  CASE
    WHEN urh.event_id IS NOT NULL THEN COALESCE(ch.name, '')
    ELSE COALESCE(ich.name, '')
  END AS source_label,
  CASE
    WHEN urh.event_id IS NOT NULL THEN COALESCE(e.one_line_summary, '')
    ELSE COALESCE(i.content, '')
  END AS primary_remark
FROM user_read_history AS urh
LEFT JOIN event AS e ON e.id = urh.event_id
LEFT JOIN category AS c ON c.id = e.primary_category_id
LEFT JOIN info AS ri ON ri.id = (
  SELECT link.item_id
  FROM event_item_link AS link
  WHERE link.event_id = e.id
  ORDER BY link.is_primary DESC, link.weight DESC, link.id ASC
  LIMIT 1
)
LEFT JOIN channel AS ch ON ch.id = ri.channel_id
LEFT JOIN info AS i ON i.id = urh.info_id
LEFT JOIN category AS ic ON ic.id = i.category_id
LEFT JOIN channel AS ich ON ich.id = i.channel_id
WHERE urh.user_id = ?
ORDER BY urh.read_at DESC, urh.id DESC
LIMIT ?`,
		userID,
		limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	items := []user.ReadHistoryItem{}
	for rows.Next() {
		var item user.ReadHistoryItem
		var eventID sql.NullInt64
		var infoID sql.NullInt64
		var title string
		var subtitle string
		var sourceLabel string
		var primaryRemark string
		if err := rows.Scan(&eventID, &infoID, &item.ReadAt, &title, &subtitle, &sourceLabel, &primaryRemark); err != nil {
			return nil, err
		}
		item.Title = title
		item.Subtitle = subtitle
		item.SourceLabel = sourceLabel
		item.PrimaryRemark = primaryRemark
		if eventID.Valid {
			item.ItemType = "event"
			id := eventID.Int64
			item.EventID = &id
			item.TargetPath = fmt.Sprintf("/events/%d", id)
		}
		if infoID.Valid {
			item.ItemType = "info"
			id := infoID.Int64
			item.InfoID = &id
			item.TargetPath = fmt.Sprintf("/info/%d", id)
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (s *MySQLStore) RecordReadHistory(ctx context.Context, userID int64, eventID *int64, infoID *int64) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()

	if eventID != nil {
		if _, err := tx.ExecContext(ctx, `DELETE FROM user_read_history WHERE user_id = ? AND event_id = ?`, userID, *eventID); err != nil {
			return err
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO user_read_history (user_id, event_id) VALUES (?, ?)`, userID, *eventID); err != nil {
			return err
		}
	}

	if infoID != nil {
		if _, err := tx.ExecContext(ctx, `DELETE FROM user_read_history WHERE user_id = ? AND info_id = ?`, userID, *infoID); err != nil {
			return err
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO user_read_history (user_id, info_id) VALUES (?, ?)`, userID, *infoID); err != nil {
			return err
		}
	}

	return tx.Commit()
}

var _ user.Store = (*MySQLStore)(nil)
