#!/usr/bin/env bash
set -euo pipefail
QUANT_ROOT=/mnt/d/codex/coin
export QUANT_ROOT
export QUANT_STATE=/home/xflops/coin-state
export UV_CACHE_DIR="$QUANT_ROOT/.cache/uv"
export XDG_CACHE_HOME="$QUANT_ROOT/.cache/xdg"
export XDG_CONFIG_HOME="$QUANT_ROOT/.cache/config"
export TMPDIR="$QUANT_ROOT/.cache/tmp"
export UV_PYTHON_DOWNLOADS=never
export UV_LINK_MODE=copy
export PYTHONPYCACHEPREFIX="$QUANT_ROOT/.cache/pycache"
export PYTHONPATH="$QUANT_ROOT/src"
export TZ=UTC
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
export POLARS_MAX_THREADS=4
export PATH="$QUANT_ROOT/.tools/bin:$PATH"
cd "$QUANT_ROOT"

