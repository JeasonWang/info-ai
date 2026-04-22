package repository

import (
	"context"
	"database/sql"
	"os"
	"testing"
	"time"

	_ "github.com/go-sql-driver/mysql"

	"info-serve/internal/auth"
)

func TestMySQLStorePersistsUserAndSession(t *testing.T) {
	dsn := os.Getenv("INFO_SERVE_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Skip("INFO_SERVE_TEST_MYSQL_DSN 未设置，跳过真实 MySQL 集成测试")
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatalf("open mysql: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	store := NewMySQLStore(db)
	ctx := context.Background()
	email := "integration-user@example.com"
	_, _ = db.ExecContext(ctx, "DELETE FROM user_session WHERE user_id IN (SELECT id FROM user_account WHERE email = ?)", email)
	_, _ = db.ExecContext(ctx, "DELETE FROM user_account WHERE email = ?", email)

	user, err := store.CreateUser(ctx, auth.CreateUserParams{
		Email:        email,
		PasswordHash: "hash-for-test",
		Role:         "user",
	})
	if err != nil {
		t.Fatalf("CreateUser returned error: %v", err)
	}
	if user.ID == 0 {
		t.Fatal("created user id should not be zero")
	}

	found, err := store.FindUserByEmail(ctx, email)
	if err != nil {
		t.Fatalf("FindUserByEmail returned error: %v", err)
	}
	if found.Email != email || found.PasswordHash != "hash-for-test" {
		t.Fatalf("found user = %+v", found)
	}

	err = store.CreateSession(ctx, auth.CreateSessionParams{
		UserID:    user.ID,
		Email:     email,
		TokenHash: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
		ExpiresAt: time.Now().Add(time.Hour),
	})
	if err != nil {
		t.Fatalf("CreateSession returned error: %v", err)
	}

	sessionUser, err := store.FindUserBySessionTokenHash(ctx, "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
	if err != nil {
		t.Fatalf("FindUserBySessionTokenHash returned error: %v", err)
	}
	if sessionUser.ID != user.ID {
		t.Fatalf("session user id = %d, want %d", sessionUser.ID, user.ID)
	}
}
