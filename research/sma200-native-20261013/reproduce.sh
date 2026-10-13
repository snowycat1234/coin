#!/usr/bin/env bash
# Read-only verification of published original wallets. No account replay.
set -euo pipefail
cd "$(dirname "$0")/../.."
export COIN_CPD_STATE="${SMA_VERIFY_STATE:-/workspace/sma200-verification-state}"
export QUANT_ROOT="$PWD" QUANT_STATE="$COIN_CPD_STATE"
python_bin="${SMA_VERIFY_PYTHON:-/workspace/coin/.venv/bin/python}"
[[ "$COIN_CPD_STATE" != /workspace/sma200-native-state && "$COIN_CPD_STATE" == /workspace/* ]]
mkdir -p "$COIN_CPD_STATE"
bounded() { bash research/slow-momentum-cpd-20261011/launch.sh "$python_bin" "$@"; }
if [[ "${1:-}" == --rebuild-source ]]; then
  # Fresh-machine public Git source recovery, not rerun in this experiment.
  for year in 2023 2025; do
    source_dest="/workspace/follow-native-${year}-public-cold/source_rebuilt"
    [[ ! -e "$source_dest" ]] || { printf '%s\n' "Existing source preserved: $source_dest" >&2; exit 2; }
    mkdir -p "$(dirname "$source_dest")"
    bounded research/rejected-break-follow-native-20261012/cold_source.py "Y$year" "$source_dest" > "$COIN_CPD_STATE/SOURCE_Y${year}.log" 2>&1
  done
fi
for source_index in /workspace/follow-native-2023-public-cold/source_rebuilt/SOURCE_INDEX.json /workspace/follow-native-2025-public-cold/source_rebuilt/source/SOURCE_INDEX.json; do
  [[ -f "$source_index" ]] || { printf '%s\n' 'Verified source caches required; see REPORT.md and --rebuild-source for a fresh machine.' >&2; exit 2; }
done
bounded -m pytest -q research/sma200-native-20261013/test_targets.py --basetemp "$COIN_CPD_STATE/pytest"
bounded research/sma200-native-20261013/archive.py cold --window Y2023 --artifact-commit e9f50eabd8e5135b6a4bb8c1d01c213f565dc827 --output "$COIN_CPD_STATE/Y2023_PUBLIC_RESTORE.json"
bounded research/sma200-native-20261013/archive.py cold --window Y2025 --artifact-commit e79ddb4b7b8566688cf3d21c50f745ccfc3ba642 --output "$COIN_CPD_STATE/Y2025_PUBLIC_RESTORE.json"
bounded research/sma200-native-20261013/compare.py --output "$COIN_CPD_STATE/COMPARISON.json"
