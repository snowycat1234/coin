SAVED DISTINCT-FAMILY RISK / EXPOSURE / COST EVIDENCE

Scope
This isolated module reads completed, independently approved saved 2023/2024
annual STATIC50 and VOL_MANAGED_HOLD outputs at LOW/MID/HIGH. It preserves the
original 18-cell frozen cohort and all six H090/STATIC exact duplicate groups.
The analysis has12 cells and six matched year/tier pairs, with fresh10000-USDT
annual accounts. No financial account is constructed, no chronology is replayed,
no raw data or covariance is read, and no policy/model/threshold is retuned.
Frozen source, policy, prep and original evidence are never modified.

Imports: Python standard library and numpy only. No account/provider/financial
runtime imports. CPU6 and one numerical thread are required for derivation/tests.
The initial verified publication parent is48e42f4040e317edf732bfedc9dce5d54e29ed12;
publication and any later parent update remain the root's responsibility.

Input gate
Use a small explicit input JSON:
{
 "parent_authorized_saved_family_risk_final": true,
 "parent_commit": "48e42f4040e317edf732bfedc9dce5d54e29ed12",
 "comparison": {"path": ".../MATRIX_COMPARISON.json", "SHA256": "..."},
 "comparison_index": {"path": ".../FINAL_SAVED_EVIDENCE_INDEX.json", "SHA256": "..."},
 "exact_path_signatures_addendum": {"path": ".../EXACT_REALIZED_PATH_SIGNATURES_ADDENDUM.json", "SHA256": "..."},
 "frozen_manifest": {"path": "bounded_native_continuation_guard50_exit_expansion_20261015/FROZEN_SEVENTEEN_CELL_MANIFEST.json", "SHA256": "0c08a0c362c8222d2dc16735f7ebf11a26f4892999bc57b3b062d189ff050638"}
}
All18 normalized rows must be independently approved and calendar-complete. The
comparison must bind the exact parent-authorized all17-terminal evidence index.
The new module rehashes every case/risk/finance reference it uses and the original
saved MINUTE archive, then validates the exact37 columns, finite float64 values,
strict minute clocks, positive NAV and signed-asset gross/net projections.
The reused2024 MID case uses its original exact receipt and original finance
review plus the independently approved supplementary/transported risk proofs.

Commands (run from workspace root)
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 POLARS_MAX_THREADS=1 taskset -c 6 python -m unittest discover -s saved_distinct_family_risk_evidence_20261015 -p 'test_*.py' -v

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 POLARS_MAX_THREADS=1 taskset -c 6 python saved_distinct_family_risk_evidence_20261015/saved_family_risk.py --workspace . --index INPUT.json --output NEW_OUTPUT_DIRECTORY --authorize-saved-final

Final outputs are immutable/new-directory-only. No final derivation may run
without parent authorization. A completed module still requires fresh independent
review before root publication. The module itself never publishes or commits.

Definitions
- Raw paid annual return is the native exact approved terminal NAV/10000 minus1.
  HOLD minus STATIC uses paired full-year paid returns only. Conditional model
  settlements and halted prefixes cannot be presented as paid annual uplift.
- Deterministic saved-float64 minute returns are nav[t]/nav[t-1]-1, with initial
  denominator10000. Only their canonical little-endian f64 hash and small summary
  are retained; the original minute array stays local.
- Daily NAV is the last of1440 exact observations. Daily simple returns use the
  initial10000 denominator. Realized annual volatility is std(ddof=1)*sqrt365,
  including leap-year2024; no interpolation, missing-day imputation or flat tails.
- Native all-observation MDD is preserved from authoritative native proofs.
  Minute-close MDD and complete-daily-close MDD are separate telemetry measures.
  None supplies an intraminute bar-high/low price path.
- Gross/net/asset means and extrema, time flat (all actual quantities exactly0),
  free-cash minima and isolated-margin maxima are post-transition minute-close
  observations. Annual means use published daily sums divided by exact minute
  counts. These differ from direct numpy minute means only at possible summation
  roundoff; the original independently reviewed fields are retained and checked
  at1e-12 relative-to-max(1,|a|,|b|) scientific scalar tolerance, never monetary
  ledger tolerance. Saved native monetary projections must equal the exact f64
  projection of the approved Decimal text at the terminal observation.
