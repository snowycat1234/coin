#!/usr/bin/env bash
set -euo pipefail
test "$#" -eq 2
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES="" FUNDING_TARGET_OUTER_TIMEOUT_SECONDS=120
exec timeout --signal=TERM --kill-after=5s 120s python "$HERE/run_targets.py" --parent-go "$1" --output "$2"
