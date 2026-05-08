package repository

import (
	"context"
	"database/sql"
	"os"
	"strings"
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

func TestCompactArticleTextPreservesReadableParagraphs(t *testing.T) {
	input := "标题 。 作者 。 2026-05-08 83 阅读10分钟 。 第一段内容介绍事件背景。 第二段内容分析影响。 第三段内容给出后续观察。"

	result := compactArticleText(input, 2000)

	if !strings.Contains(result, "第一段内容介绍事件背景。\n\n第二段内容分析影响。") {
		t.Fatalf("article text was not paragraph formatted: %q", result)
	}
	if strings.Contains(result, "标题 。") {
		t.Fatalf("punctuation spacing was not normalized: %q", result)
	}
}
