#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
artifact=859876b563fb28ae525bbcc22d75900e2e4ec86c
old=f46229d072d82ad63553dc163d943d04e7b8f439
for commit in "$artifact" "$old"; do
  git -C "$repo" cat-file -e "$commit^{commit}" 2>/dev/null || git -C "$repo" fetch --depth=1 origin "$commit"
done
export COIN_CPD_STATE="${COIN_CPD_STATE:-/workspace/co-tail-reproduce-guard}"
export QUANT_ROOT="$repo" QUANT_STATE="$COIN_CPD_STATE"
exec bash "$repo/research/slow-momentum-cpd-20261011/launch.sh" /workspace/coin/.venv/bin/python "$repo/research/co-tail-risk-20261012/cold.py" --state "${1:-/workspace/co-tail-reproduce-restored}" --artifact-commit "$artifact"
