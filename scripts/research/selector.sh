#!/usr/bin/env bash
set -euo pipefail
task_root=/mnt/d/codex/coin
task_python=/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python
case "${1:-status}" in
  status)
    if [[ -f "$task_root/state/selector_progress.json" ]]; then cat "$task_root/state/selector_progress.json"; else echo '{"status":"NOT_STARTED"}'; fi
    ;;
  start|resume)
    if systemctl --user is-active --quiet coin-selector-v1.service; then echo 'Selector process is already active; keeping it.'; exit 0; fi
    systemd-run --user --collect --unit=coin-selector-v1 --slice=coin-research.slice -p MemorySwapMax=0 \
      "$task_root/scripts/with_task_progress.sh" --title 'Selector v1 · independent local DAG · no LLM calls' -- \
      env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH="$task_root/src:$task_root" \
      "$task_python" -B "$task_root/scripts/research/run_selector_research.py" --config configs/selector_v1.yaml
    ;;
  logs) journalctl --user -u coin-selector-v1 --no-pager -n 40 ;;
  *) echo 'Use start | resume | status | logs' >&2; exit 2 ;;
esac
