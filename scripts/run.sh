#!/usr/bin/env bash
source /mnt/d/codex/coin/scripts/env.sh
exec bash scripts/bounded.sh .venv/bin/python -m quant "$@"

