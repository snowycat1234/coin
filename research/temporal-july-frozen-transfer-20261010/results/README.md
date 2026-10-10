The unchanged April-prefix GRU512 earned **+249.14USDT**, versus frozen VOL
**−37.44USDT**, on the user-fixed July1–September2 exclusive,2024 block.
Primary PnL excess is **+286.58USDT**, utility excess **+0.03049181604**,
and daily drawdown difference **−2.694pp**. All four separate10k wallets are
reported, including paid common liquidation September1 at00:01:00.000001 UTC.
There are63 decisions and62 active intervals; no September2 outcome is used.

| Frozen policy | Net PnL USDT | Utility | Daily MDD | Mean active actual gross | Peak actual gross | Peak allocated gross | Funding PnL USDT |
|---|---:|---:|---:|---:|---:|---:|---:|
| April-prefix GRU512 | +249.14 | +0.02357037 | 2.108% | 14.959% | 34.639% | 36.776% | −3.81 |
| Prefix-static VOL | −37.44 | −0.00692145 | 4.802% | 12.882% | 17.257% | 17.031% | −10.04 |
| Static50 | +137.07 | +0.01252536 | 2.390% | 18.636% | 28.502% | 34.524% | −4.72 |
| Cash50 | +104.64 | +0.01010476 | 1.201% | 10.582% | 16.721% | 19.513% | −2.76 |

Mean gross uses62 opening holdings; peak actual gross includes openings and
end-boundary drift. Allocated gross sums absolute expert legs before netting.
All allocation gross≤.6/asset≤.3, opening/post-reduction position caps,
past30 covariance annual-vol≤.1 and post-eligibility-release L1≤.1 checks pass.
Maximum allocated asset gross is9.325% for GRU,3.406% VOL,8.226% Static50,
4.653% Cash50. Boundary risk reductions/events are zero for all four.

| Frozen policy | Fees USDT | Spread USDT | Slippage USDT | Total cost USDT | Paid terminal cost USDT |
|---|---:|---:|---:|---:|---:|
| April-prefix GRU512 | 8.89791 | 6.47129 | 6.47129 | 21.84049 | .95735 |
| Prefix-static VOL | 2.75572 | 2.00416 | 2.00416 | 6.76403 | 1.80128 |
| Static50 | 8.45111 | 6.14631 | 6.14631 | 20.74373 | 2.32302 |
| Cash50 | 4.96861 | 3.61357 | 3.61357 | 12.19575 | 1.15712 |

The frozen model has13,699 parameters,512 historical training updates, identity
`922c46f92dcfd4ef7b358b8803c87cd39ee5acdaa942f039d71987b3d8b9e6c9`.
Its checkpoint/scaler and original68 source bodies remain byte-identical to
the [April bundle](../../temporal-april-transfer-20261009/forward/FOLD_20240401/MANIFEST.json).
Scoring made zero model fits, optimizer updates or scaler updates. Eval requests
repeat bit for bit with Torch RNG unchanged. The original prefix-static VOL
choice is retained; no July-prefix selection was recalculated.

Inputs are63×64×5×24 values and validity masks,63×64×5 actual-step masks,
and18 current signed expert-target/eligibility values. CORE5 order is
BTC/ETH/SOL/XRP/DOGE; original ten-asset aggregate context is retained.
All126 unique completed steps Apr29–Sep1 are observed; the first window uses
raw bars Apr28–June30. Original formulas exactly reproduce1,642 retained
feature rows,91 April–June CASH/VOL/CS targets and covariance rows, and61
May–June SHORT rows. The unchanged train-only scaler uses878 unique rows
strictly before April1. There are no observed wallet-state model features.

The economics packet from immutable commit
[`5109edc`](https://github.com/snowycat1234/coin/blob/5109edcaa5a790a023a11828cfd1452b5705ba1a/research/core5-july2024-native-data/CONSUMER_INDEX.json)
provides63 real00:01 prices and62 complete held coefficients. Exact SHA/CRC,
execution clocks, event brackets and strict-prior mark clocks pass; independent
signed-rate×past-mark sums differ by at most3.56e−15USDT/base unit. Only324,273
bytes of small derived members/index/ZIP-directory HTTP206 responses were
restored, with zero provider/whole-archive downloads or raw market members.
The prior [coverage-only receipt](../RECEIPT.json) remains unchanged historical
evidence of the earlier blocked attempt.

Six focused tests pass. Independent saved-path verification reconciles252
rows, exact targets/budgets, costs, signed funding, utility, drawdown, caps and
paid flattening; maximum daily PnL residual is2.26e−12USDT. It also publishes
per-asset net contributions. One initial frozen-buffer property error occurred
before inference or any wallet; it was corrected with no recipe change and its
failed resource receipt is retained. The four economic wallets ran once.

This is **project-seen historical transfer**, with daily boundary/full-fill
execution assumptions and completed-day publication-time proxies. It is not
minute-native or pristine OOS. All five assets lack mark bars opened
**2024-08-12 10:02 and10:03 UTC** in the official archives; those are neither
filled nor used as synthetic observations. Verified daily prices/funding stay
complete, but any later full-minute claim must flag the gaps. No native wallet
was run. The separate native-only repair reported official mark API451 and
stopped at `001024ceb6f7a33be6b1f95b17f7c7d9777a3dde`; daily economics hashes
remain unchanged. No repair was duplicated or awaited here.
This positive block supports conditional transfer only; earlier
failures remain, and there is no promotion, stable-performance or APR claim.
STOP after this fixed block.

Artifacts: [complete outcomes](RESULT.json), [input receipt](INPUT_RECEIPT.json),
[paired requests/paths](PAIRED_PATHS.npz), [all252 daily accounting rows](DAILY_ACCOUNTING.csv),
[verification](VERIFICATION.json), [test/resource receipt](TEST_RECEIPT.json),
[source/file manifest](MANIFEST.json). Small frozen model/scaler files are
referenced in their existing April location rather than duplicated.

Reproduce with the retained primitive STATE and the
[dependency recipe](../requirements-transfer.txt), using existing bounded
runtime and an exclusive new output/report destination. No package install
was needed. A fresh environment installs CPU Torch from its official index,
then remaining pins from official PyPI. Add repository root and `src` to
PYTHONPATH. Example wallet command (CPU3, one thread, resident2GB/shared8GB,
swap0/GPU0; replace STATE with the retained source root):

```bash
PYTHONPATH="$PWD:$PWD/src" taskset -c 3 /workspace/coin/.venv/bin/python \
  research/temporal-april-transfer-20261009/BOUNDED_RESIDENT_RUNTIME.py \
  --report NEW_RESOURCE.json /workspace/coin/.venv/bin/python \
  -m modules.temporal_july_transfer.evaluate \
  --state STATE --economics STATE/july-frozen-transfer/economics \
  --output NEW_RESULTS
```

Restore only the necessary economics with `../restore_economics.py --output
NEW_ECONOMICS` under the existing bounded recovery launcher. Focused tests are
`pytest -q modules/temporal_july_transfer/test_transfer.py` with STATE-owned
`--basetemp` under the same resident guard. Read-only verification is
`python -m modules.temporal_july_transfer.verify --state STATE --economics
ECONOMICS --results RESULTS --output NEW_VERIFICATION.json`; it performs no
wallet or model inference.
