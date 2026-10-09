# Frozen offline runner recovery

The original `scripts/investment/resumable_perpetual.py` is recovered verbatim
from public commit `55ac3d2ee730b1cd1381696330a6abaf1925eb92`, on
`research/multiday-native-labels-20261009`. Its SHA256 is
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.
The older `cc1829…` / `d69e9…` copy hashes to `36c74d0b…75f6d`; the
33-line source delta only adds bounded tape retention. This branch preserves
the exact required bytes, with the existing Decimal account and strategy code.

`baseline.py` is a **new portable adapter**, not recovered original launcher
source. It calls the original five expert recipes, original daily L1 budget
ramp and target combiner, and exact native scheduler. Guard is OFF. No learned
selector code or training pack is recovered here. All paths are relative or
supplied by the caller. `RECOVERY_MANIFEST.json` binds the financial and target
sources; `FINANCIAL_CONFIG.json` preserves the published conditional account
contract and the complete 86-day calendar.

Use this in a saved cloud checkout. Recovery and validation never request data
from exchanges and never open a trading connection. The numerical recipe is
drawn from the published native diagnostics environment; Python 3.12 is used.

```bash
# From the repository root; keep state/dependencies outside tracked source.
uv --cache-dir ../coin-recovery-state/uv-cache pip install \
  --target ../coin-recovery-state/deps \
  -r research/recover-frozen-runner-20261009/requirements.txt

git fetch --no-tags origin research/okx-forward-coverage-20261009 \
  research/okx44-native-results-20261009
python3 research/recover-frozen-runner-20261009/recover.py \
  --destination ../coin-recovery-state

PYTHONPATH=../coin-recovery-state/deps python3 \
  research/recover-frozen-runner-20261009/baseline.py check \
  --state ../coin-recovery-state --output ../coin-recovery-state/PREFLIGHT.json

python3 ../coin-recovery-state/reference44/verify_results.py
python3 ../coin-recovery-state/reference41/verify_results.py
```

Recovery verifies every transport part, concatenated bundle and tar member,
then keeps each original layer separately. The selected view uses the final
published coverage index. The original SOL August 28 partial/API files remain;
the active day selects the distinct `gap-resolution/` files. Exactly one
08:30 UTC trade record follows the retained official archive, with original
API confirm=0 evidence, archive time scope/UTC offset, quote-USDT volumes and
actual retrieval timestamps preserved. Daily and funding bytes remain original.
No interpolation or provider download is performed.

The check command verifies all 430 asset-days and 1,238,400 minute records,
the 3,230 daily history rows and 1,290 funding events, and compares regenerated
targets against the separate published 44- and 41-day account journals. It
does not rerun those accounts. Those independent fresh-account results are
not a stitched 86-day wallet and are never inputs to fitting or tuning.

The explicit `run` command is reserved for a later user continuation. **No
86-day wallet or training has run as part of recovery.** Each future invocation
uses one independent 10,000-USDT account, prior-minute quote capacity, isolated
1x/MMR .005 assumptions, BASE27 costs, signed funding scale 1 and paid terminal
closure. Historical publication, contract/account rules and actual exchange
settlement remain uncertified. This preserves an offline conditional research
runner, not trading/deployment permission or investment qualification.

## Authorized 86-day comparison

`EXECUTION_PLAN.json` freezes the user's subsequent continuation: three serial
fresh 10,000-USDT wallets for VOL, CSMOM21 and fixed 50/50 allocation on the full
July 15–October 9 calendar. `execute_wallet.py` enforces one CPU, one numerical
thread, a 6,000,000,000-byte address-space limit, a 600-second alarm and a 15 GiB
disk reserve. All retained and selected input hashes are checked before each
wallet. No 44/41-day account is stitched or rerun.

Use the full published plan commit SHA, and a fresh output for each policy:

```bash
PYTHONPATH=../coin-recovery-state/deps python3 \
  research/recover-frozen-runner-20261009/execute_wallet.py \
  --state ../coin-recovery-state --output ../coin-recovery-state/results86/FIXED_VOL_HOLD \
  --policy FIXED_VOL_HOLD --plan-commit PUBLISHED_PLAN_COMMIT
PYTHONPATH=../coin-recovery-state/deps python3 \
  research/recover-frozen-runner-20261009/verify_portable.py \
  --root ../coin-recovery-state/results86 --policy FIXED_VOL_HOLD --write-audit
```

The journal-only verifier uses the original independent Decimal cash auditor
and liquidation-event witness adapter, preserved under `verification_helpers`.
It does not import the financial engine. Results, actual execution receipts,
independent audits and all journal bytes belong in the portable result package;
raw market archives remain at the existing pinned public data commit.

The two small source bodies requested by the separate native model worker are
under `auxiliary/`, with original SHA256 and provenance in `auxiliary/SOURCES.json`.
They are distinct from this comparison's financial implementation.
