#!/usr/bin/env bash
# Public historical source + full snapshot verification; zero financial advance.
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
state="${COIN_TERMINAL_STATE:-/workspace/terminal-readiness-2025-reproduce}"
python_bin="${COIN_CPD_PYTHON:-/workspace/coin/.venv/bin/python}"
export COIN_CPD_STATE="$state" QUANT_ROOT="$repo" QUANT_STATE="$state"
[[ "$state" == /workspace/* && ! -e "$state/PUBLIC_COLD" ]]
cd "$repo"
[[ -z "$(git status --porcelain)" ]]
sha256sum -c research/terminal-readiness-2025-20261012/FINANCIAL_SHA256.txt
exec bash research/slow-momentum-cpd-20261011/launch.sh "$python_bin" \
  research/terminal-readiness-2025-20261012/archive.py restore \
  --state "$state/PUBLIC_COLD" \
  --artifact-commit 1c9542ff095c95652781bfe87beded2b4140990e
