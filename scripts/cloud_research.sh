#!/usr/bin/env bash
# Authorized cloud-only offline runner; no account, network or resource changes.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
state="${QUANT_STATE:-/workspace/coin-state}"
[[ "$repo" == /workspace/* && "$state" == /workspace/* ]] || exit 2
seconds="${COIN_RUN_SECONDS:-900}"
[[ "$seconds" =~ ^[0-9]+$ && "$seconds" -ge 1 && "$seconds" -le 900 ]] || exit 2
[[ "$(wc -l < /proc/swaps)" -eq 1 ]] || { echo 'Cloud research requires swap0' >&2; exit 2; }
allowed="$(awk '/Cpus_allowed_list:/ {print $2}' /proc/self/status)"
cpu="${allowed%%[-,]*}"
mkdir -p "$state/native-action-progress"
stamp="$(date -u +%Y%m%dT%H%M%S)-$$"
log="$state/native-action-progress/$stamp.log"
export QUANT_ROOT="$repo" QUANT_STATE="$state" PYTHONPATH="$repo/src:$repo"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1 POLARS_MAX_THREADS=1 CUDA_VISIBLE_DEVICES=''
cd "$repo"
start="$(date +%s)"
printf 'started_utc=%s cpu=%s address_space_bytes=6000000000 limit_seconds=%s\n' "$stamp" "$cpu" "$seconds" > "$log"
set +e
taskset -c "$cpu" prlimit --as=6000000000 --cpu="$seconds" \
  timeout --signal=TERM --kill-after=5 "$seconds" "$@" 2>&1 | tee -a "$log"
code="${PIPESTATUS[0]}"
set -e
printf 'exit_code=%s elapsed_seconds=%s\n' "$code" "$(( $(date +%s) - start ))" >> "$log"
exit "$code"
