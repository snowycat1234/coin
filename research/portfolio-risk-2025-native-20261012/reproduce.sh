#!/usr/bin/env bash
set -euo pipefail
risk2025_arm=$1
risk2025_state=$2
risk2025_artifact=$3
case "$risk2025_arm" in CS_MATCHED|VOL_MATCHED|STATIC50) ;; *) exit 2 ;; esac
test ! -e "$risk2025_state"
export COIN_CPD_STATE="$risk2025_state/guard" QUANT_ROOT="$(git rev-parse --show-toplevel)" QUANT_STATE="$risk2025_state/guard"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/portfolio-risk-2025-native-20261012/public_source.py --state "$risk2025_state/SOURCE_PUBLIC" --artifact-commit "$risk2025_artifact"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/portfolio-risk-2025-native-20261012/archive.py restore --state "$risk2025_state/ACCOUNT_PUBLIC" --arm "$risk2025_arm" --artifact-commit "$risk2025_artifact" --prepared "$risk2025_state/SOURCE_PUBLIC/source"
