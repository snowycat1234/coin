#!/usr/bin/env bash
set -euo pipefail
task_state="${1:-/workspace/jump-risk-reproduction}"
task_root="$(cd "$(dirname "$0")/../.." && pwd)"
task_python="${COIN_CPD_PYTHON:-/workspace/coin/.venv/bin/python}"
export COIN_CPD_STATE="${task_state}-guard" QUANT_ROOT="$task_root" QUANT_STATE="${task_state}-guard"
cd "$task_root"
task_artifact=f46229d072d82ad63553dc163d943d04e7b8f439
if ! git cat-file -e "${task_artifact}^{commit}" 2>/dev/null; then git fetch --filter=blob:none --depth=1 origin "$task_artifact"; fi
bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/jump-share-risk-20261012/cold.py --state "$task_state" --artifact-commit "$task_artifact"
