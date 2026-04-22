package repository

import (
	"context"
	"database/sql"
	"errors"

	"info-serve/internal/auth"
)

// UpsertAdminAccount 创建或更新首个管理员账号。
//
// Pro 初期管理员不开放公开注册，使用该方法配合命令行工具初始化。
func UpsertAdminAccount(ctx context.Context, db *sql.DB, email string, passwordHash string) (auth.User, error) {
	store := NewMySQLStore(db)
	existing, err := store.FindUserByEmail(ctx, email)
	if err == nil {
		_, updateErr := db.ExecContext(
			ctx,
			`UPDATE user_account SET password_hash = ?, role = 'admin', status = 'active' WHERE id = ?`,
			passwordHash,
			existing.ID,
		)
		if updateErr != nil {
			return auth.User{}, updateErr
		}
		existing.PasswordHash = passwordHash
		existing.Role = "admin"
		existing.Status = "active"
		return existing, nil
	}
	if !errors.Is(err, auth.ErrUserNotFound) {
		return auth.User{}, err
	}
	return store.CreateUser(ctx, auth.CreateUserParams{
		Email:        email,
		PasswordHash: passwordHash,
		Role:         "admin",
	})
}
