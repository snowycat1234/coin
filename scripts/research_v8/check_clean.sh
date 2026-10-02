#!/usr/bin/env bash
# Local CI gate inside the D-hosted WSL; no GitHub runner or paid service setup.
set -euo pipefail
coin_env="$1"
coin_test_dir="$2"
coin_report="$3"
[[ "$coin_env" == /home/xflops/coin-state/* ]]
[[ "$coin_test_dir" == /home/xflops/coin-state/* ]]
[[ "$coin_report" == reports/fast_research/V8_* ]]
test -f scripts/research_v8/labels_v2.py
test -f tests/test_v8_label_contract_v2.py
test ! -e "$coin_test_dir"
test ! -e "$coin_report"
# The dependency environment was installed in an exclusive directory via uv sync
# --frozen; the separate smoke receipt proves imports never fall back to .venv.
exec "$coin_env/bin/python" -m pytest \
  tests/test_v8_experiment_registry.py tests/test_v8_label_contract.py \
  tests/test_v8_label_contract_v2.py \
  --basetemp="$coin_test_dir" --junitxml="$coin_report" -q
