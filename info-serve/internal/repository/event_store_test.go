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

func TestBuildEventWhereUsesRequestedPublicStatus(t *testing.T) {
	whereSQL, args := buildEventWhere(events.ListEventsParams{Status: "monitoring", CategoryCode: "tech"})

	if !strings.Contains(whereSQL, "e.status = ?") {
		t.Fatalf("where sql missing status filter: %s", whereSQL)
	}
	if len(args) < 1 || args[0] != "monitoring" {
		t.Fatalf("args = %+v, want first arg monitoring", args)
	}
}

func TestBuildEventWhereShieldsActiveFeedFromWeakQualityRows(t *testing.T) {
	whereSQL, args := buildEventWhere(events.ListEventsParams{Status: "active", CategoryCode: "all"})

	for _, expected := range []string{
		"e.display_quality_level",
		"mixed_unrelated_sources",
		"missing_usable_source",
		"missing_complete_source",
		"CHAR_LENGTH",
		"one_line_summary",
		"全家都爱",
		"已出现相关信息",
		"上头条",
		"social_channel",
		"nonsocial_channel",
	} {
		if !strings.Contains(whereSQL, expected) {
			t.Fatalf("where sql missing %q guard: %s", expected, whereSQL)
		}
	}
	if len(args) < 1 || args[0] != "active" {
		t.Fatalf("args = %+v, want first arg active", args)
	}
}

func TestBuildEventOrderPrioritizesPublicEventsOnAllFeed(t *testing.T) {
	orderSQL := buildEventOrder(events.ListEventsParams{CategoryCode: "all", Sort: "composite"})

	for _, expected := range []string{
		"CASE c.code",
		"WHEN 'international' THEN 0",
		"WHEN 'hot' THEN 1",
		"WHEN 'tech' THEN 4",
		"e.source_count DESC",
		"e.display_quality_score",
	} {
		if !strings.Contains(orderSQL, expected) {
			t.Fatalf("order sql missing %q: %s", expected, orderSQL)
		}
	}
}

func TestBuildEventOrderLatestUsesRecency(t *testing.T) {
	orderSQL := buildEventOrder(events.ListEventsParams{CategoryCode: "all", Sort: "latest"})

	if !strings.HasPrefix(orderSQL, "ORDER BY e.last_updated_at DESC") {
		t.Fatalf("latest order sql = %s", orderSQL)
	}
}
