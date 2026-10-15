# One frozen conservative ranking challenger

This standalone packet contains one new model, its immutable fitted coefficients, derived training/evaluation inputs, complete results and tests. It contains no original model pickle, source archive, original source fingerprints or private source locations. It needs Python 3.12, NumPy, SciPy and threadpoolctl; the actual-fit versions are in FIT_RECEIPT.json.

## Reproduce without refitting

Run from this directory:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m unittest -v test_ranker.py
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python ranker.py reproduce
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python independent_saved_check.py

The first command runs synthetic tests only (including two synthetic optimizer executions to test determinism). The second uses the supplied coefficients and requires exact equality with RESULTS.json. The third command independently checks the saved scaler, gradient, forecasts and decisions without importing the model implementation or an optimizer. None refits actual data. Do not delete FIT_RECEIPT.json or run another actual fit. The fit-once code is retained for methodological transparency; an existing receipt prevents accidental reruns.

## Contents and outcome

- FROZEN_PROPOSAL.md: unchanged pre-experiment protocol snapshot; its proposal-only status describes the time it was frozen, before this authorized execution
- ranker.py: frozen loss, gradient, solver and saved-coefficient reproduction
- coefficients.json: the sole actual-fit 5-by-61 coefficient matrix plus train-only scaling
- derived_inputs.json: 40 original mature training dates, 182 original scoring states, 176 mature labels, saved STATE_ONLY forecasts and original 22 preselected evaluation dates
- RESULTS.json: every block, all 182 scores, all mature utilities and paired outcomes; training fit separately
- FIT_RECEIPT.json: original run receipt, including the post-fit serialization failure
- REPORT_RECOVERY_RECEIPT.json: saved-coefficient reporting recovery, no refit
- optimizer_output.json: original saved optimizer parameters and acceptance status
- test_ranker.py and test/reproduction logs
- REPORT.md: findings, full block table and limitations
- independent_saved_check.py, INDEPENDENT_CHECK.json and INDEPENDENT_REVIEW.md: independent no-refit verification
- FILES.json: final portable-file manifest; hashes identify new deliverable files, not private original source artifacts

Fourteen synthetic tests passed before the actual fit. A fifteenth serialization regression test was added afterward. The sole actual optimizer converged; result export then failed on a NumPy integer. Only its reporting conversion was fixed, and the successful saved coefficients were evaluated without restarting optimization. The original failed-stage receipt is intentionally retained. The recovery completed within 19 seconds of the original start. The private original traceback is retained outside this clean packet because it contains local paths. Reporting also explicitly leaves pairwise accuracy undefined for the fixed CASH policy: its fixed action is not a full ordinal forecast.

This is repeatedly seen development, not fresh out-of-sample evidence. The new model was actually fitted on 2026-10-15; the historical cutoff is simulated causal availability, not a claim that forecasts were issued in 2024. Scores are ordinal, not utility forecasts or wallet instructions. See REPORT.md.
