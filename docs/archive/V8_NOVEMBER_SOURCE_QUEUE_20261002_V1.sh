#!/usr/bin/env bash
set -euo pipefail
cd /mnt/d/codex/coin
spec_file=reports/fast_research/V8_NOVEMBER_SOURCE_PREREGISTRATION_20261002_V1.json
for spec in spot:BTCUSDT spot:ETHUSDT perp:BTCUSDT perp:ETHUSDT; do
  IFS=: read -r market symbol <<< "$spec"
  prior="reports/fast_research/V7_MONTHLY_${market^^}_${symbol}_202510_V2.json"
  prior_qa="reports/fast_research/V7_MONTHLY_${market^^}_${symbol}_202510_INDEPENDENT_QA_V2.json"
  fetch=scripts/research_v7/fetch_monthly_v2.py
  if [[ "$spec" == perp:ETHUSDT ]]; then
    prior=reports/fast_research/V7_MONTHLY_PERP_ETHUSDT_202510_RECOVERY_V3.json
    prior_qa=reports/fast_research/V7_MONTHLY_PERP_ETHUSDT_202510_RECOVERY_INDEPENDENT_QA_V3.json
    fetch=scripts/research_v8/fetch_monthly_from_recovery.py
  fi
  report="reports/fast_research/V8_MONTHLY_${market^^}_${symbol}_202511_V1.json"
  audit="reports/fast_research/V8_MONTHLY_${market^^}_${symbol}_202511_INDEPENDENT_QA_V1.json"
  directory="/home/xflops/coin-state/v8-monthly-${market}-${symbol,,}-202511-v1"
  bash scripts/with_task_progress.sh --title "V8 November容量与登记核对 ${market} ${symbol}" -- \
    /home/xflops/coin-state/research-env-v6/bin/python .cache/v8_november_source_guard_v1.py \
    --spec "$spec_file" --market "$market" --symbol "$symbol" --mode capacity
  bash scripts/with_task_progress.sh --title "V8 官方月档 ${market} ${symbol} 2025-11" -- \
    env COIN_TASK_PROGRESS=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 POLARS_MAX_THREADS=1 ARROW_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=-1 \
    /home/xflops/coin-state/research-env-v6/bin/python "$fetch" \
    --market "$market" --symbol "$symbol" --month 2025-11 --prior-receipt "$prior" --prior-qa "$prior_qa" \
    --run-dir "$directory" --output "$report"
  bash scripts/with_task_progress.sh --title "V8 November实际CHECKSUM绑定 ${market} ${symbol}" -- \
    /home/xflops/coin-state/research-env-v6/bin/python .cache/v8_november_source_guard_v1.py \
    --spec "$spec_file" --market "$market" --symbol "$symbol" --mode receipt
  bash scripts/with_task_progress.sh --title "V8 月档逐行QA ${market} ${symbol} 2025-11" -- \
    env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 POLARS_MAX_THREADS=1 ARROW_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=-1 \
    /home/xflops/coin-state/research-env-v6/bin/python scripts/research_v7/audit_monthly.py \
    --receipt "$report" --output "$audit"
  bash scripts/with_task_progress.sh --title "V8 November独立QA接受核对 ${market} ${symbol}" -- \
    /home/xflops/coin-state/research-env-v6/bin/python .cache/v8_november_source_guard_v1.py \
    --spec "$spec_file" --market "$market" --symbol "$symbol" --mode accepted
done
