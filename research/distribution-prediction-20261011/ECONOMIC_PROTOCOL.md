# Fixed economic translation probe, phase2

Registered after the frozen phase1 fit/scoring and before inspecting any phase2
profit result. The phase1 recipe/seed/model/scaler remain unchanged. Relative
distribution gates passed, but upper1% tail exceedance is3.14% rather than1%:
that is not reliable absolute tail calibration. This phase checks whether the
small scoring improvement can supply meaningful net short decisions.

Use existing CSMOM21 negative targets from the immutable92-day Q4 producer at
recovery546cb9bd; do not port or refit Momentum Transformer. Existing targets
are causal context only, no realized wallet NAV/teacher labels enter the probe.
Use the complete Q4 actual00:01 prices and signed held funding coefficients
from data152606ad. Verify consumer/member SHA before access. No provider download.

The probe is a paired **one-day unit-notional diagnostic** on each existing
CSMOM21 short opportunity, not a replacement native wallet. Both distributions
use identical opportunities, price outcomes, fees5.5bp and execution8bp per side.
Adverse entry/exit fill prices determine fee notionals. For r=log(Pexit/Pentry),
`net = (1-e)(1-f) - exp(r)(1+e)(1+f) + signed_funding_coefficient/Pentry`.
Positive funding is a receipt for a short. Record price, fees, execution and
funding separately. Future funding never enters a decision. Expected funding
uses the last complete *strictly earlier* interval coefficient normalized by
its own entry price: at UTC00:00 use intervalt−2, whose00:01 end precedes D.
The first two Q4 days have no qualifying saved lag and stay no-decision for
both arms; this is a predeclared availability rule, not selection by outcome.

Freeze only the natural break-even decision `expected net > 0`, no probability
threshold or evaluation search. Expected exp(r) integrates the same piecewise
quantile distribution exactly. Profit probability uses the cost/funding-adjusted
return cutoff, not r<0. Run both preserved funding-unit interpretations(scale1
and.01), report both, never choose the more profitable interpretation. The price
outcome is actual daily execution-to-execution; forecasts were trained on
completed-close log returns, so report this clock/basis mismatch explicitly.

Report all445 asset/day available observations, existing short opportunities,
selected/declined counts, Brier profit calibration, observed downside-yet-net-loss
cases, selected net components per unit, blocked winners and avoided losers.
No standalone capital return/APR is inferred; independent units cannot be
summed as a portfolio. Daily forced round trips omit multi-day inventory netting,
minute capacity/partial fills, funding ownership during delayed fills, margin
and liquidation survival. Expected upper-tail losses and realized rebound losses
remain explicit. Missing values stop; do not substitute0 for unknown funding.

Only consider a subsequent frozen native account pair if, under **both** funding
interpretations, model accepts>=20 actual short opportunities, its paired daily
unit utility gain has positive lower95%44-day cluster CI, selected net unit mean
is positive, profit Brier is no worse than Gaussian, and observed upper1% price
tail exceedance<=2%. These are sufficiency gates for spending further replay
budget, not investment qualifications. No passes means stop the economic recipe
without training repair, threshold tuning or new wallets. Existing full10k native
controls remain untouched; actual shared capital/caps/paid closure would still
be required for a strategy net-profit claim. Given the score-stage tail miss,
not proceeding to a wallet is a valid informative outcome of this minimal test.
