#!/usr/bin/env bash
# 启动服务（默认后台）；开发调试可加 -f / --foreground
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname "$0")/scripts/common.sh"

usage() {
  cat <<EOF
用法: ./start.sh [选项]

  （无参数）  后台启动，日志写入 logs/server.log
  -f, --foreground  前台启动（带 --reload，改代码自动重载，Ctrl+C 退出）

环境变量: HOST（默认 127.0.0.1） PORT（默认 8765）
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  -f|--foreground) FOREGROUND=1 ;;
  "") FOREGROUND=0 ;;
  *) echo "未知参数: $1"; usage; exit 1 ;;
esac

ensure_venv

URL="http://${HOST}:${PORT}"

if [[ "$FOREGROUND" -eq 0 ]]; then
  if is_running; then
    echo "服务已在运行 (PID $(cat "$PID_FILE"))"
    echo "访问: $URL"
    exit 0
  fi
  mkdir -p "$(dirname "$PID_FILE")" "$LOG_DIR"
  echo "后台启动: $URL"
  echo "日志: $LOG_FILE"
  nohup uvicorn backend.main:app --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  sleep 0.5
  if is_running; then
    echo "已启动 (PID $(cat "$PID_FILE"))"
  else
    echo "启动失败，请查看日志: $LOG_FILE" >&2
    exit 1
  fi
else
  echo "前台启动（--reload）: $URL"
  echo "按 Ctrl+C 停止"
  exec uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
fi
