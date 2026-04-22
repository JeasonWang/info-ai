package repository

import (
	"context"
	"database/sql"
	"os"
	"testing"

	_ "github.com/go-sql-driver/mysql"
)

func TestMySQLStoreGetsAdminOverviewFromMigratedData(t *testing.T) {
	dsn := os.Getenv("INFO_SERVE_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Skip("INFO_SERVE_TEST_MYSQL_DSN 未设置，跳过真实 MySQL 集成测试")
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatalf("open mysql: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	overview, err := NewMySQLStore(db).GetOverview(context.Background())
	if err != nil {
		t.Fatalf("GetOverview returned error: %v", err)
	}
	if overview.ChannelCount == 0 {
		t.Fatal("expected channel count from migrated data")
	}
	if overview.EventCount == 0 {
		t.Fatal("expected event count from migrated data")
	}
	if overview.InfoCount == 0 {
		t.Fatal("expected info count from migrated data")
	}
}

func TestMySQLStoreListsAdminConfigurationsFromMigratedData(t *testing.T) {
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
	categories, err := store.ListCategories(context.Background())
	if err != nil {
		t.Fatalf("ListCategories returned error: %v", err)
	}
	if len(categories) == 0 || categories[0].Code == "" {
		t.Fatalf("expected migrated categories, got %+v", categories)
	}

	channels, err := store.ListChannels(context.Background())
	if err != nil {
		t.Fatalf("ListChannels returned error: %v", err)
	}
	if len(channels) == 0 || channels[0].CategoryName == "" {
		t.Fatalf("expected migrated channels with category names, got %+v", channels)
	}
}
