#!/usr/bin/env bash
set -euo pipefail
/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python - <<'PY'
import ast
from pathlib import Path
for name in ('multi_asset_data.py','multi_asset_portfolio.py','compare_multi_asset_portfolios.py','multi_asset_financial_audit.py'):
    ast.parse((Path('/mnt/d/codex/coin/scripts/investment')/name).read_text())
print('Normal current source syntax accepted; no market or ledger read.')
PY
exec /mnt/c/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe -NoProfile -NonInteractive -File D:/codex/coin/.cache/d058_metadata.ps1 -ExpectedTargetSHA256 6e9aa37dad81f754543653acdfccbc75aa96750afff55e817e654debce10bd79 -ExpectedPortfolioSHA256 4ee1ae0f8c75e6b13d1d69d18f8acd6e70108041a82232895aa8e55d7951c570 -ExpectedCheckerSHA256 cefd6bd0051c24756da99a9f6bd52be80472951ef918004b90f92a5552406215 -ExpectedComparerSHA256 32fb5846a28bb9d45ed5cff4c0dc1540d17f1c9f41e1ef10a34ea4365dc3b1a0 -ExpectedDataSHA256 ca8076e5a3bbc511a6cfb144f09a892755ab5d279206f8f8e8316a70521eabc3 -ExpectedSharedSHA256 0107ce0cb410280be3435eb6b7264e2e3e3e80c76b03cfebdfd7453124126682 -WarmProofPath reports/fast_research/RSI2_JANUARY_DAILY_WARMUP_ACCEPTANCE_20261004_V1.json -WarmProofSHA256 c9416c61bcbf842104da33fd718178ffc9ef188de06a4c38107ff77292ab833e -MetadataTaskId "$COIN_TASK_ID"
