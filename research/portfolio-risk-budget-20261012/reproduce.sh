#!/usr/bin/env bash
set -euo pipefail
[[ $# -ge 3 && $# -le 4 ]] || { echo 'Usage: reproduce.sh P1|P2 CS_MATCHED|VOL_MATCHED|STATIC50 /workspace/FRESH_STATE [artifact_commit]' >&2; exit 2; }
case "$1" in P1|P2) ;; *) exit 2 ;; esac
case "$2" in CS_MATCHED|VOL_MATCHED|STATIC50) ;; *) exit 2 ;; esac
task_state="$3"
[[ "$task_state" == /workspace/* && ! -e "$task_state" ]] || { echo 'Fresh /workspace STATE required' >&2; exit 2; }
repo="$(cd "$(dirname "$0")/../.." && pwd)"
artifact="${4:-$(git -C "$repo" rev-parse HEAD)}"
export COIN_CPD_STATE="$task_state" QUANT_ROOT="$repo" QUANT_STATE="$task_state"
exec bash "$repo/research/slow-momentum-cpd-20261011/launch.sh" \
 /workspace/coin/.venv/bin/python "$repo/research/portfolio-risk-budget-20261012/archive.py" restore \
 --window "$1" --arm "$2" --state "$task_state/recovered" --artifact-commit "$artifact"
