#!/usr/bin/env bash
set -euo pipefail
[[ $# -ge 2 && $# -le 3 ]] || { echo 'Usage: reproduce.sh Y2023|Y2025 /workspace/FRESH_STATE [artifact_commit]' >&2; exit 2; }
case "$1" in Y2023|Y2025) ;; *) exit 2 ;; esac
task_state="$2"
[[ "$task_state" == /workspace/* && ! -e "$task_state" ]] || { echo 'Fresh /workspace STATE required' >&2; exit 2; }
task_root="$(cd "$(dirname "$0")/../.." && pwd)"
task_artifact="${3:-$(git -C "$task_root" rev-parse HEAD)}"
task_python="${COIN_CPD_PYTHON:-/workspace/coin/.venv/bin/python}"
export COIN_CPD_STATE="${task_state}-guard" QUANT_ROOT="$task_root" QUANT_STATE="${task_state}-guard"
cd "$task_root"
exec bash research/slow-momentum-cpd-20261011/launch.sh "$task_python" research/rejected-break-follow-native-20261012/archive.py restore --window "$1" --state "$task_state" --artifact-commit "$task_artifact"
