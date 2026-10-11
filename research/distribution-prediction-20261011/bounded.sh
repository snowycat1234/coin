#!/usr/bin/env bash
set -euo pipefail
# Cloud-only execution adapter; authorized separately from the WSL installation.
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export NUMEXPR_NUM_THREADS=4 CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export XDG_CACHE_HOME=/workspace/distribution-state/cache
mkdir -p /workspace/distribution-state/cache
available=$(df -B1 --output=avail /workspace | tail -1 | tr -d ' ')
(( available >= 15000000000 )) || { echo 'Less than 15 GB reserve' >&2; exit 1; }
exec timeout --signal=TERM --kill-after=15s 1800s prlimit --as=7500000000 -- "$@"
