"""SQLite 到 MySQL 的 Pro 版本迁移脚本。

该脚本负责把 Plus 阶段 SQLite 中的采集内容、事件流和摘要数据迁移到
Pro 阶段 MySQL。用户账号、会话、管理审计等 Pro 新增表不从 SQLite 迁移。
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pymysql


MIGRATION_TABLE_ORDER = [
    "category",
    "channel",
    "info",
    "info_acquisition_log",
    "event",
    "event_item_link",
    "event_timeline_entry",
    "event_summary_snapshot",
]

PRO_TABLE_ORDER = [
    *MIGRATION_TABLE_ORDER,
    "user_account",
    "user_session",
    "user_favorite_event",
    "user_preference",
    "user_read_history",
    "admin_audit_log",
    "crawl_task",
    "crawl_run_log",
    "data_quality_snapshot",
]

FK_FILTERS = {
    "info_acquisition_log": {"info_id": "info"},
    "event_item_link": {"event_id": "event", "item_id": "info"},
    "event_timeline_entry": {"event_id": "event", "source_item_id": "info"},
    "event_summary_snapshot": {"event_id": "event"},
}

DATETIME_COLUMNS = {
    "created_at",
    "updated_at",
    "event_time",
    "detail_fetched_at",
    "started_at",
    "last_updated_at",
    "occurred_at",
}


def normalize_datetime(value: Any) -> str | None:
    """把 SQLite 常见时间值归一化为 MySQL DATETIME 字符串。"""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str):
        normalized = value.replace("T", " ").split(".")[0].strip()
        if len(normalized) >= 19:
            return normalized[:19]
    return str(value)


def build_insert_sql(table_name: str, columns: list[str]) -> str:
    """生成 MySQL 批量插入兼容的 UPSERT 语句。"""
    quoted_columns = ", ".join(f"`{column}`" for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    updatable_columns = [column for column in columns if column != "id"]
    update_clause = ", ".join(
        f"`{column}` = VALUES(`{column}`)" for column in updatable_columns
    )
    return (
        f"INSERT INTO `{table_name}` ({quoted_columns}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_clause}"
    )


def get_sqlite_columns(sqlite_conn: sqlite3.Connection, table_name: str) -> list[str]:
    """读取 SQLite 表字段，保证迁移脚本跟随当前表结构。"""
    cursor = sqlite_conn.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def normalize_row(columns: list[str], row: sqlite3.Row) -> tuple[Any, ...]:
    """根据字段类型清洗一行数据。"""
    values = []
    for column in columns:
        value = row[column]
        if column in DATETIME_COLUMNS:
            values.append(normalize_datetime(value))
        else:
            values.append(value)
    return tuple(values)


def iter_rows(
    sqlite_conn: sqlite3.Connection,
    table_name: str,
    columns: list[str],
    batch_size: int,
) -> Iterable[list[tuple[Any, ...]]]:
    """按批次读取 SQLite 数据，避免一次性加载过多内容。"""
    cursor = sqlite_conn.execute(f"SELECT {', '.join(columns)} FROM {table_name}")
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        yield [normalize_row(columns, row) for row in rows]


def fetch_existing_ids(mysql_conn, table_name: str) -> set[int]:
    """读取 MySQL 中指定表已有 ID，用于过滤历史脏外键。"""
    with mysql_conn.cursor() as cursor:
        cursor.execute(f"SELECT `id` FROM `{table_name}`")
        return {int(row[0]) for row in cursor.fetchall()}


def filter_rows_by_fk(
    columns: list[str],
    rows: list[tuple[Any, ...]],
    valid_id_sets: dict[str, set[int]],
) -> list[tuple[Any, ...]]:
    """过滤引用不存在父记录的行，避免历史重复数据打断迁移。"""
    column_indexes = {column: index for index, column in enumerate(columns)}
    filtered_rows = []
    for row in rows:
        keep_row = True
        for column, valid_ids in valid_id_sets.items():
            if column not in column_indexes:
                continue
            value = row[column_indexes[column]]
            if value is not None and int(value) not in valid_ids:
                keep_row = False
                break
        if keep_row:
            filtered_rows.append(row)
    return filtered_rows


def table_exists(sqlite_conn: sqlite3.Connection, table_name: str) -> bool:
    """判断 SQLite 中是否存在指定表。"""
    row = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def iter_sql_statements(schema: str) -> Iterable[str]:
    """按 SQL 字符串边界切分语句，避免 Cookie 等文本里的分号打断执行。"""
    buffer: list[str] = []
    quote: str | None = None
    escaped = False

    for char in schema:
        buffer.append(char)

        if quote is not None:
            if quote in {"'", '"'} and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = None
            escaped = False
            continue

        if char in {"'", '"', "`"}:
            quote = char
            continue

        if char == ";":
            statement = "".join(buffer[:-1]).strip()
            if statement:
                yield statement
            buffer = []

    statement = "".join(buffer).strip()
    if statement:
        yield statement


def execute_schema(mysql_conn, schema_path: Path) -> None:
    """执行 MySQL 建表脚本。"""
    schema = schema_path.read_text(encoding="utf-8")
    with mysql_conn.cursor() as cursor:
        for sql in iter_sql_statements(schema):
            cursor.execute(sql)
    mysql_conn.commit()


def reset_target_database(mysql_conn) -> None:
    """清空 Pro 目标库数据，方便迁移脚本安全重跑。"""
    with mysql_conn.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table_name in reversed(PRO_TABLE_ORDER):
            cursor.execute(f"TRUNCATE TABLE `{table_name}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    mysql_conn.commit()


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    mysql_conn,
    table_name: str,
    batch_size: int,
) -> int:
    """迁移单张表，返回迁移行数。"""
    if not table_exists(sqlite_conn, table_name):
        return 0

    columns = get_sqlite_columns(sqlite_conn, table_name)
    insert_sql = build_insert_sql(table_name, columns)
    migrated_count = 0
    fk_filters = {
        fk_column: fetch_existing_ids(mysql_conn, parent_table)
        for fk_column, parent_table in FK_FILTERS.get(table_name, {}).items()
    }

    with mysql_conn.cursor() as cursor:
        for batch in iter_rows(sqlite_conn, table_name, columns, batch_size):
            if fk_filters:
                batch = filter_rows_by_fk(columns, batch, fk_filters)
            if not batch:
                continue
            cursor.executemany(insert_sql, batch)
            migrated_count += len(batch)
    mysql_conn.commit()
    return migrated_count


def migrate(
    sqlite_path: Path,
    mysql_dsn: dict[str, Any],
    schema_path: Path,
    batch_size: int,
    reset_target: bool = False,
) -> dict[str, int]:
    """执行完整迁移并返回每张表迁移数量。"""
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    mysql_connection_args = build_mysql_connection_args(mysql_dsn)
    mysql_connection_args.pop("target_database", None)
    mysql_conn = pymysql.connect(**mysql_connection_args)
    try:
        execute_schema(mysql_conn, schema_path)
        if reset_target:
            reset_target_database(mysql_conn)
        result = {}
        for table_name in MIGRATION_TABLE_ORDER:
            result[table_name] = migrate_table(sqlite_conn, mysql_conn, table_name, batch_size)
        return result
    finally:
        sqlite_conn.close()
        mysql_conn.close()


def build_mysql_connection_args(mysql_dsn: dict[str, Any]) -> dict[str, Any]:
    """首次连接 MySQL 时不指定 database，避免目标库尚未创建导致连接失败。"""
    connection_args = dict(mysql_dsn)
    connection_args["target_database"] = connection_args.get("database")
    connection_args["database"] = None
    return connection_args


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="迁移信息达人 SQLite 数据到 Pro MySQL")
    parser.add_argument("--sqlite-path", required=True, help="SQLite 数据库文件路径")
    parser.add_argument("--mysql-host", default="localhost", help="MySQL 主机")
    parser.add_argument("--mysql-port", type=int, default=3306, help="MySQL 端口")
    parser.add_argument("--mysql-user", default="root", help="MySQL 用户")
    parser.add_argument("--mysql-password", default="root1234", help="MySQL 密码")
    parser.add_argument("--mysql-db", default="info-max", help="MySQL 数据库名")
    parser.add_argument(
        "--schema-path",
        default=str(Path(__file__).with_name("mysql8_init.sql")),
        help="MySQL 8 初始化脚本路径",
    )
    parser.add_argument("--batch-size", type=int, default=500, help="每批迁移数量")
    parser.add_argument("--reset-target", action="store_true", help="迁移前清空目标库数据，适合本地完整重跑")
    return parser.parse_args()


def main() -> None:
    """命令行入口。"""
    args = parse_args()
    result = migrate(
        sqlite_path=Path(args.sqlite_path),
        mysql_dsn={
            "host": args.mysql_host,
            "port": args.mysql_port,
            "user": args.mysql_user,
            "password": args.mysql_password,
            "database": args.mysql_db,
            "charset": "utf8mb4",
            "autocommit": False,
        },
        schema_path=Path(args.schema_path),
        batch_size=args.batch_size,
        reset_target=args.reset_target,
    )
    for table_name, count in result.items():
        print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
