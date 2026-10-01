#!/usr/bin/env bash
source /mnt/d/codex/coin/scripts/env.sh
# A foreground WSL client keeps the distribution alive. No project paging to C.
exec bash scripts/bounded.sh systemd-run --user --scope --quiet --slice=coin-quant.slice \
  -p MemoryMax=2147483648 -p MemorySwapMax=0 \
  .venv/bin/python -u -m quant.runtime_v2 "$@"
