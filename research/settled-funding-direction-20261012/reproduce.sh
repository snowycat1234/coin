#!/usr/bin/env bash
set -euo pipefail
task_mode="${1:-restore}"
task_state="${2:-/workspace/funding-reproduction}"
[[ "$task_mode" == restore || "$task_mode" == score ]] || exit 2
task_root="$(cd "$(dirname "$0")/../.." && pwd)"
task_python="${COIN_CPD_PYTHON:-/workspace/coin/.venv/bin/python}"
export COIN_CPD_STATE="${task_state}-guard" QUANT_ROOT="$task_root" QUANT_STATE="${task_state}-guard"
cd "$task_root"
bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/settled-funding-direction-20261012/persist.py restore --state "$task_state" --artifact-commit 5fc36717dbb3357a7989c4f93a123b1a089079b8
if [[ "$task_mode" == score ]]; then
 bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/settled-funding-direction-20261012/run.py --state "$task_state/RECOMPUTED" --prepared "$task_state/INPUTS" --source-commit "$(git rev-parse HEAD)"
fi
