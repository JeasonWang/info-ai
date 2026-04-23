#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

start_service() {
  local name="$1"
  local workdir="$2"
  shift 2
  echo "Starting $name ..."
  (
    cd "$workdir"
    "$@"
  ) >"$LOG_DIR/$name.log" 2>&1 &
  echo "$!" >"$LOG_DIR/$name.pid"
}

start_service "info_aggregation" "$ROOT_DIR/info_aggregation" ./.venv/bin/python main.py
start_service "info-serve" "$ROOT_DIR/info-serve" env \
  GOCACHE=/tmp/info-serve-go-build-cache \
  INFO_SERVE_HTTP_ADDR=:18080 \
  INFO_SERVE_MYSQL_DSN='root:root1234@tcp(localhost:3306)/info-max?charset=utf8mb4&parseTime=true&loc=Local' \
  INFO_AGGREGATION_BASE_URL='http://127.0.0.1:8000' \
  go run ./cmd/server
start_service "info-max" "$ROOT_DIR/info-max" env VITE_INFO_SERVE_BASE_URL=http://localhost:18080 npm run dev -- --host 127.0.0.1 --port 5173
start_service "info-admin" "$ROOT_DIR/info-admin" env VITE_INFO_SERVE_BASE_URL=http://localhost:18080 npm run dev -- --host 127.0.0.1 --port 5174

echo "本地服务启动命令已提交，日志位于 $LOG_DIR。"
echo "info-max: http://127.0.0.1:5173/"
echo "info-admin: http://127.0.0.1:5174/"
