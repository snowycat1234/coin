#!/usr/bin/env bash
set -euo pipefail
task_state="${1:-/workspace/mark-trade-reproduction}"
task_root="$(cd "$(dirname "$0")/../.." && pwd)"
task_python="${COIN_CPD_PYTHON:-/workspace/coin/.venv/bin/python}"
export COIN_CPD_STATE="${task_state}-guard" QUANT_ROOT="$task_root" QUANT_STATE="${task_state}-guard"
cd "$task_root"
task_artifact=d0adcbc10e0fe980e3361d3233df44acc7a9888c
if ! git cat-file -e "${task_artifact}^{commit}" 2>/dev/null; then
 git fetch --filter=blob:none --depth=1 origin "$task_artifact"
fi
bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/mark-trade-dislocation-20261012/cold.py --state "$task_state" --artifact-commit "$task_artifact"
