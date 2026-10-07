#!/usr/bin/env bash
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
state="${EXPERT_STATE:-/home/ubuntu/coin/execution-state/expert-aggregation-v1-20261007}"
python="/home/ubuntu/coin/coin_collector_v3_fixed/work/research-venv/bin/python"
unit="coin-expert-aggregation-v1"
[[ "$repo" == /home/ubuntu/coin/* && "$state" == /home/ubuntu/coin/execution-state/* && "$state" != *'/../'* ]] || { echo '必须使用规范化服务器绝对路径'; exit 1; }
mkdir -p "$state"
export PYTHONPATH="$repo:$repo/src" POLARS_MAX_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
case "${1:-}" in
  --foreground) exec "$python" -m modules.expert_aggregation.run --state "$state" ;;
  --watch) exec "$python" -m modules.expert_aggregation.watch --state "$state" ;;
  --status) exec "$python" -m modules.expert_aggregation.watch --state "$state" --once ;;
esac
if systemctl --user is-active --quiet "$unit"; then
  echo '任务已在后台运行。'
else
  systemd-run --user --collect --unit="$unit" --property="WorkingDirectory=$repo" \
    --property="StandardOutput=append:$state/service.log" --property="StandardError=append:$state/service.log" \
    --setenv="PYTHONPATH=$PYTHONPATH" --setenv=POLARS_MAX_THREADS=1 --setenv=OPENBLAS_NUM_THREADS=1 \
    --setenv=OMP_NUM_THREADS=1 --setenv=MKL_NUM_THREADS=1 \
    "$python" -u -m modules.expert_aggregation.run --state "$state"
fi
echo "后台运行独立于SSH；实时进度：bash $repo/modules/expert_aggregation/run_expert_aggregation.sh --watch"
