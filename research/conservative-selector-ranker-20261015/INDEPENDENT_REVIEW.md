# Independent no-refit verification

PASS. The independent reviewer invoked no optimizer and performed no fit or refit. All saved predictions, 176 mature decisions and 22 frozen blocks reproduce exactly. Training-only means/scales match exactly; 40 dates, 60 features, 10 constant columns and the zero-CASH anchor are verified. Independent manual loss and gradient match saved values. Finite-difference error across all 305 coefficients is 6.31e-11; gradient infinity norm is 2.25e-8.

Original source features, saved Ridge forecasts, original block dates and 222 learned-expert provenance clocks were independently checked locally. Private source details remain outside this packet. Fourteen nonoptimizer synthetic tests also passed with optimizer calls disabled. Existing optimizer-determinism logs were inspected, not rerun.

The retained receipt records one actual converged fit followed by a reporting serialization failure; the original failure remains. Recovery reused saved coefficients. The available record supports one actual fit but cannot prove absence of unrecorded execution. Actual fitting occurred October 15, 2026; January 2024 availability is a simulated historical cutoff, not contemporaneous issuance.

The challenger improves mean chosen reference utility over saved Ridge by 0.00117070, with 8 better blocks, 8 worse and 6 ties. It remains worse than CASH. Ordinal scores have no utility-MSE comparison, wallet use or deployment interpretation. This is repeatedly seen development, with 305 parameters and only 40 independent training dates.

Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python independent_saved_check.py` to independently recompute scaler, loss, finite-difference gradient, forecasts and decisions using only this packet. The checker does not import the author's ranker or any optimizer. Source identity and external historical-publication assertions cannot be established by the portable checker alone.
