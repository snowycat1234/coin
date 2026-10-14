# Exact CSH target identity after the funding rank test

Preparation only. The new funding-candidate versus same-lag-price target pass
has not run. No future returns, funding cash, costs, turnover, native wallets,
account/NAV, models or holdouts are evaluated by this module.

## Why one more target discriminator is needed

The completed weekly-support test is durable at
894fdc4c3e5890034e1900e83f0cd6327ef8572f. Its basket changes were0/1/2/1 across
2021/2023/2024/2025, with196 admitted weekly ranks in total. The2021 result
is specifically0 changes among39 all-five200-admitted scheduled ranks.
It does not establish a full daily-target no-op or complete original CSH
ownership coverage. Original2021 code keeps CS31 weekly state while HOLD200
is inactive; on2021-04-02 the daily matched target can activate using the
2021-03-29 rank. This source-established boundary is explicitly included
here. The completed result/failure history is preserved without revision or
an extra replay.

## Fixed allocation stack

The pair is funding-adjusted simple21 return versus identical-lag simple21
price return. Both rank windows remain `[D−22days,D−1day)`, with close endpoints
D−22days and D−1day. The adjustment sums observed rates once, scale1
conditional on raw fractions; it is not exact funded PnL. Original raw interval
unknowns and retrieved-project/archive-relative coverage limits remain.

CS31 updates on the original2024Jan1 weekly anchor and preserves the previous
ownership rank. Original price-eligibility min4/stable ties and sticky member
clearing are retained. Funding-unready does not create a smaller universe:
both paired arms share a whole-rank source-known flag. An unknown owning rank
feeding a later daily admitted target is INCONCLUSIVE, not fabricated cash.
An unknown early rank that never feeds an admitted output is disclosed.

Daily risk still uses the original CURRENT31 completed-close history at D,
30 simple returns, signed held-subset `np.cov(ddof=1)*365` and .10 downscale.
Only the rank features have the24h availability lag. HOLD200 masks and original
HOLD targets remain identical across arms. The unchanged original `match`
function applies its daily all-five CS31/HOLD200 and64-close clock gate,
`common=min(.10,CS_sigma,HOLD_sigma)` and common-zero behavior. STATIC50 is
half the matched CS plus half matched unconditional VOL_MANAGED_HOLD, then
the unchanged original portfolio `allocate/scale` can upscale toward .10
subject .30 per-asset and .60 gross caps. It is not a simple average of already
final scaled targets. SMA and EXACTHALF remain excluded.

The six complete original source files and `original_functions.py` are retained
at their exact public source hashes. Their selected function bodies/defaults
execute unchanged, without importing models, wallet code or economic helpers.
The only replaced dependency is `match`'s `public_targets` result: it receives
the already computed paired CS component and exact eligibility diagnostic.

## Preparation evidence

Twelve synthetic tests cover source CS replay parity, March29/April2
activation, min4 ties, sticky recovery, unknown owning rank, common-zero,
signed covariance, upscale/caps, causal prefixes, feature-only lag, future
funding suffixes, parent-GO and NumPy-scalar reporting. Original unlagged CSH
targets reproduce all365/365/366/365 previously published target rows exactly,
including2021's91 matched-cash days. This is original-source arithmetic QA;
no new candidate/same-lag target pass or subsequent economic outcome is used.

## Reproduce preparation

The previous funding source/preparation module and its pinned external inputs
must be restored as documented there. Set `FUNDING_RANK_SOURCE_DIR` to its
`source_admission` directory and `FUNDING_RANK_PREPARATION_DIR` to the original
preparation parent module when the local sibling defaults do not match the
published layout. Three additional compact original target packets belong
under this module's `inputs_restored` directory, with exact filenames and
hashes in `SOURCE_REFERENCES.json`. No full-minute data or provider download
is needed for this target-only stage.

From this module directory run:

`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest discover -s . -p 'test_*.py' -v`

`python -c 'from verify_original_parity import verify; print(verify())'` checks
only original source target parity. It does not run the new funding pair.

After a frozen independent PASS and separate exact parent GO, the sole
historical target command is `bash run_once.sh PARENT_GO.json ATTEMPT001`.
The whole process is bounded by120seconds plus5second TERM/KILL grace,
one CPU/numeric thread, hidden GPUs,4GB address space,2GB sampled RSS,
8GB host-use stop, zero swap,15GiB disk reserve and10MB new outputs.
Original-source parity took1.45seconds and synthetics .405seconds locally;
the new target pass is expected comfortably under120seconds, not timed yet.

All four full natural calendars, zero-delta periods, existing four changed
episodes and activation ownership contexts remain. Output is exact daily
target identity and readiness only. No later native matched wallet or proxy
is authorized by this preparation or its result.
