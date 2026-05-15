package repository

import (
	"context"
	"database/sql"
	"os"
	"testing"

	_ "github.com/go-sql-driver/mysql"
)

func TestChannelQualityActionAdvicePrioritizesCredentialIssue(t *testing.T) {
	row := map[string]any{
		"real_count":                12,
		"usable_ratio":              35.0,
		"needs_attention_ratio":     80.0,
		"avg_detail_content_length": 90.0,
		"top_failure_reasons":       []map[string]any{{"reason": "anti_crawl_blocked", "count": 5}},
		"credential_health":         map[string]any{"health": "missing_required", "missing_required": []string{"WEIBO_COOKIE"}},
	}

	advice := channelQualityActionAdvice(row)

	if advice["primary_issue"] != "缺少采集凭证" {
		t.Fatalf("primary_issue = %v", advice["primary_issue"])
	}
	if advice["next_action"] != "配置 WEIBO_COOKIE 后重抓低完整详情" {
		t.Fatalf("next_action = %v", advice["next_action"])
	}
}

func TestChannelQualityActionAdviceHandlesEmptyCoreSource(t *testing.T) {
	row := emptyCoreSourceRow("reuters")

	if row["primary_issue"] != "暂无真实采集数据" {
		t.Fatalf("primary_issue = %v", row["primary_issue"])
	}
	if row["next_action"] != "确认核心信源采集任务是否启用" {
		t.Fatalf("next_action = %v", row["next_action"])
	}
}

func TestEventAnalysisActionAdvicePrioritizesWeakSources(t *testing.T) {
	advice := eventAnalysisActionAdvice([]string{"low_confidence", "weak_sources"}, 2)

	if advice["primary_issue"] != "来源质量不足" {
		t.Fatalf("primary_issue = %v", advice["primary_issue"])
	}
	if advice["next_action"] != "先执行详情补偿，再重新分析该事件" {
		t.Fatalf("next_action = %v", advice["next_action"])
	}
}

func TestEventAnalysisIssueReasonsIgnoreMinorWeakTail(t *testing.T) {
	reasons := eventAnalysisIssueReasons(true, "succeeded", "", 98, 0.72, false, 2, 1, "已有完整来源支撑。")

	for _, reason := range reasons {
		if reason == "weak_sources" {
			t.Fatalf("reasons = %+v, want minor weak tail ignored", reasons)
		}
	}
}

func TestEventAnalysisIssueReasonsKeepHighWeakRatioRisk(t *testing.T) {
	reasons := eventAnalysisIssueReasons(true, "succeeded", "", 98, 0.72, false, 6, 5, "已有多平台讨论。")

	found := false
	for _, reason := range reasons {
		if reason == "weak_sources" {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("reasons = %+v, want weak_sources", reasons)
	}
}

func TestDisplayQualityActionAdvicePrioritizesSingleWeakSource(t *testing.T) {
	advice := displayQualityActionAdvice([]string{"single_weak_source", "low_value_content"})

	if advice["primary_issue"] != "单一弱来源" {
		t.Fatalf("primary_issue = %v", advice["primary_issue"])
	}
	if advice["next_action"] != "补充可用事实源后刷新展示质量" {
		t.Fatalf("next_action = %v", advice["next_action"])
	}
}

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

func TestMySQLStoreListsChannelHealth(t *testing.T) {
	dsn := os.Getenv("INFO_SERVE_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Skip("INFO_SERVE_TEST_MYSQL_DSN 未设置，跳过真实 MySQL 集成测试")
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatalf("open mysql: %v", err)
	}
	t.Cleanup(func() { _ = db.Close() })

	items, err := NewMySQLStore(db).ListChannelHealth(context.Background())
	if err != nil {
		t.Fatalf("ListChannelHealth returned error: %v", err)
	}
	if len(items) == 0 {
		t.Fatal("expected channel health items")
	}
	if items[0].ChannelCode == "" {
		t.Fatalf("channel health missing code: %+v", items[0])
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
