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

Saved economic audit: `SAVED_DOGE_AUDIT.json`, independently reconstructs all trade collateral/basis and free cash, uses original source marks, verifies previous-minute trigger, funding/ordinary-fill order, bankruptcy loss exactly once, flat interval and paid fresh-signal reentry. Eight DOGE events pass the frozen conditional semantics. Two raw first events qualify under modern mark-MM but not prior entry-MM at that observed minute; no later counterfactual is inferred. Six minute overshoots remove negative residual equity at bankruptcy takeover (declared insurance proxy), two remove positive residual equity. This is not ordinary fee-free closure or certified native insurance cash.

Bybit says modern margin-rule rollout starts2025-09-02: https://www.bybit.com/en/help-center/article/Understanding-the-Adjustment-and-Impact-of-the-New-Margin-Calculation . Thus2021 and other pre-rollout applications require the explicit **modern rules applied to historical Binance prices** scope, not contemporary native validation. Assumed MMR .005 remains uncertified. Official order cost includes fee-to-close reserve: https://www.bybit.com/en/help-center/article/Order-Cost-USDT-Contract . Omitted short1x partition is2*entry-notional*fee: .211665–.292885USDT per saved takeover. All-leg conservative reserve maximum2.6981–2.9143USDT is far below old observed minimum free cash7345.62–7545.78. No evidence of opening cash insufficiency from this omission; native cash partition/liquidation expenses remain incomplete. Do not add this partition as an extra PnL charge or into existing collateral (which would wrongly move LP as extra margin).

Read-only audit first launch stopped on initial flat/no-position funding receipts lacking decimal_strings; corrected to accept ONLY explicitly zero unowned receipts. No funded value imputed, wallet or fit created. Audit0fits/0reruns. Independent read-only reviewer reached the same eight-event conclusions; all source/hash/results retained. Final default10 checks include the unchanged synthetic two-leg full-cost kernel golden net−5.346USDT and terminal cash closure.
