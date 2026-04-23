package repository

import (
	"context"

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

var _ user.Store = (*MySQLStore)(nil)
