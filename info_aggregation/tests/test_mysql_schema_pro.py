from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "mysql_schema_pro.sql"


def test_pro_mysql_schema_contains_core_tables_and_comments():
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    lowered = schema.lower()

    required_tables = [
        "category",
        "channel",
        "info",
        "event",
        "event_item_link",
        "event_timeline_entry",
        "event_summary_snapshot",
        "user_account",
        "user_session",
        "user_favorite_event",
        "user_follow_keyword",
        "user_preference",
        "admin_audit_log",
        "crawl_task",
        "crawl_run_log",
        "crawl_health_snapshot",
        "data_quality_snapshot",
    ]

    for table_name in required_tables:
        assert f"create table if not exists `{table_name}`" in lowered

    required_comments = [
        "comment '邮箱地址，作为当前阶段的注册和登录账号'",
        "comment '密码哈希，使用 bcrypt 或后续统一密码算法'",
        "comment '管理后台操作审计日志id'",
        "comment '采集任务id'",
        "comment '质量快照id'",
        "comment='用户账号表：保存邮箱注册用户和管理员账号'",
        "comment='采集运行日志表：记录每次采集执行结果'",
    ]

    for comment in required_comments:
        assert comment in lowered


def test_pro_mysql_schema_uses_utf8mb4_and_innodb():
    schema = SCHEMA_PATH.read_text(encoding="utf-8").lower()

    assert "engine=innodb" in schema
    assert "default charset=utf8mb4" in schema
    assert "collate=utf8mb4_unicode_ci" in schema
