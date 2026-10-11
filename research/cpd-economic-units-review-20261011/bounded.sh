#!/usr/bin/env bash
set -euo pipefail
# Independent read-only cloud review adapter; original WSL launcher inaccessible.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export XDG_CACHE_HOME=/workspace/cpd-economic-review-state/cache
mkdir -p "$XDG_CACHE_HOME"
available=$(df -B1 --output=avail /workspace | tail -1 | tr -d ' ')
(( available >= 15000000000 )) || { echo 'Review disk reserve below15GB' >&2; exit 1; }
(( $(wc -l < /proc/swaps) == 1 )) || { echo 'Swap active; stop review' >&2; exit 1; }
exec timeout --signal=TERM --kill-after=5s 120s prlimit --as=4000000000 -- "$@"
