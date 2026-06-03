#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "重启服务 ..."
"$ROOT/stop.sh" || true
sleep 1
exec "$ROOT/start.sh" "$@"
