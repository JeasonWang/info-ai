from datetime import datetime

from sql import mysql_migration_from_sqlite as migration


def test_migration_table_order_keeps_foreign_key_dependencies_first():
    order = migration.MIGRATION_TABLE_ORDER

    assert order.index("category") < order.index("channel")
    assert order.index("category") < order.index("info")
    assert order.index("channel") < order.index("info")
    assert order.index("event") < order.index("event_item_link")
    assert order.index("info") < order.index("event_item_link")
    assert "user_account" not in order


def test_normalize_datetime_accepts_common_sqlite_values():
    assert migration.normalize_datetime(None) is None
    assert migration.normalize_datetime("") is None
    assert migration.normalize_datetime("2026-04-22 09:12:33") == "2026-04-22 09:12:33"
    assert migration.normalize_datetime("2026-04-22T09:12:33") == "2026-04-22 09:12:33"
    assert migration.normalize_datetime(datetime(2026, 4, 22, 9, 12, 33)) == "2026-04-22 09:12:33"


def test_build_insert_sql_generates_mysql_upsert_statement():
    sql = migration.build_insert_sql("category", ["id", "name", "code"])

    assert sql.startswith("INSERT INTO `category` (`id`, `name`, `code`) VALUES")
    assert "%s, %s, %s" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert "`name` = VALUES(`name`)" in sql
    assert "`code` = VALUES(`code`)" in sql


def test_build_mysql_connection_args_connects_without_database_first():
    args = migration.build_mysql_connection_args(
        {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "root1234",
            "database": "info-max",
            "charset": "utf8mb4",
        }
    )

    assert args["database"] is None
    assert args["target_database"] == "info-max"


def test_filter_rows_by_fk_removes_rows_with_missing_parent_ids():
    columns = ["id", "info_id", "channel_code"]
    rows = [
        (1, 10, "weibo"),
        (2, 99, "weibo"),
        (3, None, "weibo"),
    ]

    filtered = migration.filter_rows_by_fk(columns, rows, {"info_id": {10}})

    assert filtered == [(1, 10, "weibo"), (3, None, "weibo")]