- Fees and execution-price friction are positive costs. Signed funding is a NAV
  credit when positive and debit when negative. fees+execution-funding is a
  descriptive same-quantity drag, not a separate subtraction from already-net
  returns. The original native gross-mid-price same-executed-quantity PnL bridge
  and native bridge residual are copied without ledger reconstruction. Execution
  friction is already inside realized execution-price PnL; do not subtract twice.
- Forecast-budget overshoots, max excess and count are copied from the approved
  frozen-covariance risk report. Their definition is held signed weights times
  strictly-past daily covariance, sqrt(w C w); breach count tolerance1e-10.
- Warning counts are per-symbol initial Guard50 warning signals with approved
  paid-exit evidence, not necessarily unique portfolio days or independent events.
- Raw precision100 captured-delta residuals remain visible in their original
  schema. Native40 chronological terminal proofs are authoritative; diagnostic
  higher-precision subtraction residuals are neither repaired nor new cashflows.

Compact evidence and reproducibility
RISK_EVIDENCE.json and CELL_EVIDENCE.json retain native exact amounts, risk
metrics, original reviewed rows, source/quality/code/policy/prep/GO/review bindings,
minute archive sizes/hashes and canonical values/ordered-column signatures.
DAILY.npz is lossless float64 derived telemetry: endpoint NAV/return, daily sums
and extrema of signed/absolute gross/net/asset weights, exact flat minute counts,
cash/margin extrema and cumulative paid costs/funding/turnover endpoints/changes.
Canonical value hashes use little-endian float64 C-order bytes; ordered column
names use canonical UTF8 JSON. Original dtype/shape/raw-byte descriptors remain
separate. Changed columns, one-bit values and signed zeros alter signatures.
ORIGINAL_18ROW_COMPARISON.json preserves the original cohort.
EXACT_DUPLICATE_EVIDENCE.json additionally preserves all six exact H090/STATIC
path proofs and independent strict canonical financial/array signatures without
adding H090 duplicate paths to the two-family count. Our six STATIC f64 value
signatures are checked against that independent addendum. CSVs are convenience displays; JSON
and NPZ retain unrounded values. COMPACT_ARTIFACT_MANIFEST.json pins all outputs.

Public compact verification, without original minute outputs:
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 taskset -c 6 python saved_family_risk.py --recompute-compact OUTPUT_DIRECTORY
It checks every file hash, lossless daily signatures, daily-to-annual aggregates,
native annual-return/cost arithmetic, descriptive ratios and all six raw pairs.
All-minute MDD/exposure/return-hash deep revalidation requires the omitted original
hash-pinned MINUTE.npz archives; compact daily records cannot establish it alone.
Exact financial ledger reconstruction also requires the separately omitted native
ledger/chronological proof records. No full minute NPZ is uploaded in this module.

Interpretation
All results are adaptive seen-development evidence, not OOS or independent alpha.
Equal nominal tiers do not produce equal realized risk, gross, net, drawdown or
cost. 2024 NAV/weights/forecasts retain the original bound carry-forward/unknown
causal-mark-quality sidecar; they are frozen-model telemetry, not certified
exchange prices/execution or true-market risk. All fixed-calendar observations
are retained. No outcome/quality-selected subset or new quality rule is used. Separate annual accounts cannot be multiplied into a continuous two-year
return or CAGR. Native venue/funding/filter/liquidation assumptions are uncertified.

The optional return/realized-volatility and return/mean-gross ratios use full-sample
future observations. They are descriptive, future-informed arithmetic only. No
scaled-trade/cost run is executed, and they establish no executable advantage,
OOS performance or alpha. There is no scaled return curve and no new backtester.
A possible future causal past-only normalization rule is discussed separately in
saved_distinct_family_risk_comparison_plan_20261015/NEXT_MODULE_RECOMMENDATION.md.
That proposal is not implemented or approved for execution by this module.
