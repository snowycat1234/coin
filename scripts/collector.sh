#!/usr/bin/env bash
# Background lifecycle stays on D. This script does not submit any orders.
source /mnt/d/codex/coin/scripts/env.sh
action="${1:-status}"
pid_file="$QUANT_ROOT/state/collector.pid"
log_file="$QUANT_ROOT/logs/collector.log"

is_our_pid() {
  [[ -f "$pid_file" ]] || return 1
  read -r collector_pid < "$pid_file"
  [[ "$collector_pid" =~ ^[0-9]+$ ]] || return 1
  [[ -r "/proc/$collector_pid/cmdline" ]] || return 1
  tr '\0' ' ' < "/proc/$collector_pid/cmdline" | grep -q 'quant.collector'
}

case "$action" in
  run)
    duration="${2:-}"
    exec bash scripts/bounded.sh .venv/bin/python -c 'import asyncio,json,sys; from quant.collector import collect; print(json.dumps(asyncio.run(collect(float(sys.argv[1]) if sys.argv[1] else None)),indent=2))' "$duration"
    ;;
  start)
    printf 'Use Windows scripts/live.ps1 start to keep the WSL client alive.\n' >&2
    exit 2
    ;;
  stop)
    if is_our_pid; then
      kill -TERM "$collector_pid"
      printf 'Stop signal sent: pid %s\n' "$collector_pid"
    else
      printf 'No active collector owned by this PID file\n'
    fi
    ;;
  status)
    exec bash scripts/bounded.sh .venv/bin/python -c 'import json; from quant.collector import status; print(json.dumps(status(),indent=2,ensure_ascii=False))'
    ;;
  *)
    printf 'Usage: scripts/collector.sh {start|stop|status|run [seconds]}\n' >&2
    exit 2
    ;;
esac
