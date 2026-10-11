# Frozen minimum distribution pair

Registered on 2026-10-11 before any historical model fit or comparison. Parent
source is `546cb9bd4e508020e9e24dfd30059496b82f3f8e`. This independent branch
does not change Momentum Transformer or any existing wallet/collector files.
The 2026-03-01–2026-09-01 collector lock is never opened. Original unpublished
Q1/Q2 native ledgers remain missing; price recovery is not ledger recovery.

Hypothesis: one small two-stage qLSTM adaptation improves a recent-22-day
conditional Gaussian distribution on proper scores and calibrated tails.
One configuration, one seed, one fit. No Optuna, threshold search, ensemble,
qHybrid, hyperparameter repair after outcomes, or automatic promotion.

## Target and causal contract

At UTC completed-day boundary D, predict one common marginal distribution for
the next 22 **individual daily log returns**, not their sum or joint path.
All features use completed bars available at or before D. Source OHLCV tables
are read with a strict whitelist: dt, high, low, close, quote_volume,
complete_kline. Economic/future columns and supplied regime labels are not
features. Historical availability is the existing completed-day proxy, not a
certified original publication timestamp. Compare the reused close changes
to the archived causal mom1 feature wherever observed, and preserve holes.

Use CORE5 in the explicitly named order, without outcome-based asset admission.
The source archive and every member are SHA/CRC checked; original exchange raw
ZIPs are not in this feature packet, so a fresh raw checksum claim is excluded.
Source tables are evidence for a **new whitelisted daily adapter**, not a
wholesale import of the prior feature payload. No forward fill. Any sample
needs 22 contiguous past observations plus its 22 contiguous mature outcomes;
missing samples and reasons are counted. No calendar is compressed across gaps.

2021 Jan–Sep is TRAIN, Oct–Dec is VALIDATION. Stop label maturity strictly before
each role's exclusive end; purge boundary-straddling targets. Select only the
best validation epoch, copy state tensors deeply, fit feature normalization on
training input rows only, then freeze. All 2023, July–August 2024 and Q4 2024
are chronological **already-seen development evaluation**, never pristine OOS.
Each block's labels mature strictly before its exclusive end. Do not update
model/scaler in evaluation. Use daily origins; overlapping windows and common
market shocks require paired date-level uncertainty, not IID asset-day counts.

## Fixed model, control and scores

Control: normal quantiles with the same asset's known last22 mean and sample
standard deviation; sigma floor 0.0001 daily log return. No fitted threshold.
Adaptation: PyTorch asset LSTM16 and market LSTM16, one layer each, dense16
ReLU heads, 37 original quantile levels and sorted normalized quantiles.
Asset features are daily return, log high/low range, log1p quote volume and
causal EWMA volatility; market features are CORE5 observed return/volatility
means. Normalize X and Z using TRAIN only. Future labels use the origin's
known EWMA sigma, not future sigma. Raw quantiles equal normalized quantiles
times origin sigma times a positive learned market multiplier. Train the
paper-style sum of raw-percent and normalized multi-observation pinball losses.
Initialize quantile-head biases from standard normal quantiles. Max40 epochs,
patience8, AdamW .001, weight decay .0001, batch128, seed271198. No auxiliary
cheat loss. This is a reduced COIN adaptation, not an exact paper replication.

Primary CRPS is computed exactly for the CDF defined by linear quantile
interpolation with fixed endpoint atoms. Both forecasts use this same full
distribution representation. Report unweighted pinball at all37 levels as a
separate proper quantile-vector score; no density-smoothing parameters are fit.
Report lower/upper1% and5% pinball, exceedance calibration, coverage90%, PIT
histogram, expected short upper-tail loss, and day1 scoring separately. Extreme
0.005% tails are not identifiable from this sample; no extreme-tail claim.

For uncertainty, average assets and the22 outcomes per forecast date, group
consecutive origin dates in nonoverlapping44-day calendar clusters within each
evaluation block, resample whole clusters jointly for both forecasts2000 times.
Each cluster retains its actual count. Report 95% paired percentile CI and
cluster count. Boundary dependence remains possible; few clusters limit power.
Also report each block separately; no claim of independent five-asset markets.

Proceed to economic testing only if all of: pooled CRPS gain>=1%, upper95% CI
of model-minus-control CRPS<0, pinball improves,1%/5% tail pinball<=1.05x control,
max tail calibration error increases by<=1 percentage point, and each calendar
block's CRPS is no worse. This gate cannot be relaxed after seeing results.
If it fails, PAUSE this recipe and do not refit or run new wallets.

## Economic boundary

P(r<0) is not P(short net>0). For one fixed-entry short unit, a one-day return r
has price profit `1-exp(r)` per entry notional; entry and exit fees/slippage are
charged on their respective notionals, signed funding is included. Rebound loss
grows as exp(r); larger holding periods need joint returns, funding and path
survival, which this marginal model does not supply. A fixed probability/utility
mapping may be used only after day1 calibration and complete native inputs.
No evaluation-period threshold selection. The existing frozen native1x engine,
full10k capital,30% per asset/60% gross caps and paid closure remain prerequisites
for a net strategy claim. July2024 has actual missing mark minutes, while Q4 has
complete minute tapes; this difference must not be hidden. Failed distribution
gate means economic wallets NOT_RUN, not zero profit and not failed engine.

## Budget and preservation

CPU only,4 threads, <=7.5GB address space within shared8GB research budget,
30-minute command bound,15GB disk reserve, <=1GB task-state output. Reuse existing
runtime and public Git objects, zero provider redownloads. Cloud adapter replaces
only inaccessible WSL paths, not old safeguards or authorization. Store models,
row predictions and derived data outside tracked code; commit small results and
their SHA. Record every execution attempt, successful or failed. Stop on source
mismatch, boundary violation, resource breach or failed distribution gate.
