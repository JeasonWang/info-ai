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

func TestMySQLStorePersistsFavoriteEventIDs(t *testing.T) {
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
	email := "integration-favorite-user@example.com"
	_, _ = db.ExecContext(ctx, "DELETE FROM user_favorite_event WHERE user_id IN (SELECT id FROM user_account WHERE email = ?)", email)
	_, _ = db.ExecContext(ctx, "DELETE FROM user_session WHERE user_id IN (SELECT id FROM user_account WHERE email = ?)", email)
	_, _ = db.ExecContext(ctx, "DELETE FROM user_account WHERE email = ?", email)

	var eventID int64
	if err := db.QueryRowContext(ctx, "SELECT id FROM event ORDER BY id LIMIT 1").Scan(&eventID); err != nil {
		t.Skipf("当前 MySQL 没有 event 数据，跳过收藏集成测试: %v", err)
	}

	user, err := store.CreateUser(ctx, auth.CreateUserParams{
		Email:        email,
		PasswordHash: "hash-for-test",
		Role:         "user",
	})
	if err != nil {
		t.Fatalf("CreateUser returned error: %v", err)
	}
	t.Cleanup(func() {
		_, _ = db.ExecContext(ctx, "DELETE FROM user_favorite_event WHERE user_id = ?", user.ID)
		_, _ = db.ExecContext(ctx, "DELETE FROM user_account WHERE id = ?", user.ID)
	})

	if err := store.AddFavoriteEvent(ctx, user.ID, eventID); err != nil {
		t.Fatalf("AddFavoriteEvent returned error: %v", err)
	}

	ids, err := store.ListFavoriteEventIDs(ctx, user.ID)
	if err != nil {
		t.Fatalf("ListFavoriteEventIDs returned error: %v", err)
	}
	if len(ids) != 1 || ids[0] != eventID {
		t.Fatalf("favorite event ids = %+v, want [%d]", ids, eventID)
	}

	items, err := store.ListFavoriteEvents(ctx, user.ID, 20)
	if err != nil {
		t.Fatalf("ListFavoriteEvents returned error: %v", err)
	}
	if len(items) != 1 || items[0].ID != eventID || items[0].TargetPath == "" {
		t.Fatalf("favorite event items = %+v", items)
	}

	if err := store.RemoveFavoriteEvent(ctx, user.ID, eventID); err != nil {
		t.Fatalf("RemoveFavoriteEvent returned error: %v", err)
	}

	ids, err = store.ListFavoriteEventIDs(ctx, user.ID)
	if err != nil {
		t.Fatalf("ListFavoriteEventIDs after remove returned error: %v", err)
	}
	if len(ids) != 0 {
		t.Fatalf("favorite event ids after remove = %+v, want empty", ids)
	}
}

func TestMySQLStorePersistsUserPreferences(t *testing.T) {
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
	email := "integration-preference-user@example.com"
	_, _ = db.ExecContext(ctx, "DELETE FROM user_preference WHERE user_id IN (SELECT id FROM user_account WHERE email = ?)", email)
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
	t.Cleanup(func() {
		_, _ = db.ExecContext(ctx, "DELETE FROM user_preference WHERE user_id = ?", user.ID)
		_, _ = db.ExecContext(ctx, "DELETE FROM user_account WHERE id = ?", user.ID)
	})

	if err := store.SetPreference(ctx, user.ID, "home_filter", `{"category_code":"sports","sort":"latest","keyword":"NBA"}`); err != nil {
		t.Fatalf("SetPreference returned error: %v", err)
	}

	value, err := store.GetPreference(ctx, user.ID, "home_filter")
	if err != nil {
		t.Fatalf("GetPreference returned error: %v", err)
	}
	if value != `{"category_code":"sports","sort":"latest","keyword":"NBA"}` {
		t.Fatalf("preference value = %q", value)
	}
}

func TestMySQLStorePersistsReadHistory(t *testing.T) {
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
	email := "integration-read-history-user@example.com"
	_, _ = db.ExecContext(ctx, "DELETE FROM user_read_history WHERE user_id IN (SELECT id FROM user_account WHERE email = ?)", email)
	_, _ = db.ExecContext(ctx, "DELETE FROM user_session WHERE user_id IN (SELECT id FROM user_account WHERE email = ?)", email)
	_, _ = db.ExecContext(ctx, "DELETE FROM user_account WHERE email = ?", email)

	var eventID int64
	if err := db.QueryRowContext(ctx, "SELECT id FROM event ORDER BY id LIMIT 1").Scan(&eventID); err != nil {
		t.Skipf("当前 MySQL 没有 event 数据，跳过阅读历史集成测试: %v", err)
	}

	var infoID int64
	if err := db.QueryRowContext(ctx, "SELECT id FROM info ORDER BY id LIMIT 1").Scan(&infoID); err != nil {
		t.Skipf("当前 MySQL 没有 info 数据，跳过阅读历史集成测试: %v", err)
	}

	user, err := store.CreateUser(ctx, auth.CreateUserParams{
		Email:        email,
		PasswordHash: "hash-for-test",
		Role:         "user",
	})
	if err != nil {
		t.Fatalf("CreateUser returned error: %v", err)
	}
	t.Cleanup(func() {
		_, _ = db.ExecContext(ctx, "DELETE FROM user_read_history WHERE user_id = ?", user.ID)
		_, _ = db.ExecContext(ctx, "DELETE FROM user_account WHERE id = ?", user.ID)
	})

	if err := store.RecordReadHistory(ctx, user.ID, &eventID, nil); err != nil {
		t.Fatalf("RecordReadHistory(event) returned error: %v", err)
	}
	if err := store.RecordReadHistory(ctx, user.ID, nil, &infoID); err != nil {
		t.Fatalf("RecordReadHistory(info) returned error: %v", err)
	}

	items, err := store.ListReadHistory(ctx, user.ID, 20)
	if err != nil {
		t.Fatalf("ListReadHistory returned error: %v", err)
	}
	if len(items) != 2 {
		t.Fatalf("history size = %d, want 2", len(items))
	}
	if items[0].ItemType != "info" || items[0].InfoID == nil || *items[0].InfoID != infoID {
		t.Fatalf("first history item = %+v", items[0])
	}
	if items[1].ItemType != "event" || items[1].EventID == nil || *items[1].EventID != eventID {
		t.Fatalf("second history item = %+v", items[1])
	}
}
