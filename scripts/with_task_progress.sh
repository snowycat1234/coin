#!/usr/bin/env bash
set -euo pipefail
exec bash /mnt/d/codex/coin/scripts/bounded.sh \
  env PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 \
  /mnt/d/codex/coin/scripts/task_progress_run.py "$@"
