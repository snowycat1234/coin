#!/usr/bin/env bash
set -euo pipefail
source /mnt/d/codex/coin/scripts/env.sh
exec bash scripts/bounded.sh .venv/bin/python -u -m quant.collector_public_v3 --run "$@"
