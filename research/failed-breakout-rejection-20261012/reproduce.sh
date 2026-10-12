#!/usr/bin/env bash
set -euo pipefail
task_mode="${1:-restore}"
task_state="${2:-/workspace/rejected-break-reproduction}"
[[ "$task_mode" == restore || "$task_mode" == score ]] || exit 2
task_root="$(cd "$(dirname "$0")/../.." && pwd)"
task_python="${COIN_CPD_PYTHON:-/workspace/coin/.venv/bin/python}"
export COIN_CPD_STATE="${task_state}-guard" QUANT_ROOT="$task_root" QUANT_STATE="${task_state}-guard"
cd "$task_root"
bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/failed-breakout-rejection-20261012/persist.py restore --state "$task_state" --artifact-commit 16e7784dc77537eab7975bd15cc22cac8de335be
if [[ "$task_mode" == score ]]; then
 bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/failed-breakout-rejection-20261012/driver.py run --state "$task_state/RECOMPUTED" --prepared "$task_state/TARGETS" --source-commit "$(git rev-parse HEAD)"
fi
