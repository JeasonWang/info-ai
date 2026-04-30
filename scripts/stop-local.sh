#!/usr/bin/env bash
set -euo pipefail

# 一键关闭本地四个服务。
# 本脚本不停止 MySQL，不操作 Docker。

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs/local"

SERVICES=(
  "info-admin"
  "info-max"
  "info-serve"
  "info_aggregation"
)

PORTS=(
  "5174:管理端"
  "5173:用户端"
  "8080:业务 API"
  "8000:采集 API"
)

stop_by_pid_file() {
  local name="$1"
  local pid_file="$LOG_DIR/$name.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "$name: 未找到 PID 文件，跳过。"
    return
  fi

  local pid
  pid="$(tr -d '[:space:]' <"$pid_file")"
  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    echo "$name: PID 文件为空，已清理。"
    return
  fi

  if kill -0 "$pid" 2>/dev/null; then
    echo "$name: 关闭 PID $pid"
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "$name: 强制关闭 PID $pid"
      kill -9 "$pid" 2>/dev/null || true
    fi
  else
    echo "$name: PID $pid 已不在运行。"
  fi

  rm -f "$pid_file"
}

cleanup_port() {
  local spec="$1"
  local port="${spec%%:*}"
  local name="${spec#*:}"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    echo "$name: 端口 $port 无监听。"
    return
  fi

  echo "$name: 清理端口 $port 残留进程 PID: $pids"
  kill $pids 2>/dev/null || true
}

mkdir -p "$LOG_DIR"

for service in "${SERVICES[@]}"; do
  stop_by_pid_file "$service"
done

for port in "${PORTS[@]}"; do
  cleanup_port "$port"
done

echo "本地四个服务已关闭。MySQL 未处理。"
