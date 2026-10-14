# Bounded higher-risk offline prototype

This is a source-and-synthetic preparation package. It has no exchange transport,
historical input loader, market downloader, credentials, or bot account. It does
not establish stable returns, a qualified candidate, predictive AI, or a future
ruin/liquidation probability. Original and low-risk lines are unchanged.

## Fixed first stage

H090 uses one fresh 10,000 USDT CORE5 wallet, gross target cap 0.90, per-asset
cap 0.30, absolute net intent cap 0.90 and past-only 15% annual covariance
target. Isolated 1x accounting remains unchanged. The 1.20/2x stage is deferred.
Actual marked exposure can drift above its cap; increases are then blocked and
capacity-limited paid reductions are needed. Neither a cap nor a stop prevents
an adverse gap or an isolated-account halt.

Reserve at most 9,000 of the original 10,000 USDT, retaining 1,000 uncommitted.
The exact unchanged-account dry-run/commit guard also limits new actual isolated
margin to 8,500 and retains a 1,000 free-cash floor before/after increases.
Funding and losses may breach that floor; cash is never invented to restore it.
Reduce-only instructions are not denied by this added floor. Actual original
fills, costs, funding, liabilities, marks and halts remain in the pinned Decimal
account. Public quantity filters and liquidation tiers are not certified.

## One candidate and its necessary control

CSH_H090_CONTROL keeps original CSH signals and proposes a fixed 1.5x target
multiplier followed by H090 concentration/volatility and capital gates. Binding
caps can reduce this multiplier; realized equal risk is not certified by a toy.
It is the necessary higher-risk control to separate more exposure from a new
mechanism's contribution.

CSH_MART_FINITE_REPLACE10 reserves 8,000 original USDT for the CSH ownership
sleeve and 1,000 for one finite BTC-long program. The 10% refers to original
initial capital, not to 10% of a BTC position. This is a fixed, transparent,
Martingale-inspired experiment, not a replica of Bybit's ongoing bot.

The finite program's opening margins are exactly 150, 187.50, 234.3750 and
292.968750 USDT. Its 1.25 multiplier acts on order margin, not base quantity.
Total planned margin is 864.843750, leaving 135.156250 for fees/funding inside
the same pre-reserved 1,000. Only actual account-bound opening-margin receipts
advance an order; partial fills accumulate under one index. The allowed final
rounding remainder comes from the pinned account quantity step and actual fill
price. Duplicate receipts cannot advance the count or move to another order.
The next long add trigger is the actual filled average basis times 0.95.

A net sleeve loss of 200 USDT is an exit signal, never a guarantee of a 200 loss
ceiling. After three adds, inventory remains owned and marked; it is not freely
closed. Terminal mode forbids more increases. This version allows only ONE
finite non-refillable program per annual fresh wallet. Released capital stays
retired and cannot be reused through renamed owners. No automatic round restart,
profit compounding, margin transfer or top-up exists. Multi-round behavior needs
a separate prespecified and reviewed loss/capital model.

The code contains policies and generated financial fixtures, not the historical
CSH ownership adapter. The finite fixture's four other asset holdings are toy
inventory, not actual CSH signals. Combined CSH/finite-add execution and owner
attribution remain review gates; do not label the toy as a candidate backtest.

## Financial source boundary

ACCOUNT_EXTENSION.diff contains one changed validation line: the maximum gross
configuration upper bound 0.60 becomes 0.90 in a new vendor namespace. The
original default stays 0.60. Every Decimal financial method is byte-identical.
ExecutionContractV2 is copied byte-identically and reused only for its timing
and cost arithmetic. Its frozen risk fields are not H090 certification.
SOURCE_PINS.json identifies originals and the new copy. Tests compare full
original/extended snapshots under the original caps, plus high-risk recovery.

BASE27 stays taker 5.5 bp per side, spread 4 bp, slippage 4 bp. Funding keeps
original signed position/mark/rate debits, with explicitly supplied event times.
The actual historical RAW_AS_FRACTION1 interpretation is still conditional.
The original shared previous-minute quote participation remains 0.001. Fine
quantity 1e-8 and opening minimum 10 are idealized research assumptions.

NATIVE_HARDCODE_MAP.json identifies the remaining native .60/.10 guards, sizing,
account/cost factory and risk descriptor bindings. They have not been removed
or bypassed. The toy fixture scheduler has 60 paid real-minute terminal attempts
and retains unpaid residuals, but is not a historical NativeDailySimulator
adapter or a proof of terminal60 production parity.

## Run only generated checks

From this directory:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -m unittest -v test_bounded_highrisk
    python3 source_preflight.py
    python3 run_toy.py
    python3 run_bounded_checks.py --receipt-dir toy_receipts_review010

The bounded harness requires a new receipt directory, never overwrites previous
attempts, and runs only those three fixed commands. Each subprocess has one CPU,
one math thread, a 4 GB address-space limit, sampled 2 GB RSS stop, 60 CPU seconds
and 120 wall seconds. No historical path or run argument is supported.
SOURCE_FREEZE.json binds exact code/protocol files. Final bounded receipts bind
that freeze and retain original outputs. ATTEMPTS.json preserves truthful
development failures and fixes; earlier bounded receipts remain unchanged.

Generated fixtures cover a paid exit, persistent correlated adverse gap,
funding drain, short liquidation-required/bankruptcy halts, zero-liquidity
terminal and late partial fills, plus finite shared-cash margin orders. These
are adversarial examples, not representative samples or probability estimates.
Positive total NAV/free cash cannot rescue the original isolated-short model.
Bankruptcy halt, liquidation-required halt and whole-wallet economic ruin are
different outcomes and must be reported separately.

## Long-term research remains gated

PROTOCOL.json predeclares the narrow candidate/control comparison, bad-regime
coverage, metrics and conditional stress-resampling proposal. It excludes
combinatorial searching, multiplier/lookback optimization and retrospective
Aurora winners. The public Aurora process supplies seven-day backtested parameter
recommendations; its predictive model and exact search space are not verified.
Already seen 2021/2023/2024/2025 are development only; 2022 mark gaps remain;
locked March–September 2026 and unknown holdouts stay closed. Current authorized
2025 runs must not be duplicated.

111 branch names, pinned main mechanism content and the sibling bounded audit
were inspected. No named finite margin-multiplied program was found in that
bounded scope, but full historical nonduplication remains an integration review
gate. Existing expert aggregation, static50/SMA, funding and risk mechanisms
remain prior work; they are not renamed into new algorithms here.

Before any historical GO, complete source/causality admission, the separately
reviewed native controller and cost factory bindings, shared owner/pending/cost
reconciliation, native terminal/recovery parity, dedup, independent review and
explicit parent authorization. No result here warrants a high-return or stable
APR promise.

## Official mechanism references

- Martingale margin multiplier and average-price trigger: https://www.bybit.com/en/help-center/article/Futures-Martingale-Bot-Parameters-Explained
- Finite maximum adds and continuing position: https://www.bybit.com/en/help-center/article/FAQ-Futures-Martingale-Bot
- Market exit and non-compounding distinction: https://www.bybit.com/en/help-center/article/Introduction-to-Futures-Martingale-Bot
- Actual per-position funding cadence and signs: https://www.bybit.com/en/help-center/article/Funding-fee-calculation

These references inform mechanism design. They do not validate the simulator's
historical fees, funding units, filter assumptions or a predictive AI claim.
