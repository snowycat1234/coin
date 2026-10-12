#!/usr/bin/env bash
set -euo pipefail
task_mode="${1:-restore}"
task_state="${2:-/workspace/calendar-weekday-reproduction}"
[[ "$task_mode" == restore || "$task_mode" == score ]] || exit 2
task_root="$(cd "$(dirname "$0")/../.." && pwd)"
task_python="${COIN_CPD_PYTHON:-/workspace/coin/.venv/bin/python}"
export COIN_CPD_STATE="${task_state}-guard" QUANT_ROOT="$task_root" QUANT_STATE="${task_state}-guard"
cd "$task_root"
bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/calendar-weekday-mean-20261012/persist.py restore --state "$task_state" --artifact-commit 8382b27b709baf52a730ff149cac689132cc1438
if [[ "$task_mode" == score ]]; then
 bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/calendar-weekday-mean-20261012/run.py score --state "$task_state/RECOMPUTED" --prepared "$task_state/INPUTS" --model "$task_state/MODEL/MODEL.json" --source-commit "$(git rev-parse HEAD)"
fi
