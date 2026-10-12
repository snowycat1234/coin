# Fixed direct cross-sectional slow/fast ranking

One new scientific attempt: daily `rank(r21)-rank(r1)` versus daily `r21` and `price[t-1]/price[t-21]-1`, with the unchanged top-two/bottom-two portfolio function. Equal rank coefficients are fixed before outcomes. The SKIP control distinguishes reversal ranking from merely removing the newest trend day. This is a fixed crypto adaptation, not the paper's Sharpe-trained DMN, GP change point detector or exact traditional-futures replication. The original paper/code review and unsuccessful CPD adaptations remain in `research/slow-momentum-cpd-20261011`; no old Transformer or learned sleeve is rerun.

P1 is Apr2021–Jun2022, P2 is complete2023: independently initialized shared10k wallets, three arms each, no stitching or pristine OOS claim. Existing published minute trade/mark/funding sources and actual daily cube are reused. No supervised fitting, normalization fitting, future regime labels, oracle profit or new data request. All-active arms share past-only predicted risk; intrinsic cash remains cash and excludes itself from the minimum risk. Cash dates and actual vol/gross are reported separately.

`PROTOCOL.json` freezes costs, cadence, risk, source SHAs, bootstrap811720, six-wallet budget and strict economic/paid-terminal gates. Original 318a native engine and financial account are SHA-bound and untouched. Inventory/NAV audit failure is saved as FAIL and blocks acceptance. Technical recovery is not a new economic attempt or a parameter rescue.

Two causal tests passed in2.87s, including future suffix invariance and intrinsic-cash handling. Archive import smoke passed. An existing independent reviewer was requested but its turn failed due model capacity; the primary agent checked original default bindings, target identity/caps, fault preservation and original zero-advance state APIs before freezing.

Only previously verified reproducible cold caches of the two prior completed research windows were reclaimed (811877321+652828748B). Original observed sources/wallets and public packets/proofs remain. New window publication and zero-advance public restoration must complete before moving to the next window, regardless of its profit. Full minute numeric values and original scheduler state are retained.

Run through the unchanged guard:

```bash
export COIN_CPD_STATE=/workspace/cs-dual-speed-state
export QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=$COIN_CPD_STATE
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/cs-dual-speed-ranking-20261012/experiment.py prepare --state "$COIN_CPD_STATE/PREPARED" --source-commit <frozen-source-SHA>
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/cs-dual-speed-ranking-20261012/experiment.py run --state "$COIN_CPD_STATE/OBSERVED_P1" --window P1 --prepared /workspace/cs-continuous-state/SOURCE_RECOVERED --source-commit <published-input-SHA>
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/cs-dual-speed-ranking-20261012/archive.py restore --state "$COIN_CPD_STATE/FRESH_RESTORE_P1" --window P1 --artifact-commit <published-packet-SHA>
```

Use P2 and its published2023 source cache for the second calendar; exact final commands/SHAs will accompany actual results. No2024 imputation/451 retry,2026 lock access, lost-ledger reconstruction, distribution-study edit, Library, live or deployment.
