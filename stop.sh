#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname "$0")/scripts/common.sh"

stopped=0

if is_running; then
  pid="$(cat "$PID_FILE")"
  echo "停止服务 (PID $pid) ..."
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    if ! kill -0 "$pid" 2>/dev/null; then
      stopped=1
      break
    fi
    sleep 0.3
  done
  if [[ "$stopped" -eq 0 ]]; then
    echo "进程未退出，发送 SIGKILL ..."
    kill -9 "$pid" 2>/dev/null || true
    stopped=1
  fi
  rm -f "$PID_FILE"
fi

# 兼容旧方式前台启动、或未写入 PID 的占用
remaining="$(port_pids | tr '\n' ' ')"
if [[ -n "${remaining// }" ]]; then
  echo "清理占用端口 ${PORT} 的进程: $remaining"
  # shellcheck disable=SC2086
  kill $remaining 2>/dev/null || true
  sleep 0.3
  # shellcheck disable=SC2086
  kill -9 $remaining 2>/dev/null || true
  stopped=1
fi

if [[ "$stopped" -eq 1 ]]; then
  echo "服务已停止"
else
  echo "未发现运行中的服务（端口 ${PORT}）"
fi
