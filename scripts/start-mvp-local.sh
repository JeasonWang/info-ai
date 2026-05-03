#!/usr/bin/env bash
set -euo pipefail

# 一键启动 info-mvp 本地开发环境（H5 模式）
# 依赖：已启动的 info-serve（8080）和 MySQL

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs/local"
mkdir -p "$LOG_DIR"

INFO_MVP_PORT="${INFO_MVP_PORT:-5175}"
INFO_SERVE_PORT="${INFO_SERVE_PORT:-8080}"

log_step() {
  echo
  echo "==> $1"
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
    exit 1
  fi
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
require_command npm
require_command curl

log_step "检查端口"
check_port_free "$INFO_MVP_PORT" "info-mvp"

log_step "检查后端"
if ! curl -fsS "http://127.0.0.1:${INFO_SERVE_PORT}/health" >/dev/null 2>&1; then
  echo "警告: info-serve 未在 ${INFO_SERVE_PORT} 端口运行，请先启动后端服务。" >&2
fi

log_step "启动 info-mvp"
(
  cd "$ROOT_DIR/info-mvp"
  exec npm run dev:h5 -- --port "$INFO_MVP_PORT"
) >"$LOG_DIR/info-mvp.log" 2>&1 &

echo "$!" >"$LOG_DIR/info-mvp.pid"
echo "info-mvp 已启动，PID: $!，日志: $LOG_DIR/info-mvp.log"

log_step "等待服务就绪"
wait_for_url "http://127.0.0.1:${INFO_MVP_PORT}/" "info-mvp"

cat <<EOF

info-mvp 本地开发环境启动完成。

用户端(H5): http://localhost:${INFO_MVP_PORT}
业务 API:   http://localhost:${INFO_SERVE_PORT}

日志目录: $LOG_DIR
关闭服务: kill \$(cat $LOG_DIR/info-mvp.pid)
EOF
