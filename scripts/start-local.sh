#!/usr/bin/env bash
set -euo pipefail

# 一键启动本地四个服务。
# 注意：本脚本不启动 MySQL、不启动 Docker；默认使用本机 MySQL 3306。

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs/local"
mkdir -p "$LOG_DIR"

MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-root1234}"
MYSQL_DB="${MYSQL_DB:-info-max}"
MYSQL_DSN="${MYSQL_USER}:${MYSQL_PASSWORD}@tcp(${MYSQL_HOST}:${MYSQL_PORT})/${MYSQL_DB}?charset=utf8mb4&parseTime=true&loc=Local"

AGGREGATION_PORT="${AGGREGATION_PORT:-8000}"
INFO_SERVE_PORT="${INFO_SERVE_PORT:-8085}"
INFO_MAX_PORT="${INFO_MAX_PORT:-5173}"
INFO_ADMIN_PORT="${INFO_ADMIN_PORT:-5174}"
INFO_MVP_PORT="${INFO_MVP_PORT:-5175}"

log_step() {
  echo
  echo "==> $1"
}

require_path() {
  local path="$1"
  local message="$2"
  if [[ ! -e "$path" ]]; then
    echo "错误: $message: $path" >&2
    exit 1
  fi
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "错误: 缺少命令 $command_name" >&2
    exit 1
  fi
}

check_port_free() {
  local port="$1"
  local name="$2"
  local pid
  pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pid" ]]; then
    echo "错误: $name 端口 $port 已被占用，PID: $pid" >&2
    echo "请先运行: ./scripts/stop-local.sh" >&2
    exit 1
  fi
}

start_service() {
  local name="$1"
  local workdir="$2"
  shift 2

  log_step "启动 $name"
  (
    cd "$workdir"
    exec "$@"
  ) >"$LOG_DIR/$name.log" 2>&1 &

  echo "$!" >"$LOG_DIR/$name.pid"
  echo "$name 已启动，PID: $!，日志: $LOG_DIR/$name.log"
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local max_wait="${3:-30}"

  for _ in $(seq 1 "$max_wait"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name 就绪: $url"
      return
    fi
    sleep 1
  done
  echo "警告: $name 暂未就绪，请查看日志。" >&2
}

log_step "检查依赖"
require_command lsof
require_command curl
require_command go
require_command npm
require_path "$ROOT_DIR/info_aggregation/.venv/bin/python" "缺少 Python 虚拟环境"
require_path "$ROOT_DIR/info_aggregation/main.py" "缺少采集服务入口"
require_path "$ROOT_DIR/info-serve/go.mod" "缺少 Go 服务模块"
require_path "$ROOT_DIR/info-max/package.json" "缺少用户端项目"
require_path "$ROOT_DIR/info-admin/package.json" "缺少管理端项目"
require_path "$ROOT_DIR/info-mvp/package.json" "缺少h5端项目"

log_step "检查端口"
check_port_free "$AGGREGATION_PORT" "采集 API"
check_port_free "$INFO_SERVE_PORT" "业务 API"
check_port_free "$INFO_MAX_PORT" "用户端"
check_port_free "$INFO_ADMIN_PORT" "管理端"
check_port_free "$INFO_MVP_PORT" "h5端"

start_service "info_aggregation" "$ROOT_DIR/info_aggregation" env \
  APP_ENV=local \
  DB_TYPE=mysql \
  DB_HOST="$MYSQL_HOST" \
  DB_PORT="$MYSQL_PORT" \
  DB_USER="$MYSQL_USER" \
  DB_PASSWORD="$MYSQL_PASSWORD" \
  DB_NAME="$MYSQL_DB" \
  LOG_DIR="$LOG_DIR" \
  ENABLE_SEED_DATA="${ENABLE_SEED_DATA:-false}" \
  API_HOST=127.0.0.1 \
  API_PORT="$AGGREGATION_PORT" \
  ./.venv/bin/python main.py

start_service "info-serve" "$ROOT_DIR/info-serve" env \
  GOCACHE=/tmp/info-serve-go-build-cache \
  INFO_SERVE_HTTP_ADDR=":${INFO_SERVE_PORT}" \
  INFO_SERVE_MYSQL_DSN="$MYSQL_DSN" \
  INFO_SERVE_SESSION_SECRET="${INFO_SERVE_SESSION_SECRET:-info-serve-local-dev-session-secret}" \
  INFO_AGGREGATION_BASE_URL="http://127.0.0.1:${AGGREGATION_PORT}" \
  go run ./cmd/server

start_service "info-max" "$ROOT_DIR/info-max" env \
  VITE_INFO_SERVE_BASE_URL="http://127.0.0.1:${INFO_SERVE_PORT}" \
  npm run dev -- --host 127.0.0.1 --port "$INFO_MAX_PORT"

start_service "info-admin" "$ROOT_DIR/info-admin" env \
  VITE_INFO_SERVE_BASE_URL="http://127.0.0.1:${INFO_SERVE_PORT}" \
  npm run dev -- --host 127.0.0.1 --port "$INFO_ADMIN_PORT"
  
start_service "info-mvp" "$ROOT_DIR/info-mvp" env \
  VITE_INFO_SERVE_BASE_URL="http://127.0.0.1:${INFO_SERVE_PORT}" \
  npm run dev:h5 -- --host 127.0.0.1 --port "$INFO_MVP_PORT"

log_step "等待服务就绪"
wait_for_url "http://127.0.0.1:${AGGREGATION_PORT}/" "采集 API"
wait_for_url "http://127.0.0.1:${INFO_SERVE_PORT}/health" "业务 API"
wait_for_url "http://127.0.0.1:${INFO_MAX_PORT}/" "用户端"
wait_for_url "http://127.0.0.1:${INFO_ADMIN_PORT}/" "管理端"
wait_for_url "http://127.0.0.1:${INFO_MVP_PORT}/" "h5端"

cat <<EOF

本地服务启动完成。

MySQL:   ${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}
采集 API: http://localhost:${AGGREGATION_PORT}
业务 API: http://localhost:${INFO_SERVE_PORT}
用户端:   http://localhost:${INFO_MAX_PORT}
管理端:   http://localhost:${INFO_ADMIN_PORT}
h5端:  http://localhost:${INFO_MVP_PORT}

日志目录: $LOG_DIR
关闭服务: ./scripts/stop-local.sh
EOF
