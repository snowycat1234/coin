# STATIC50 actual-2024 native replay halt: read-only diagnosis

**Result.** This is a modeled isolated-margin failure in the frozen research policy, not evidence that the strategy made a full-year +15.63% paid return. The account stopped at 2024-11-16 10:49:00 UTC, 461,448 of 527,040 required minute observations (day index 320, 648 completed minutes that day), on a short of 300 XRP. The run reports `LIQUIDATION_REQUIRED_HALT`, `NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED`, `STOP_PARTIAL_2024_NATIVE_SENSITIVITY`, `paid_cash_return: null`, `paid_flat: false`, and no liquidation event generated. The +$1,563.0844447500833 / +15.6308444475% is *partial marked NAV* at the halt, not realized/paid or full-year performance. A zero-length simulated liquidation list does not mean the account was safe; the engine explicitly stops before modeling a liquidation fill.

## Decisive position and arithmetic

| Item | Actual recorded value |
|---|---:|
| Asset and side | XRPUSDT, short |
| Quantity | -300 XRP |
| Entry | 0.53197408 USDT/XRP |
| Mark at observed halt | 1.06181663 USDT/XRP |
| Isolated balance | 159.592224 USDT |
| Unrealized position P&L | -158.952765 USDT |
| Isolated equity | 0.639459 USDT |
| Assumed maintenance rate | 0.005 |
| Maintenance margin | 1.592724945 USDT |
| Deficit to maintenance | 0.953265945 USDT |
| Portfolio NAV | 11,563.0844447500833083 USDT |
| Free cash | 9,853.6755977726814794 USDT |
| Unpaid liability | 0 |

Independent Decimal recomputation: `159.592224 - 300*(1.06181663 - 0.53197408) = 0.639459`, while `300*1.06181663*0.005 = 1.592724945`. The 1x short loses essentially all its original position collateral when its price nearly doubles (+99.5993% from entry). The exact assumed threshold for this residual position is `(159.592224 + 300*0.53197408)/(300*1.005) = 1.0586548855721393`, or +99.0050% from entry. One minute earlier, at the 10:48 close, mark was 1.05526648, equity 2.604504 and maintenance 1.58289972: still above threshold. The 10:49 close mark 1.06181663 crosses it. The 10:49 minute itself is excluded from the 648 recorded successful rows because the mark check halts immediately.

The portfolio NAV remains positive because cash and the other positions' gains outweigh the XRP loss. The policy checks *each isolated position* rather than offsetting an under-margined XRP position with 9,853.68 USDT of free cash or gains on BTC/SOL/DOGE. This is consistent with the code's stated no-margin-top-up design and with the synthetic unit exercise below. It does **not** certify actual Bybit liquidation timing or price.

## Why the exposure persisted

- Last XRP resize: 2024-11-15 00:01:00.000001 UTC, a buy/close of 200 XRP from -500 to -300 at fill 0.7761204. It released 106.394816 USDT of isolated balance and realized -48.829264 USDT on that leg. The remaining 300 kept its 0.53197408 basis and 159.592224 isolated balance.
- Last recorded XRP funding: 2024-11-16 08:00:00.001 UTC, +0.029178 USDT to free cash at a 0.9726 prior mark. Funding cash does not automatically top up XRP's isolated balance. The funding-rate unit/publication are explicitly uncertified in this conditional replay.
- Frozen 2024-11-16 XRP daily target weight was -0.018445998257567743, implying a desired quantity of approximately -237.88109 XRP against the held -300. Each of five scheduled 00:01–00:05 reduction requests was 62.11890914338037 XRP, smaller than the **assumed** 100-XRP step. The account's `floor` to whole assumed lots therefore produces zero; each attempt is rejected `BELOW_MIN_NOTIONAL_OR_CAPACITY`, then the daily target expires `FIVE_ATTEMPTS_EXPIRED`. The rejection label is shared with other causes, but the frozen lot arithmetic alone suffices here. There were no XRP fills on 2024-11-16 before the halt.
- The scheduler's separate emergency reduction mechanism triggers only when an asset is over the 0.30 NAV cap or gross exposures are over 0.60 NAV. At the halt XRP absolute weight is about 0.02755, gross weight about 0.18442, so it cannot fire. There is no margin-distance protective exit or free-cash collateral transfer. Daily targets can expire after five attempt minutes.
- Merely rounding that 62-XRP daily reduction up to 100 would not by itself ensure survival. The account's partial close releases isolated balance pro rata; at a fixed adverse price, residual isolated equity and maintenance both decline in proportion to remaining quantity. A new protective policy would need a timely *full* reduce-only close before breach, or an explicitly modeled collateral top-up. It would also need capacity/fee/latency checks and a new policy identity.

## Source and implementation checks

