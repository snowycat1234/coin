#!/usr/bin/env bash
# Reuse the published conservative recovery guard, no altered financial limits.
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
state="${COIN_CPD_STATE:-/workspace/slow-momentum-state}"
python_bin="${COIN_CPD_PYTHON:-/workspace/coin/.venv/bin/python}"
[[ "$repo" == /workspace/* && "$state" == /workspace/* ]] || exit 2
[[ "$(wc -l < /proc/swaps)" -eq 1 ]] || exit 2
[[ "$(df --output=avail -B1 /workspace | tail -1)" -ge 16106127360 ]] || { echo '15GiB disk reserve required' >&2; exit 2; }
mkdir -p "$state/source" "$state/receipts"
guard="$state/source/bounded_cloud.py"
if [[ ! -f "$guard" ]]; then
  unzip -p "$repo/research/workspace-recovery-20261011/SOURCE_RECOVERY.zip" state/bounded_cloud.py > "$guard"
fi
echo "99432c34f2b7e6411ec9b68e5370deded6d1a94e6ff08d71e22e4a1164df914e  $guard" | sha256sum -c -
export PYTHONPATH="$repo/src:$repo" PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 POLARS_MAX_THREADS=1
cpu="$(awk '/Cpus_allowed_list:/ {print $2}' /proc/self/status | cut -d- -f1 | cut -d, -f1)"
cd "$repo"
exec taskset -c "$cpu" prlimit --as=4000000000 --cpu=1200 "$python_bin" "$guard" \
  --report "$state/receipts/$(date -u +%Y%m%dT%H%M%S)-$$.json" -- "$@"
