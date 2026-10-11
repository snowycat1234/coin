# Isolated economic semantics and permanent unpaid halt

Independent branch based on `b8e1289014ec8c67f18dbb22294be77a9e414d8e`; no old wallet rerun or result replacement.

`UNPAID_BEFORE.json` reproduces a real override defect through public fills/funding: synthetic funding drains free cash and BTC margin, creates 1003.80176 USDT genuine liability, while ETH collateral keeps NAV positive. Old Bybit `_risk` selects BOUND rather than the base account's permanent BANKRUPT_HALT. `UNPAID_AFTER.json` binds the corrected version. This extreme boundary rate is synthetic, not an observed funding rate or historical performance result.

Version v2 preserves existing HALTS and checks unpaid debt before isolated liquidation, plus after reentrant exchange liquidation instructions. No debt forgiveness, cross-leg top-up, reserve allocation or price formula change. Base account/controller behavior is retained.

Validation: first test attempt had 3 fixture expectation failures/41 passes because permanent-halt public APIs correctly raise RuntimeError; fixture corrected to test rejection and direct risk preservation. Final 44 passed in 18.40s: new Bybit debt tests, perpetual account/settlement, multi-asset, directional controller, ExecutionV2, funding, liquidation and liquidation-engine suites. Both receipts retained in external STATE.

Minimal reproduction, from repository root:

```bash
COIN_CPD_STATE=/workspace/liquidation-repro QUANT_ROOT=$PWD QUANT_STATE=/workspace/liquidation-repro bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/liquidation-semantics-20261011/reproduce_unpaid_halt.py --expect fixed --output /workspace/liquidation-repro/UNPAID.json
```

Old four wallets have zero terminal unpaid liability and minimum observed free cash above 7345 USDT; no evidence this defect affected them. They retain their original source bindings and conditional STOP. Native liquidation certification remains false.