1. The 2024-11 source is a hash-bound market NPZ, `prepared_2024_cold/months/2024-11.npz` (SHA-256 `b0f120af935f7300e2f5d991bbd5a17f9f92292b1725feb444608c2e4abe5b75`). Its XRP `mark` for the 10:47 minute is 1.05526648 (observed at 10:48); for the 10:48 minute it is 1.06181663 (observed at 10:49). The only 10 derived source mark cells relate to the recorded August gap, not the November event. The full cold source index SHA-256 is `0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69`.
2. The recorded `recovery/DAY_0320.npz` (SHA-256 `9fb50fb2fb7cb5557e910d6224c5a5e2d192bd1afd2d7a97c96df0e965b5479`) has 648 completed rows. Its last row has XRP equity 2.604504 at 10:48. The following actual source mark and account witness independently reproduce the 10:49 breach. `recovery/POINTER.json` records the genuine state hash `17a2d33a9b1c2c0e496245ab6bcad2f5297ceec299b6158d4b221df5fc3ac7af`.
3. The financial account code `src/quant/perpetual_account.py` lines 290–305 checks `isolated_balance + quantity*(mark-entry) <= abs(quantity)*mark*0.005`, stops with the explicit witness, and does not net free cash into the per-position test. Lines 319–345 invoke that check on each causal minute-close mark. Lines 396–416 release isolated balance pro rata on a partial close. Lines 515–546 book funding to free cash or debit it, without increasing isolated margin. `scripts/investment/resumable_perpetual.py` lines 289–310 restrict emergency reductions to exposure caps; lines 380–398 expire unfilled daily requests after five attempts; lines 440–444 stop at the close mark breach. The source files match the frozen runner's required SHAs (`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585` for the scheduler and `6c51c4efe33d652b2ddb1e3befd4e90f1aefca1140a578f9ff6fc3d50a8da0d6` for the quantity account adapter).
4. The result's independent Decimal NAV bridge reports zero error (`0E-35`). Its net bridge is gross same-quantity P&L 1,877.2382615606 minus execution 110.236034160 minus fees 75.786912342988 plus funding -128.1308703075286917 = 1,563.0844447500833083 USDT. This validates the recorded NAV arithmetic, not the real-world executability or actual exchange filters.
5. `test_isolated_policy_synthetic.py` is a safe synthetic-only direct-account check; all four tests passed. It confirms that (a) a 300-XRP short can trigger `LIQUIDATION_REQUIRED_HALT` with more than 9,000 USDT free, (b) a 62.1189-XRP request floors to zero at the assumed 100-XRP step, (c) closing only 100 of 300 XRP leaves the isolated-equity/maintenance ratio unchanged at a fixed mark and can still halt at the later adverse mark, and (d) a fully filled 300-XRP reduce-only close *before* the later observed breach removes the exposure. Test (d) assumes sufficient capacity and a fill at the chosen synthetic time; it does not claim that such an exit was historically available or executed. These are account invariants, not historical performance tests.

**Classification.** We found no evidence of an arithmetic, timestamp, import, or replay-output defect causing this halt. It is an economic failure **under the explicitly conditional frozen research policy**, magnified by coarse assumed lot steps, five-attempt daily target expiry, no per-position margin safety exit, and no automatic top-up. The assumed 100-XRP step and 0.005 MMR are not certified actual/historical venue rules; intraminute liquidation behavior, risk tiers, funding publication, and fills are outside this model. The earliest *observed minute-close modeled* breach is the supported conclusion.

**Next sensitivity, only after frozen arms finish.** Register a distinct policy/configuration and evaluate all already selected years/arms without cherry-picking this outcome: e.g. a **pre-registered generic** margin-headroom guard that, while still ACTIVE, schedules a full reduce-only close when isolated equity approaches maintenance (or explicitly transfers bounded free cash as a different policy), with whole-lot and observed-capacity execution, latency, fees, and explicit unexecutable stops. Choose the guard threshold on prior policy grounds, not retrospectively from the 10:48 observation. Add pure-account tests for short adverse moves, enough free cash but insufficient isolated equity, a sub-step daily reduction, partial-close pro-rata insufficiency, full protective close, and funding-credit isolation. Report this as a new sensitivity beside the immutable frozen baseline; do not alter, advance, or rerun the halted STATIC50 wallet.

## Principal on-disk evidence

- `coin_expanded_coverage_20261013/wallets/STATIC50/RESULT.json` — SHA-256 `d50431e8e17c8cda856d73823baba4f623528d917f18e36532b0f20bdcb1ac1e`
- `coin_expanded_coverage_20261013/wallets/STATIC50/ACCOUNT.json` — SHA-256 `caa26fc4b3797f06036611721020c637fa3d7259dba0caa3519cd39cba8a976f`
- `coin_expanded_coverage_20261013/wallets/STATIC50/recovery/DAY_0320.npz`
- `coin_expanded_coverage_20261013/prepared_2024_cold/months/2024-11.npz`
- `coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py` — SHA-256 `ffa57a4c3c3b031945fcbc5db429d8b5e6ef06e880a8a577265836602ad55110`
- `coin_native_half_mix_20261013/repo/research/quantity-grid-sensitivity-20261012/QUANTITY_PROFILE.json` — SHA-256 `94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf`
- `coin_2024_halt_diagnosis_20261013/test_isolated_policy_synthetic.py` — SHA-256 `dc440d97dc76bc015a51445ec20e4cdce85550b02af1c64d7f817627b5954df5`
