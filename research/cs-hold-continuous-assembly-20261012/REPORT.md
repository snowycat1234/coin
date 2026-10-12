# Static CS/HOLD continuous coverage: two wallets executed, STOP

The known fixed50 target rule was actually executed in two new shared10k wallets, with four original single controls reused and zero selector fits/provider downloads/old-wallet replays. This is new continuous execution coverage, not a new assembly algorithm. The preceding six ranking wallets are complete and preserved at research/cs-dual-speed-ranking-20261012, closure31fe7210a18de8a6029fa08906ce4ed7b20940ba; none was rerun.

| Planned source calendar | Actual mixed account outcome | Qualification |
|---|---|---|
| Apr2021–Jun2022,456days | Halted on42nd day,59267minutes; markedNAV10981.56 | Incomplete, not cash income, STOP |
| Complete2023,365days | 525600minutes, paid-flat net+1205.47USDT | Cash-CI crosses0, STOP |

The first wallet hit default `LIQUIDATION_REQUIRED_HALT` on2021-05-12 03:48UTC. ETH quantity−.00176847 at mark4325.75123408 gave about7.65USDT notional; isolated equity.033220860853 was below maintenance.038249806425. Total account residual notional314.886446USDT and unpaid liability0 were retained. The default engine did not simulate liquidation or charge an invented settlement. ETH rejection receipts include196 BELOW_MIN_NOTIONAL_OR_CAPACITY and41 FIVE_ATTEMPTS_EXPIRED; this is evidence of execution constraints, not an estimated counterfactual rescue. No topup, min-order waiver, forced-free close, protection retune or restart. It never reached the later2022 bear phase. Its positive marked value cannot be compared with full456-day controller returns.

The2023 mixture earned+1205.468702USDT after actual funding−79.498963, fees64.626592 and execution94.003239; same-quantity price contribution1443.597496. Actual annualized daily vol7.430959%, maximum minute drawdown8.411573%, worst30-day−3.648794%; mean/max gross23.475726/39.284222%. Same-wallet LONG+2137.732146 and SHORT−932.263444 are contribution accounting, not independent strategy capital. The14-day circular-bootstrap cash-increment mean-return95CI[−.000120831917,.000808874971] crosses0. Paid/net/risk gates passed, confidence gate failed.

On the same complete2023 calendar its descriptive marked increments are+1220.498959 versus CS−15.030256(paid flat), and−1206.398740 versus HOLD+2411.867442(marked,5.824199USDT residual). No income is computed by averaging separate accounts. The mixture's ex-ante sigmas averaged6.642846/6.588659% versus ingredient9.950224/9.330635% inP1/P2, so these are not equal-risk alpha comparisons. Target components, clocks, source and default execution exactly match the reused controls; joint netting deliberately changes exposure and inventory history.

The original32c4f8e fixed-half compose rule nets before execution and does not re-lever. OldSMA200+CS half-year controls, old temporal soft weights/ramp, four prequential63-day folds, support-pair/minute models,28wallet EG/FixedShare, native86-day50/50−63.55 and Q4 Static50+1461.05 with XRP liquidation all remain prior evidence. No repeated concept/Q4/86 run or original selector training. The exact difference is current matched CS/HOLD components and the complete456/365 calendars under unchanged318a/USDT/BASE27/raw actual funding/source/capacity/1x/no-topup/min10/five-attempt/last6-minute contracts. Historical native fees, fund unit, charge-mark, MMR and arrival authority remain uncertified.

Counts: one frozen coverage attempt, two actual new wallets, four single controls REUSED, six completed ranking wallets REUSED, zero model/normalizer fits, provider downloads or old-account replays. Native times15.050784/159.276572s. First partial report incorrectly compared its fragment to full controllers and passed partial positivity; original JSON is retained, reporting-only correction removes the increments and fails whole-calendar positivity. Three tests passed3.65s including this regression; no financial input or kernel change.

The complete two-account payload79564266B is below200MB: partialP18655607B/12parts at5191aeddd5d9fa1a68a29f1812a95692e3095cbd; fullP270908659B/91parts ata958d1a7eb1e4cad8e80daf9a9f1bbff79f186c8. Both fresh public recoveries rebuilt exact full price/funding sources, ordinary original scheduler/account state and all37 minute values/clocks, original NPZ byte SHA, journals, summary and inventory/NAV. Account advances/new fits/downloads/observed-cache opens were zero. Restoration times59.143293/106.848068s. Actual new observed accounts remain; only verified duplicate wrappers/codec buffers/source ZIPs or published reconstruction caches were reclaimed.

Frozen code92fd36246a9c6ea33c72701371ed8421ad8d6579, target/publication3838b45ed7779d6260b3b2a94fcd56abfbc718af; P1 native at3838b45e, P2 native at287760a40dcff15b3bd0c81af9cf3748fcfce328. Full hashes/bindings/config/seeds are in PROTOCOL/SOURCE_SHA256/input/summary/evidence. Two already-seen independently initialized calendars are not a stitched curve or pristine OOS. SOURCE gaps/HTTP451 for2024, locked2026 observations, inaccessible old ledgers and unrelated distribution files remain untouched. No Library, keys, live, pay or deployment.

Minimal exact public recovery from a clean checkout and fresh state:

```bash
export COIN_CPD_STATE=/workspace/cs-hold-reproduce-state
export QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=$COIN_CPD_STATE
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/cs-hold-continuous-assembly-20261012/archive.py restore --state "$COIN_CPD_STATE/P1" --window P1 --artifact-commit 5191aeddd5d9fa1a68a29f1812a95692e3095cbd
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python research/cs-hold-continuous-assembly-20261012/archive.py restore --state "$COIN_CPD_STATE/P2" --window P2 --artifact-commit a958d1a7eb1e4cad8e80daf9a9f1bbff79f186c8
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python -m pytest -q research/cs-hold-continuous-assembly-20261012 --basetemp="$COIN_CPD_STATE/TEST_TMP"
```

The execution gap has been tested, with one incomplete halted and one complete positive wallet. Fixed half-weight assembly does not pass cross-stage robustness. The concrete blocker is isolated maintenance/exit feasibility plus insufficient statistical evidence, rather than missing assembly code or an unrun Q4/86 test. No new dynamic selector is justified by these two paths.
