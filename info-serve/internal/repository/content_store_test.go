package repository

import (
	"context"
	"database/sql"
	"os"
	"testing"

	_ "github.com/go-sql-driver/mysql"

	"info-serve/internal/content"
)

func TestMySQLStoreGetsMigratedContentData(t *testing.T) {
	dsn := os.Getenv("INFO_SERVE_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Skip("INFO_SERVE_TEST_MYSQL_DSN 未设置，跳过真实 MySQL 集成测试")
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatalf("open mysql: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })
	store := NewContentMySQLStore(db)

	categories, err := store.ListCategories(context.Background())
	if err != nil {
		t.Fatalf("ListCategories returned error: %v", err)
	}
	if len(categories) == 0 {
		t.Fatal("expected migrated categories")
	}

	channels, err := store.ListChannels(context.Background(), categories[0].ID)
	if err != nil {
		t.Fatalf("ListChannels returned error: %v", err)
	}
	if len(channels) == 0 {
		t.Fatal("expected migrated channels")
	}

	stats, err := store.GetStats(context.Background())
	if err != nil {
		t.Fatalf("GetStats returned error: %v", err)
	}
	if stats.Total == 0 {
		t.Fatal("expected migrated info count")
	}

	page, err := store.ListInfos(context.Background(), content.ListInfoParams{Page: 1, PageSize: 1})
	if err != nil {
		t.Fatalf("ListInfos returned error: %v", err)
	}
	if len(page.Items) == 0 {
		t.Fatal("expected migrated info list")
	}
}
