# HEADROOM local 2021 / 2023 result audit

Both original-bound local candidate states passed zero-transition cold restoration using the original codec, HEADROOM simulator and FineGridAccount. Each has 365 verified chunks and 525,600 genuine minute rows, full calendar, exact CORE5 Decimal zero inventory, active account, no halt, and paid-flat completion. No historical wallet or control was rerun by this observer.

| Year | Original paid PnL (USDT) | HEADROOM paid PnL (USDT) | Difference (USDT) | Original minute DD | HEADROOM minute DD | Original daily vol, annual | HEADROOM daily vol, annual |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 2499.489571 | 2597.759413 | +98.269843 | 5.112714% | 5.179632% | 9.026628% | 9.786756% |
| 2023 | 1159.692494 | 1119.037877 | -40.654617 | 11.993969% | 12.314499% | 10.354854% | 10.374826% |

These results do not establish consistent improvement. 2021 PnL increases while minute drawdown and annual daily volatility worsen. 2023 PnL decreases by 40.654617 USDT and both risk measures worsen. These negatives are retained.

## Scope and verification

- Exact financial prefixes through the first protection signal: 2021 has 219,522 minute rows, 259 trade legs and 2,290 funding rows through 2021-06-02 10:42 UTC; 2023 has 279,016 minute rows, 1,197 trade legs and 2,910 funding rows through 2023-07-13 18:16 UTC. Every numeric minute bit and exact trade/funding journal matches the prebound original control. Policy metadata or full old/new snapshot equality is not claimed.
- Each candidate had one recomputed causal READY protection signal, one actual protected reduce-only request on a true open, and one later daily-direction reset. Own trigger quantity/collateral/equity matches genuine numeric state and trade inventory/entry. All snapshot live-lock state is restored by the unchanged original validator.
- All 6,538 (2021) and 9,575 (2023) fill requests are source-backed and checked for open+1us timing, original latency, prior complete quote-volume .001 capacity, and shared symbol/open consumption. Ordinary flip phases may share one bucket. Original ordinary terminal uses five eligible opens; already-persistent protection retains its existing clock.
- Per-leg 5.5bp fees plus 4bp spread and 4bp slippage, fine 1e-8 grid, original account/source/targets, funding ownership/cash, isolated collateral, signed inventory, and Decimal NAV bridges pass. All original and candidate state/input files remain unchanged.
- Original 2023 RESULT omissions are supplemented from its original ACCOUNT summary and genuine chunks. Old/new net exposure uses the identical ordered CORE5 float64 marked-notional sum divided by float64 NAV. Missing values are never treated as zero.
- Paid cash PnL, marked PnL and residual inventory remain separate. Here both candidates are full paid-flat with zero residual; partial-flat or halted cases cannot count as paid.
- Cold code was independently reviewed. Actual receipts are supplied for a separate read-only review. 2024 is cloud-only and is not audited here; no new 2025 wallet is opened.

## Resources and retained failure

One CPU, 4GB address-space limit, 2GB sampled RSS cap, 300-second CPU and 360-second wall limits, zero swap, 8GB host cap, and the original 15GiB disk reserve were applied. 2021 passed in 26.03 seconds with sampled peak RSS 1.515GB; 2023 passed in 22.74 seconds with sampled peak RSS 1.568GB. Limits are sampled controls, not hard kernel RSS certification.

The initial 2021 read-only attempt used system Python and stopped at import because polars was absent, before from_snapshot. Its log/resource evidence is retained. The successful attempt reused the original existing financial runner venv, with no install, financial change or new wallet.

Exact values, file hashes, code-review identity, full signal/lock/source/ledger proofs, and original comparators are in LOCAL_RESULTS_SUMMARY.json and the two receipts.
