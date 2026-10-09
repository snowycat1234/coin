# April 1–June 3, 2024 input readiness

Preparation only for `FOLD_20240401`: 63 UTC decisions, 62 active intervals,
fresh 10,000 USDT startup. No requests, model exports, wallet results, control
fallback, fitting, inference, provider downloads or old experiment reruns.

`ADAPTER_CONTRACT.json` binds the unchanged original guard-OFF engine
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`, financial
configuration, current executable adapter bytes, existing dependency recipe,
retained H1 market identity, and the two small canonical context packets.
It reuses `evaluate_requests63.py` with explicit calendar/contract arguments.
The original January contracts and completed account evidence are preserved.

`READINESS.json` verifies all 70 registered H1 artifact hashes and the actual
CORE5 synchronous grid: 90,720 trade and mark minutes per asset, actual quote
USDT volumes, and 189 signed funding records per asset (945 total), retaining
their reported 8-hour intervals and original timestamps. Prices and causal
30-day returns are bit-identical to the original H1 packet. Original VOL/CS
recipes reproduce the targets exactly with the January 1, 2024 weekly anchor;
the existing SHORT recipe passes its independent scalar check. Original E5
slots remain intact and SHORT occupies appended slot 5. Producer comparison
will use admitted cash/VOL/CS/SHORT slots 0/1/4/5; unused SMA/Don producer zeros
must not replace canonical source data. Contexts are evaluation inputs.

`PREFIX_AVAILABILITY.json` verifies retained feature and expert inputs before
April 1 without fitting a scaler. There are 749 causal decisions, natural
prefix lengths 54/88/62/144/401, and 878 unique completed feature rows.
Only 748 raw next-day labels mature strictly before April 1. March 31's raw
label clock is April 1 00:01:00.000001 UTC. Its possible known-flat terminal
clock, March 31 00:01:00.000001 UTC, is conditional on the actual producer's
source-bound terminal identity and no-future-suffix proof; it is not an observed
replacement label. No raw clock is changed and no training provenance is
claimed for an export that has not arrived.

Paid native terminal semantics retain final-day target zero and persistent
cash closure on June 2, using the full actual tape until June 3 exclusive.
Actual delayed/partial fill clocks and paid flatness require the eventual
wallet audit; no surrogate clock or free close is substituted. Initial quote
capacity is zero with no external prestart minute. Historical publication,
venue contract and account rules remain uncertified.

Remaining dependencies: the actual frozen April model and control requests,
externally pinned producer source/config/model/scaler and fresh empty-Adam
birth-0 fixed-512 receipts; strict prefix clocks/known-flat terminal proof;
current-context and target/budget parity; and a request-specific authorized
published execution plan. Preparation does not authorize a wallet.

To reproduce into a fresh output directory with the already retained state
and `requirements-native61.txt` dependencies (no downloads):

```sh
python research/recover-frozen-runner-20261009/prepare_april63.py \
  --state STATE --output FRESH_CONTEXT_OUTPUT
```

The command bounds one CPU, 6 GB address space, 600 CPU seconds, preserves a
15 GiB disk reserve and disables network access. No account entry point is
provided by this preparation command.
