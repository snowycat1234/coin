#!/usr/bin/env bash
set -euo pipefail
cd /workspace/coin-tail-risk
task_state=${1:?Provide a NEW recovery directory below /workspace}
export COIN_CPD_STATE=/workspace/expert-structure-state
export QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/expert-structure-state
run() { bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python "$@"; }
run research/high-reference-expert-20261012/archive.py restore --state "$task_state/Y2023" --year Y2023 --artifact-commit 2cae83296340e43605ca64a2347f86b219b1836e
run research/high-reference-expert-20261012/archive.py restore --state "$task_state/Y2025" --year Y2025 --artifact-commit 0a99734a74cf33f26264b4087c811ff33e18c6a8 --reused-source /workspace/portfolio-risk-2025-state/PUBLIC_SOURCE_RECOVERED/source
run research/high-reference-expert-20261012/tail_recovery.py --state "$task_state/Y2025_EXIT" --parent "$task_state/Y2025/account" --artifact-commit 73388947b8c26cf6b08fc3328f6632fda3da980e
