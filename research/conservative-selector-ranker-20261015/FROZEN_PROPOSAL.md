# Proposed frozen next experiment: conservative linear ranking replacement

Status: proposal only; no new fit authorized or performed by this worker.

Question: can a conservative ranking-oriented linear replacement improve the frozen model's highest-ranked expert choices on the same already-seen development evaluation? This is not clean objective-only causal attribution: the loss normalization, penalty and intercept treatment change. No claim that regularization is equivalent to Ridge alpha 30.

Inputs and chronology:
- Exact original 40 disjoint training dates, all matured strictly before 2023-12-25 UTC; saved fit availability 2024-01-01 UTC.
- Original 60 state-only features, reconstructed using identical 30 consecutive strictly past feedback observations and causally available current expert targets. No market13 features in this experiment.
- Standardize each feature using those 40 rows only, population standard deviation; zero-variance training features mapped to zero in both train and evaluation. Verify this transformation against original scaler semantics; do not unpickle a model merely to fit this new model.
- Original six expert identities, target eligibility, utility labels, ranker provenance, maturity clocks and same 182 scoring dates. No new data or learned ranker fit.
- Evaluate the same preselected 22 dates from the completed diagnostic; retain all 176 mature rows for transparency. This is repeatedly seen DEV, not fresh OOS.

Parameterization:
- Five noncash experts each have a 60-vector and intercept; CASH score is fixed at zero for identification. Thus 305 free coefficients, only 40 independent-date training units. This imbalance is a major limitation.
- Augment standardized x with a final constant 1. Let theta be a 5-by-61 matrix; score for each noncash expert is theta_e dot x_augmented. CASH score is exactly zero.
- Initialize all theta at exactly zero. No random seeds, restarts, searches, early-stop selection or outcome-driven changes.

Exact loss:
- At each training date d, enumerate all original eligible expert pairs i<j whose realized utility differs exactly. Set y_dij=+1 if utility_i>utility_j, otherwise -1. Exact realized ties contribute no pair.
- The date loss is the mean over its pairs of logaddexp(0, -y_dij*(score_i-score_j)). A date with zero unequal pairs contributes exactly zero; do not remove its date weight.
- Data loss is the sum of all 40 date losses divided by 40. Every date has weight 1/40 regardless of pair count. Pairwise examples are not called independent samples.
- Total loss = data loss + (1/2)*sum(theta^2). Lambda is fixed at 1.0, including intercepts. This is one conservative, prespecified shrinkage level; no validation-set calibration, alpha equivalence or penalty sweep.
- Penalizing intercepts as well as weights makes the objective strongly convex even if some pair comparisons separate perfectly. This differs from ordinary Ridge's unpenalized intercept and must be disclosed.

Optimization and stopping:
- Deterministic SciPy L-BFGS-B, analytic gradient, double precision, no bounds, maxiter=500, maxls=40, ftol=1e-12, gtol=1e-8, single BLAS/OpenMP thread. No optimizer fallback or restarting with changed settings.
- One process, 120-second total deadline for the fit/reproduction stage. Save start/PID/end, versions, elapsed time, iterations, final loss decomposition, gradient infinity norm, termination status and all failed attempts.
- Require optimizer success and finite coefficients/loss plus gradient infinity norm <=1e-6. If not, report nonconvergence and do not treat the fit as an accepted challenger. No parameter changes after looking at 2024 outcomes.
- Synthetic analytic-gradient finite-difference, expert-pair masks, equal-date weighting, ties, CASH anchor, causal availability, scaler-only-train and optimizer determinism tests before actual fit.

Comparison and report:
- Original saved STATE_ONLY Ridge forecasts, exact zero-CASH/train-best baseline, and one new ranking replacement. No refitting the old baseline.
- Same frozen argmax ties, all block utilities, mean regret, pairwise accuracy, paired chosen-utility differences, choice mix and oracle diagnostic. Report train loss and train pairwise fit separately from evaluation.
- Scores from a ranking loss are ordinal, not utility forecasts. Do not compare utility MSE directly, feed scores into the old softmax temperature, or create wallet targets without a separate protocol.
- No model/penalty selection based on 2024H1; no annualized return, significance, portfolio-return or live-performance claims. Even improvement would justify another past-only validation design, not deployment.
