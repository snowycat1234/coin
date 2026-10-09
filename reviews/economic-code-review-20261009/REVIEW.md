# Independent economic code review, 2026-10-09

One verified **medium-severity adapter defect** was found. It can reject a valid
historical evaluation path when expert eligibility disappears. It does not explain
the retained May–June poor-return results: their inspected E5 and momentum-short
expert masks have no loss-of-eligibility transitions. No new defect was found in
the reviewed accounting, feature timing or differentiable objective scope.

The subsequent [executed input/configuration diagnosis](CONFIGURATION_REVIEW.md)
reproduces frozen model exports and scaling, verifies encoder gradients, and
quantifies feature-scale concentration, allocation saturation and omitted expert
state. It adds a minimal calendar/state witness without implementing a new model.

## Verified defect: forced CASH release incorrectly charged to discretionary ramp

Source: [`evaluate_requests61.py:117–122` at 0090a7182c75a655197afd85f4db2c66db6456f6](https://github.com/snowycat1234/coin/blob/0090a7182c75a655197afd85f4db2c66db6456f6/research/recover-frozen-runner-20261009/evaluate_requests61.py#L117).
SHA256 `c7b814f3cac58363dcf11b04f6794af9944e6fe0e9887a9e72faa58c1e153ef3`.
The same source bytes were checked at later branch head
`d2682ced22efedde0ca6fb1e1336b8ca2cb3f634` during this review.

The append-only six-slot path correctly releases an unavailable prior allocation
to CASH, then applies the discretionary L1 ramp to that released prior. Its final
assertion instead compares against the unreleased prior. The assertion is shared
with the five-slot path, although the direct reproducer exercises the actual
six-slot implementation without substituting its mapper or target combiner.

Three SHORT-only requests produce `[.85 CASH, .15 SHORT]`. SHORT becomes
ineligible on the fourth decision; the new request selects CASH and passes
`validate()`. Expected budget is `[1 CASH, 0 SHORT]`: forced L1 movement `.3`,
discretionary L1 movement `0`. Observed result is
`ValueError("Original daily simplex/ramp violated")`. Selecting VOL as the
replacement should yield `[.95 CASH, .05 VOL]`, with discretionary L1 `.1`;
that valid path also fails. Compact-plus-SHORT and full-E5-plus-SHORT layouts
both reproduce the defect.

The original semantics explicitly exempt forced release in
[`conditional_selector_core.py:255–270`](https://github.com/snowycat1234/coin/blob/0090a7182c75a655197afd85f4db2c66db6456f6/research/recover-frozen-runner-20261009/auxiliary/conditional_selector_core.py#L255),
and the byte-bound recovered prototype documents and implements the same order
at `source/modules/direct_path/prototype.py:85–121`, SHA256
`46a0ca0b76bf29d50133bdd85b5730f4fd029f05378ce2ef086752b869a8fcab`.

Expected/observed evidence is saved in [ELIGIBILITY_RELEASE.json](ELIGIBILITY_RELEASE.json).
New regression tests are in [test_evaluate_requests61.py](../../tests/test_evaluate_requests61.py):
four cases failed at the exact offending assertion before the patch; the
discretionary-cap rejection control passed. After the patch, all five pass.
The patch computes the released prior before either layout branch and compares
the final budget against it. All-eligible paths have `released == prior`, so their
computation and acceptance condition are unchanged. The review branch updates
only the adapter's declared source/test hashes and records the ramp reference;
production branch contracts and old exports remain unchanged.

Affected results: future or previously rejected evaluations containing eligibility
loss after an allocation accumulates. No completed retained 61-day result is
attributed to this defect. The inspected momentum context SHA256
`89183eb92bd45b65a1209aa139f80964cc013c62015a803336db7a7bbd90840d` has
61/61 eligible expert rows and 305/305 eligible asset rows. Recovered
`H1_VALIDATE.npz`, SHA256
`c13de3125698f1fc350d1435453cbb6e33b7d5873537d7f859c1570344f081bc`,
has 305/305 eligible E5 expert rows. This recovered proxy container is distinct
from the native adapter's canonical `H1_E5_INPUTS.npz`; its full source-container
byte proof was not independently rerun here.

## Scope and evidence

| Scope | Exact source | Evidence |
|---|---|---|
| Native wallet and scheduler | `55ac3d2ee730b1cd1381696330a6abaf1925eb92`; engine SHA256 `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585` | Eight independent Decimal long/short × price direction × funding-sign cases match NAV to less than `1e-30`; one 12-minute synthetic CORE5 wallet verifies shared cash, costs, one-minute-plus-1µs latency, prior-minute capacity and paid terminal flat. Expected/observed NAV `9997.84`, fees `.88`, execution cost `1.28`. |
| Features and model | `316423e2b4174bbf072814c1627861469a2e952b` | 35 temporal tests and 27 feature/development/comparison tests pass: completed-bar shift, real 64-step history, feature/time masks, train-only scaling, split/maturity checks, neural finite differences and complete-wallet batching. |
| Charged surrogate and request VJP | `316423e2b4174bbf072814c1627861469a2e952b` | Eight existing proxy tests pass. Independent Decimal mapper/accounting reference agrees across 14 synthetic paths to `9.095e-12` USDT; 216 request-logit finite differences, including 24 availability releases, differ by at most `1.230e-14`. Two signed drift-reduction paths retain charged exits. |
| Warm restart and exports | `2bf2dc03e1ca3f0594b7b15dcff0cdb5651c5f1d` | Eight resume tests pass, including identical-dropout replay gradients, saved Adam/RNG, interruption recovery and terminal export barrier. Source review confirms current CASH/VOL/CS output slots `0/1/4`; the native adapter appends momentum SHORT at slot `5`. |
| Short contexts | `1291857d53360e4e06a4dd50540c130886deffbf` | Source review checks causal 200-bar eligibility, signal state advancement on the full calendar, covariance-source binding and exact target/availability identities; small development masks inspected without replaying market history. |

[Native accounting script](independent_accounting_checks.py) and
[receipt](INDEPENDENT_ACCOUNTING.json) use hand-derived expected execution prices,
fees, signed funding and NAV rather than production accounting helpers.
[Surrogate script](independent_economics.py) and
[receipt](INDEPENDENT_NUMERICS.json) independently implement scalar Decimal
release/ramp, adverse execution prices, funding, carry, charged reductions and
log-growth/downside utility. The VJP is checked against finite differences of
that reference forward calculation, not against another call to the production
gradient. Neither script trains a model or reads market archives.

The subsequent native result commit
[`6cd153bb57ca3e238ac207124ca5ec45f2ec02bd`](https://github.com/snowycat1234/coin/blob/6cd153bb57ca3e238ac207124ca5ec45f2ec02bd/research/recover-frozen-runner-20261009/temporal-v2-native61-results/README.md)
reported native versus independent NumPy daily-reference differences. The focused
[Torch/reference checker](torch_frozen_path_parity.py) executes the actual v2
Torch objective on both frozen exports at `2bf2dc0…`, using the small original
H1 fragment. Recomputed mapped target byte hashes exactly match the saved native
target hashes registered in that result commit; no native journals were downloaded.
The reference source SHA256 is
`2327fc143824b99a4359580054a9f52b090fa7bbb0022f7c8f029086e1dd7062`.

| Frozen arm | Actual Torch net USDT | Independent NumPy net USDT | Native net USDT, reused |
|---|---:|---:|---:|
| GRU no cash | -592.1827578462326 | -592.1827578462326 | -511.3892651978148 |
| Latest MLP no cash | -365.4136472892187 | -365.4136472892187 | -288.58831311018264 |

All 62 NAV boundaries match exactly in float64. Utility sums differ by at most
`1.388e-17`; cost/funding totals differ by at most `3.553e-15` USDT. Both daily
paths have one charged reduction and paid terminal flat. Across 120 feasible
VOL↔CS request finite differences, maximum absolute VJP errors are
`1.958e-12` / `6.412e-9`. Another 120 sigmoid-logit finite differences, which
avoid very small feasible simplex steps near head saturation, have maximum
errors `2.098e-13` / `2.086e-13`. The receipt is
[FROZEN_TORCH_REFERENCE_PARITY.json](FROZEN_TORCH_REFERENCE_PARITY.json).
Thus the observed +80.79/+76.83 USDT native/daily differences are not a
Torch-versus-reference objective calculation discrepancy. Their precise native
execution attribution was not recomputed here, and the difference alone is not
a new defect. No model was loaded or refitted for this check.

Existing parity tests alone are narrower evidence. The adapter fixtures kept
eligibility constant, which missed the verified defect. Several native scheduler
tests compare paths sharing the same engine/account assumptions; original/v2
surrogate parity also shares original forward assumptions. The added scalar
accounting and Decimal finite differences supply independent checks for the
stated small synthetic cases.

## Reproduction and limits

With the existing numerical environment and resource launcher, run:

```bash
QUANT_ROOT="$REVIEW_CHECKOUT" PYTHONPATH="$REVIEW_CHECKOUT:$REVIEW_CHECKOUT/src" \
  python -m pytest "$REVIEW_CHECKOUT/tests/test_evaluate_requests61.py" \
  -k 'not original_E5_parity and not nonzero_short_append' -q \
  --basetemp "$NEW_STATE/test-adapter" -p no:cacheprovider

python "$REVIEW_CHECKOUT/reviews/economic-code-review-20261009/independent_accounting_checks.py" \
  --source-root "$NATIVE_SOURCE_55AC3D2" --output "$NEW_STATE/accounting.json"

PYTHONPATH="$TEMPORAL_SOURCE_316423E:$TEMPORAL_SOURCE_316423E/src" \
  python "$REVIEW_CHECKOUT/reviews/economic-code-review-20261009/independent_economics.py" \
  --prototype "$EXACT_RECOVERY/source/modules/direct_path/prototype.py" \
  --output "$NEW_STATE/numerics.json"

PYTHONPATH="$TEMPORAL_SOURCE_316423E:$TEMPORAL_SOURCE_316423E/src" \
  python "$REVIEW_CHECKOUT/reviews/economic-code-review-20261009/torch_frozen_path_parity.py" \
  --requests-root "$EXPORT_SOURCE_2BF2DC0/research/temporal-surrogate-resume-v2-20261009/native61-requests" \
  --fragment "$EXACT_RECOVERY/direct_path_fragments/H1_VALIDATE.npz" \
  --prototype "$EXACT_RECOVERY/source/modules/direct_path/prototype.py" \
  --reference "$NATIVE_SOURCE_6CD153B/research/recover-frozen-runner-20261009/v2_same_path_diagnostic.py" \
  --native-helper "$NATIVE_SOURCE_0090A71/research/recover-frozen-runner-20261009/native61.py" \
  --results "$NATIVE_SOURCE_6CD153B/research/recover-frozen-runner-20261009/temporal-v2-native61-results/RESULTS.json" \
  --output "$NEW_STATE/frozen-parity.json"
```

Actual Python verification used the existing one-CPU, 2GB, no-swap/no-GPU portable
launcher in the selected cloud environment; original machine-specific WSL
launcher paths were unavailable. Post-patch adapter tests: **35 passed, 2 NOT_RUN**.
The two original-E5 parity tests require the recovered native mapper source
bundle, absent locally. Its 90MB market-bearing archive was not retrieved just
to obtain source. The actual six-slot path and original release/ramp/combiner
source were exercised directly. Temporal/model/proxy/resume tests total **78 passed**.
Initially batching the suites in one process produced 8 fixture setup errors
because the SHA-bound loader rejects the same module restored at multiple paths;
all affected tests passed in separate suite processes. This is a test setup
limitation, not evidence of poor economic returns.

No additional suspicious issue is elevated to a finding. Funding aggregation,
immediate daily-boundary capacity assumptions, omitted minute marks/latency/lots
and isolated liquidation are declared surrogate approximations. The known
original drift halt and charged v2 correction are not reported as new defects.
These checks do not prove the surrogate is minute-native, that real-market
features have certified historical publication times, or that the model has
learnable alpha. No historical native wallet, real fit, archive reconstruction,
trade, deployment, merge or active-branch modification was performed.

Integration should use a newly hashed adapter contract and bind any subsequent
evaluation plan/export to it. Old immutable contracts and results must retain
their identities. Full historical reruns remain with the existing native task;
they were not duplicated for this review.
