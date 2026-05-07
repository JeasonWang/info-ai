package repository

import (
	"context"
	"database/sql"
	"errors"
	"strings"
	"time"

	"info-serve/internal/auth"
)

// MySQLStore 使用 MySQL 保存用户账号和会话。
type MySQLStore struct {
	db *sql.DB
}

func NewMySQLStore(db *sql.DB) *MySQLStore {
	return &MySQLStore{db: db}
}

func (s *MySQLStore) CreateUser(ctx context.Context, params auth.CreateUserParams) (auth.User, error) {
	result, err := s.db.ExecContext(
		ctx,
		`INSERT INTO user_account (email, password_hash, role, status) VALUES (?, ?, ?, 'active')`,
		params.Email,
		params.PasswordHash,
		params.Role,
	)
	if err != nil {
		if isDuplicateError(err) {
			return auth.User{}, auth.ErrEmailAlreadyExists
		}
		return auth.User{}, err
	}
	id, err := result.LastInsertId()
	if err != nil {
		return auth.User{}, err
	}
	return auth.User{
		ID:           id,
		Email:        params.Email,
		PasswordHash: params.PasswordHash,
		Role:         params.Role,
		Status:       "active",
	}, nil
}

func (s *MySQLStore) FindUserByEmail(ctx context.Context, email string) (auth.User, error) {
	row := s.db.QueryRowContext(
		ctx,
		`SELECT id, email, password_hash, role, status FROM user_account WHERE email = ? LIMIT 1`,
		email,
	)
	return scanUser(row)
}

func (s *MySQLStore) CreateSession(ctx context.Context, params auth.CreateSessionParams) error {
	_, err := s.db.ExecContext(
		ctx,
		`INSERT INTO user_session (user_id, session_token_hash, client_type, expires_at) VALUES (?, ?, 'web', ?)`,
		params.UserID,
		params.TokenHash,
		params.ExpiresAt,
	)
	return err
}

func (s *MySQLStore) FindUserBySessionTokenHash(ctx context.Context, tokenHash string) (auth.User, error) {
	row := s.db.QueryRowContext(
		ctx,
		`SELECT u.id, u.email, u.password_hash, u.role, u.status
FROM user_session AS us
JOIN user_account AS u ON u.id = us.user_id
WHERE us.session_token_hash = ?
  AND us.revoked_at IS NULL
  AND us.expires_at > ?
LIMIT 1`,
		tokenHash,
		time.Now(),
	)
	return scanUser(row)
}

func (s *MySQLStore) RevokeSession(ctx context.Context, tokenHash string) error {
	result, err := s.db.ExecContext(
		ctx,
		`UPDATE user_session SET revoked_at = ? WHERE session_token_hash = ? AND revoked_at IS NULL`,
		time.Now(),
		tokenHash,
	)
	if err != nil {
		return err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if affected == 0 {
		return auth.ErrSessionNotFound
	}
	return nil
}

type userScanner interface {
	Scan(dest ...any) error
}

func scanUser(scanner userScanner) (auth.User, error) {
	var user auth.User
	err := scanner.Scan(&user.ID, &user.Email, &user.PasswordHash, &user.Role, &user.Status)
	if errors.Is(err, sql.ErrNoRows) {
		return auth.User{}, auth.ErrUserNotFound
	}
	return user, err
}

func isDuplicateError(err error) bool {
	return err != nil && (strings.Contains(err.Error(), "Duplicate entry") || strings.Contains(err.Error(), "1062"))
}
