# Authorized execution of the frozen moment-matched shape ablation

The user now explicitly authorizes execution of NEXT_EXPERIMENT_PLAN.md from
16bb693eeccf9cec19dd3b72c7ac8f159c982013. Its historical NOT_RUN statement remains
intact. This addendum permits its one fixed control, superseding the prior task's
two-control cap for this execution only. Preserve all earlier artifacts/results.

The formula,37 quantiles,2265×22 observations,eleven44-day joint-asset calendar
clusters,stratification,2000 replicates,seed271199 and original gates are unchanged.
Use only saved raw-log-return model forecasts and labels. The raw forecasts were
already transformed as normalized_quantiles*causal_origin_sigma*positive_factor
by the original implementation. Match moments **after** this transformation;
never load a model or run new inference. No market archive download/read needed.

Report paired absolute CRPS difference and paired relative-gain percentile CI
using the same cluster draws; report all three original periods. Preserve the
original gates as a registered decision, not an economic significance boundary.
The earlier0.99699986% versus1% is only a point-estimate gate result. Reuse saved
A1 per-window scores solely to report its paired relative-gain interval on the
same draws, without another distribution, score fit or threshold search.

Verify all2265 represented raw-log-return means/variances after the single fixed
standard-grid affine normalization. Report continuous-Normal location/scale
separately: these need not equal represented moments. Independently integrate
representative moments and E[exp(r)] with scalar quadrature and proper CRPS over
the actual return axis. Do not confuse a log-return distribution's moments with
simple-return moments; E[exp(r)]−1 is reported as a representation diagnostic,
not an economic policy or expected tradable payoff.

Keep the original endpoint atoms unchanged. Report their mass/support and actual
labels beyond support, both occurrence and unique asset/label counts. For the
Normal-shaped reference, analytically separate clipping at the existing endpoints
from interpolation/affine-normalization effects on log moments and E[exp(r)].
No additional scored control, tail extension or fitted calibration is allowed.
Unknown true model tails beyond finite support remain unknown.

Bound main execution and independent verification to120seconds each,4threads,
7.5GB address space,GPU0,swap0,15GB disk reserve,STATE<=5MB. Exactly1 new analytic
control,0 training,0 new neural inference,0 wallets,0 downloads. Commit/push
implementation/tests and confirm remote SHA before historical calculations.
Retain all attempts; stop on identity/shape/nonfinite/variance/resource failure.

After reporting the registered gates and uncertainty, push and verify remote SHA.
Then stop **all additional experiments for this recipe**, regardless of outcome.
No proposed next trial or tradable-return claim follows this ablation. Everything
remains previously seen development validation; collector locked data untouched.
