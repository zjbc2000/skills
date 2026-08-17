#!/usr/bin/env bash
# start.sh — 一键启动/停止 AE 工作台（API + 前端热重载）
#
# 用法:
#   ./scripts/start.sh start   启动 API（backend.cli.api）+ 前端（vite dev，HMR 热重载）
#   ./scripts/start.sh stop    停止两者
#   ./scripts/start.sh status  查看运行状态
#
# 端口读项目根 .env（API_HOST / API_PORT / WEB_PORT），缺省 127.0.0.1:8000 / 5173。
# 日志落在 var/log/{api,web}.log，pid 落在 var/run/{api,web}.pid。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="$ROOT/var/run"
LOG_DIR="$ROOT/var/log"
API_PID="$RUN_DIR/api.pid"
WEB_PID="$RUN_DIR/web.pid"
ENV_FILE="$ROOT/.env"
mkdir -p "$RUN_DIR" "$LOG_DIR"

# 从根 .env 读端口；已导出的同名环境变量优先
env_val() {
  local key=$1
  if [ -f "$ENV_FILE" ]; then
    grep -E "^$key=" "$ENV_FILE" | head -1 | cut -d= -f2-
  fi
}

API_HOST="${API_HOST:-$(env_val API_HOST)}"; API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-$(env_val API_PORT)}"; API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-$(env_val WEB_PORT)}"; WEB_PORT="${WEB_PORT:-5173}"

is_running() {
  [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null
}

# exec 让 $! 即真实进程（vite / python），stop 时 kill 一次即干净退出
start_one() {
  local name=$1 pidfile=$2 logfile=$3 cmd=$4
  if is_running "$pidfile"; then
    echo "[$name] 已在运行 (pid $(cat "$pidfile"))，跳过"
    return
  fi
  nohup bash -c "$cmd" >>"$LOG_DIR/$logfile" 2>&1 &
  echo $! > "$pidfile"
  echo "[$name] 已启动 (pid $!) · 日志 var/log/$logfile"
}

stop_one() {
  local name=$1 pidfile=$2
  if ! [ -f "$pidfile" ]; then
    echo "[$name] 未在运行"
    return
  fi
  local pid
  pid="$(cat "$pidfile")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 50); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.1
    done
    echo "[$name] 已停止 (pid $pid)"
  else
    echo "[$name] 进程已不在，清理 pidfile"
  fi
  rm -f "$pidfile"
}

wait_health() {
  local host=$1 port=$2
  for _ in $(seq 1 50); do
    if curl -s -o /dev/null "http://$host:$port/health" 2>/dev/null; then
      return 0
    fi
    sleep 0.2
  done
  return 1
}

start_all() {
  start_one "api" "$API_PID" "api.log" \
    "cd \"$ROOT\" && exec python3 -m backend.cli.api"
  start_one "web" "$WEB_PID" "web.log" \
    "cd \"$ROOT/web\" && exec \"$ROOT/web/node_modules/.bin/vite\""

  echo "---"
  if wait_health "$API_HOST" "$API_PORT"; then
    echo "API    http://$API_HOST:$API_PORT （已就绪）"
  else
    echo "API    http://$API_HOST:$API_PORT （未响应 /health，见 var/log/api.log）"
  fi
  echo "前端   http://localhost:$WEB_PORT （vite HMR 热重载）"
}

stop_all() {
  stop_one "web" "$WEB_PID"
  stop_one "api" "$API_PID"
}

status_all() {
  local a w
  if is_running "$API_PID"; then a="运行中 (pid $(cat "$API_PID"))"; else a="已停止"; fi
  if is_running "$WEB_PID"; then w="运行中 (pid $(cat "$WEB_PID"))"; else w="已停止"; fi
  echo "API  $a"
  echo "Web  $w"
}

case "${1:-}" in
  start)  start_all ;;
  stop)   stop_all ;;
  status) status_all ;;
  *) echo "用法: $0 {start|stop|status}" >&2; exit 2 ;;
esac
