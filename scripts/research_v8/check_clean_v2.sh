#!/usr/bin/env bash
# V8 local clean-runtime gate; archived V1 command/output remain unchanged.
set -euo pipefail
coin_env="$1"
coin_test_dir="$2"
coin_report="$3"
[[ "$coin_env" == /home/xflops/coin-state/* ]]
[[ "$coin_test_dir" == /home/xflops/coin-state/* ]]
[[ "$coin_report" == reports/fast_research/V8_* ]]
test -f scripts/research_v8/labels_v3.py
test ! -e "$coin_test_dir"
test ! -e "$coin_report"
exec "$coin_env/bin/python" -m pytest \
  tests/test_v8_experiment_registry.py tests/test_v8_label_contract.py \
  tests/test_v8_label_contract_v2.py tests/test_v8_label_contract_v3.py \
  tests/test_v8_features.py tests/test_v8_features_v2.py \
  --basetemp="$coin_test_dir" -o cache_dir="$coin_test_dir-cache" \
  --junitxml="$coin_report" -q
