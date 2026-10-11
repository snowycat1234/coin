# One next candidate, frozen and NOT_RUN

Registered after the two-control diagnostic. This document is a prospective plan;
no third control has been calculated in this task. No new data are implied.
All original protocol/results remain intact. No learned model or threshold search.

## Question and single control

Does the frozen qLSTM's non-Gaussian shape add proper-score information beyond
its own conditioned first two moments? The new EWMA zero-mean control narrows
the gap to0.99699986%; it does not match the model's learned market multiplier,
conditional drift or variance. A moment-matched structural ablation addresses
that remaining attribution question with no training or new neural inference.

For each original saved 2265-window forecast, integrate the **saved** piecewise
quantile function over u∈[0,1] to get mu=E[r] and var=E[r²]−mu², retaining its
original endpoint atoms. Build the standard Normal quantile grid z=Phi^-1(taus)
at the same 37 fixed probabilities, with the original piecewise-linear quantile
interpolation and endpoint atoms. Integrate this fixed standard-grid function
once to get m_z and v_z, then define the control quantiles as
q_control=mu+sqrt(var)*(z-m_z)/sqrt(v_z). These closed-form constants depend only
on the frozen quantile grid and representation, never outcomes. The resulting
Normal-shaped control has **exactly** the same represented mean and variance
as the frozen model. No constants have been computed yet in this task.
No loss/running-volatility refit, floor grid, new features, new loss, quantile map,
tail extrapolation or alternative control is allowed. Nonpositive/nonfinite
variance stops; do not insert a tuned floor. This is a structural shape ablation
of the learned conditioning, **not** an independent freely estimated Gaussian
baseline, and cannot claim causal architecture superiority.

The represented control remains a finite-grid Normal shape rather than a true
continuous Normal. Report the fixed grid-moment constants and check represented
moment identity; distinguish its continuous Normal location/scale parameters
from mu/sqrt(var). It shares original endpoint limitations, so it does not
validate extreme tail support. No iterative rescaling or score-based adjustment.

## Population and decision fixed before computation

Only original saved predictions 2265×22 and source-bound sample identities,
previously seen2023/2024 development data. Primary: model minus single-control
CRPS and relative gain. Use original eleven44-day jointasset/stratified calendar
clusters,2000 replicates,seed271199, plus all three old periods separately.
Secondary: original tail pinball/coverage, q99 exceedance occurrence count,
unique label counts and known overlap. Do not estimate IID precision from49830
overlapping occurrences, pick a period, choose a confidence interval, or change
the existing1% minimum-gain /1.05 tail-pinball-ratio /.01 calibration-increase
criteria. Compute the criteria as a new ablation result without rewriting old PASS.

If gain<1%, upper paired interval>=0, tail loss ratio>1.05 or calibration-error
increase>.01, record NO_RELIABLE_SHAPE_INCREMENT_FOR_THIS_RECIPE and stop.
Passing these development criteria only supports another bounded hypothesis;
it does not license economic replay or a new sample-out-of-sample claim.
No units/funding certification is supplied by this shape test.

## Resources, verification and stop

Exactly1 analytic control,0 fits,0 new inference,0 native wallets,0 downloads.
One fresh STATE directory. Bound120seconds,4threads,GPU0,7.5GB address-space cap,
swap0 and15GB disk reserve; outputs<=5MB. Verify oldprediction SHA
05f17100207dc36b30c62d4fbf8de8c500660d82d234639be09a6775da857b09 before loading.
Stop on hash/shape/date mismatch, invalid variance, nonfinite or resource breach;
retain every attempt. Before computation, commit/push its implementation and
confirm remote SHA. Independently check representative moments and actual-return
axis CDF scoring. Preserve original model/protocol/forecasts; append result only.

This task stops at this frozen plan. The current diagnostic's two-control cap is
the reason for NOT_RUN; there is no pending approval request or environmental
blocker for the completed diagnostic. Tail recalibration and economic policy
changes would require their own complete validation/data-role contracts.
