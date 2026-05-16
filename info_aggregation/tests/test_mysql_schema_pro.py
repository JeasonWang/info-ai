from pathlib import Path


MYSQL8_INIT_PATH = Path(__file__).resolve().parents[1] / "sql" / "mysql8_init.sql"


def test_pro_mysql_schema_contains_core_tables_and_comments():
    schema = MYSQL8_INIT_PATH.read_text(encoding="utf-8")
    lowered = schema.lower()

    required_tables = [
        "category",
        "channel",
        "info",
        "event",
        "event_item_link",
        "event_timeline_entry",
        "event_summary_snapshot",
        "event_analysis_run",
        "event_analysis_source",
        "event_fact_snapshot",
        "event_analysis_snapshot",
        "event_timeline_analysis",
        "event_evolution",
        "llm_model_config",
        "llm_call_log",
        "user_account",
        "user_session",
        "user_favorite_event",
        "user_preference",
        "admin_audit_log",
        "crawl_task",
        "crawl_run_log",
        "data_quality_snapshot",
        "rebuild_checkpoint",
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
    schema = MYSQL8_INIT_PATH.read_text(encoding="utf-8").lower()

    assert "engine=innodb" in schema
    assert "default charset=utf8mb4" in schema
    assert "collate=utf8mb4_unicode_ci" in schema


def test_max_mysql_migration_contains_initial_data_and_tasks():
    migration = MYSQL8_INIT_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS `category`" in migration
    assert "INSERT INTO `category`" in migration
    assert "INSERT INTO `channel`" in migration
    assert "INSERT INTO `crawl_task`" in migration
    assert "CONCAT('crawl_', ch.`code`)" in migration
    assert "CONCAT(ch.`code`, '_interval_crawl')" not in migration
    assert "admin@info-daren.local" in migration
    assert "Admin123456" in migration
    assert "llm_model_config" in migration
    assert "qwen2.5-14b-instruct" in migration
    assert "deepseek-chat" in migration
    assert "'status', 'sample'" in migration
    assert "sample_weibo_sub" in migration
    assert "2.0_sample_signature" in migration
    assert "ON DUPLICATE KEY UPDATE" in migration

    for channel_code in [
        "weibo",
        "toutiao",
        "xiaohongshu",
        "zhihu",
        "eastmoney",
        "reuters",
        "csdn",
        "juejin",
        "cnblogs",
        "36kr",
        "cctv_sports",
        "sina_sports",
    ]:
        assert f"'{channel_code}'" in migration


def test_mysql_schema_matches_orm_unique_constraints():
    migration = MYSQL8_INIT_PATH.read_text(encoding="utf-8")

    assert "UNIQUE KEY `uk_event_key` (`event_key`)" in migration
    assert "UNIQUE KEY `uq_event_analysis_source_run_info` (`run_id`,`info_id`)" in migration
