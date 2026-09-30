#!/usr/bin/env bash
source /mnt/d/codex/coin/scripts/env.sh
bash scripts/bounded.sh .venv/bin/ruff check src tests
bash scripts/bounded.sh .venv/bin/pytest -q
bash scripts/bounded.sh .venv/bin/python -m quant.disk
bash scripts/bounded.sh .venv/bin/python -m quant.resources

