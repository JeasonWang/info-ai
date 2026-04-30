#!/usr/bin/env bash
set -euo pipefail

# 本地 MySQL 结构迁移脚本。
# 开发阶段使用本机 MySQL 3306；本脚本不启动 MySQL，不操作 Docker。

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-root1234}"
MYSQL_DB="${MYSQL_DB:-info-max}"
MYSQL_CLI="${MYSQL_CLI:-mysql}"

MIGRATIONS=(
  "$ROOT_DIR/docs/数据库/2026-04-29-Max渠道采集间隔配置迁移.sql"
  "$ROOT_DIR/docs/数据库/2026-04-29-Max详情补偿队列迁移.sql"
  "$ROOT_DIR/docs/数据库/2026-04-29-Max采集任务调度版本迁移.sql"
)

if ! command -v "$MYSQL_CLI" >/dev/null 2>&1; then
  echo "错误: 未找到 mysql 客户端。可通过 MYSQL_CLI=/path/to/mysql 指定。" >&2
  exit 1
fi

echo "准备迁移本地 MySQL: ${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}"

for migration in "${MIGRATIONS[@]}"; do
  if [[ ! -f "$migration" ]]; then
    echo "错误: 迁移文件不存在: $migration" >&2
    exit 1
  fi
  echo "执行迁移: ${migration#$ROOT_DIR/}"
  "$MYSQL_CLI" \
    -h"$MYSQL_HOST" \
    -P"$MYSQL_PORT" \
    -u"$MYSQL_USER" \
    -p"$MYSQL_PASSWORD" \
    "$MYSQL_DB" <"$migration"
done

echo "本地 MySQL 迁移完成。"
