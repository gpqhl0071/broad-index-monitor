# 管理脚本公共配置（由 start/stop/restart 引用）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"
PID_FILE="${PID_FILE:-$ROOT/.run/server.pid}"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/server.log}"

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

ensure_venv() {
  cd "$ROOT"
  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi
  # shellcheck source=/dev/null
  source .venv/bin/activate
  pip install -q -r requirements.txt
}

port_pids() {
  lsof -ti ":$PORT" 2>/dev/null || true
}
