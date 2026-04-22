package repository

import (
	"context"
	"database/sql"
	"os"
	"testing"

	_ "github.com/go-sql-driver/mysql"

	"info-serve/internal/events"
)

func TestMySQLStoreListsMigratedEvents(t *testing.T) {
	dsn := os.Getenv("INFO_SERVE_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Skip("INFO_SERVE_TEST_MYSQL_DSN 未设置，跳过真实 MySQL 集成测试")
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatalf("open mysql: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	page, err := NewMySQLStore(db).ListEvents(context.Background(), events.ListEventsParams{
		CategoryCode: "all",
		Sort:         "composite",
		Page:         1,
		PageSize:     3,
	})
	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	if page.Total == 0 {
		t.Fatal("expected migrated MySQL events to be available")
	}
	if len(page.Items) == 0 {
		t.Fatal("expected at least one event item")
	}
	if page.Items[0].Title == "" {
		t.Fatalf("event item missing title: %+v", page.Items[0])
	}
}

func TestMySQLStoreGetsMigratedEventDetail(t *testing.T) {
	dsn := os.Getenv("INFO_SERVE_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Skip("INFO_SERVE_TEST_MYSQL_DSN 未设置，跳过真实 MySQL 集成测试")
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatalf("open mysql: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	page, err := NewMySQLStore(db).ListEvents(context.Background(), events.ListEventsParams{
		CategoryCode: "all",
		Sort:         "composite",
		Page:         1,
		PageSize:     1,
	})
	if err != nil {
		t.Fatalf("ListEvents returned error: %v", err)
	}
	if len(page.Items) == 0 {
		t.Fatal("expected at least one event")
	}

	detail, err := NewMySQLStore(db).GetEventDetail(context.Background(), page.Items[0].ID)
	if err != nil {
		t.Fatalf("GetEventDetail returned error: %v", err)
	}
	if detail.Event.ID != page.Items[0].ID {
		t.Fatalf("detail id = %d, want %d", detail.Event.ID, page.Items[0].ID)
	}
	if len(detail.RepresentativeSources) == 0 {
		t.Fatal("expected representative sources from migrated links")
	}
}
