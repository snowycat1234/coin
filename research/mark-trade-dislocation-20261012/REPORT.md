# Fixed same-contract mark/trade conditional increment

The single recipe stops at its frozen information gate. Adding strictly past
`log(mark_close/trade_close)` to the same own-price daily return control did not
establish a repeatable conditional prediction increment on both mandatory old
calendars. Project remains ACTIVE; no conditional economic reference or native
wallet was started. This is a cryptocurrency adaptation experiment, not an
original-paper replication or a new unseen-sample result.

| Full old calendar | Control normalized MSE | Candidate normalized MSE | Relative MSE gain | Joint daily loss improvement 14-day 95% CI |
| --- | ---: | ---: | ---: | --- |
| 2023, 365×5 | 0.3253148896952325 | 0.3270616850087429 | −0.536955% | [−0.00481422405, +0.00102664719] |
| 2025, 365×5 | 0.3492651282955829 | 0.34829789313187837 | +0.276934% | [−0.00006978989, +0.00195157586] |

Both completed-source gates PASS. Both ≥2% relative gain and positive CI-lower
gates FAIL. CIs concern normalized forecast loss, not cash returns. One pair of
five-asset deterministic OLS systems was fit: control intercept+own-price and
candidate intercept+same own-price+gap; 10 systems, 2 fit groups, no stochastic
training seed, no grid/regularization/threshold/refit rescue. Circular 14-day
calendar bootstrap, 1000 draws each, seeds 811750/811751, joint asset-day loss.
The small 2025 positive point estimate is retained, without an advantage claim.

## Sources, clocks and mature common cohort

Decision is UTC00:00. The preceding day's actual 23:59 minute trade and mark
closes share source open/close timestamps; conservative candle completion is
00:00. Current full-day source completeness is known then. The extra feature
uses that same contract's reference mark; mark is never an entry/exit price.
Own-price feature is `log(T[d]/T[d−1day])`. Label is actual trade 00:01 OPEN to
next day's 00:01 OPEN, `p1/p0−1`; conservative maturity `d+2 days` must be
strictly before 2023-01-01. Bar completion is an availability proxy, not an
observed exchange-publication/network-arrival or native-fill certificate.

Actual 2021/22 natural training calendar has 730 dates. Git-certified mark/trade
history supplies 699 completed pair days, with 27 mark minute gaps on two July
2022 days. 697 all-five completed pair decisions, label/previous-close unknowns
and the strict maturity rule yield exactly **690 common mature training dates**.
Both arms use these same indices and train-only feature means/std (ddof=1), and
the same five train-only return standard deviations for loss comparison. No
teacher utility, positive-return, old `known` or `training_indices` selection.
Each mandatory validation year has every 365 natural dates and 1825 asset pairs.
All exact admission, UNKNOWN and purge dates are in public PREPARATION.json.

Boundary repair restored only 2022-12-31 and 2024-12-31. Ten small official
Binance USD-M daily trade/mark ZIPs were acquired for the former: **413286 bytes**,
official CHECKSUM/CRC/OHLC/1440-minute identity checked. All ten 2024-12 monthly
originals were reused from immutable Git `d69e9ac94478c5be54cb46c622afec7aaf3c61f7`,
with bytepart, wrapper, member and official-checksum hashes and full monthly
grids validated before projecting the final day. No duplicate provider download,
retry, alternative venue or full December2022 recovery claim. Boundary time
13.599460s; projection 0.764166s. Original 2022/2024 source scopes are historical
development, with no protected 2026 or unknown reserved body access.

Train mark: `c4f44417a665ded2c43e6767221efea004d90dd1`,
MARK_DAILY_CONTINUOUS.npz SHA256 `0ec957375b831255920e90b9d9221ca0422731580faae436576b57fb07daeb74`.
Train trade: `0d6db3fd515eea5de421bce6cf7123b3e15ec55f`,
DAILY_CONTINUOUS.npz SHA256 `9a0e63c0b4f93b185310c65892d424e99307a6678930b5d559e421a1145edde9`.
Actual price labels/cube: `53056adaa3b54f93ef6859269106ac288331dd9c`,
INPUTS.npz SHA256 `e33cc15bd53167078252f7d58b406960d543ccb92421f430214e5360971f12f4`;
column identity is bound to that original preparation's symbol_order.
Validation original minute sources: `f38617c5a0917490c8b90fba355ecf0d5f1b87f4`
(2023), `534a18fbed0ec7a2f7ffbb298526c51b1a2a696c` (2025), exact canonical
monthly NPZs, actual aligned daily-end trade/mark values. Raw trade daily closes
and the existing economic input cube are bit-exact at their compared clocks.
Frozen actual OPEN/funding/risk inputs reuse `53357f33f4e6ccb536af762fbff39b269c24d837`;
funding and risk are retained source columns, not predictive oracle income.

## Dedup and retained prior research

69 public heads, 1702 readable source/protocol identities and 227 related items
were reviewed. V7 actual basis `perp_trade/spot_trade−1` and V8
`log(spot_trade/perp_trade)` express the same spot/perp information, while this
feature uses the same perpetual contract's mark/trade pair. V7 24-fit queue STOP
is preserved; V8 full478 cache/strictOOF/P1 is NOT_RUN/NOT_READY, not falsely a
failed fit. Old daily premiumIndex uses the actual premiumIndex feed; the old
mark-minus-spot diagnostic is zero-fit valuation. No equivalent same-contract
prediction experiment was identified in this bounded search; compressed history
was not exhaustively proved absent. Source December2022 hash-only receipts were
not misrepresented as recoverable source bodies. See evidence/DEDUP.json.

Original Slow Momentum with Fast Reversion research remains separately frozen
in research/slow-momentum-cpd-20261011 at b5543c953436dbd75cd09d966ed2158c2d86c3dc:
LSTM trend plus training-fitted GP change-point location/severity, implicit fast
reversion, traditional futures paper results with no crypto guarantee. Its prior
six-fit paired adaptation failed its information gates. The later official
repository's Transformer and stopped selectors were not repackaged here.

Both preceding positive FOLLOW native candidates remain saved: +1027.949323 and
+388.663239 USDT with risk gates passing and cash-path CIs crossing zero. Their
STOP concerns that conditional posthoc path gate, not deletion of candidates.
The 2025 controls have separately paid exits at d046cc66, with different endpoints;
those tails are not appended to same-calendar comparisons, nor described as
never having exited. All 23 original native snapshot byte hashes are preserved.

## Publication, tests and reproduction

Normal pushes were verified against remote SHA before each scientific stage:
freeze `7da7b67174aed5f0d794e51163f8352fafc73970`; original cube identity repair
`d9840f6832cc9c017982cfdb2875389bb93ae272`; mature/source packet
`e1400a51f7188f3d4d5550af59b2bb5d717d04e3` before fit; coefficients
`676b4eb81e900cb71d6986e63d2cc5be39831a9a` before either score; scores/cold code
`d0adcbc10e0fe980e3361d3233df44acc7a9888c`. Fit 0.089040s, score 0.196823s.
Two source-preparation attempts: first failed on a missing legacy symbol_order
field before any fit, then ordinary identity binding fixed; failed directory/log
is retained. Two earlier metadata schema lookup failures are also retained.

Four meaningful synthetic causal/maturity/shared-cohort/degenerate-channel/grid
tests PASS (1.08s). Synthetic test data are not real historical results. Full
repository suite NOT_RUN. Actual preparation, scoring and public cold identities
passed; no test silently runs a financial account.

Public INPUTS/MODEL/SCORES packets total **1218950 bytes** and 29 members; all exact
source features, model, forecasts, losses, original bootstrap starts/means and
new daily ZIP originals can be restored. Prior monthly original bodies remain
bound by immutable existing Git/member/checksum references rather than reuploaded.
Fresh public GitHub filtered shallow clone/sparse checkout restored packets in
0.435434s and checked 7300 saved forecast scalar matrix values and 2000 saved
bootstrap means, exact bits; maximum stored-OLS normal-equation residual
3.5346820472459033e−15. Those are verification arithmetic, with **zero new fits,
RNG draws, provider GETs, account advances or original experiment STATE opens**.
Cold verification validates stored daily raw ZIP bytes/checksums and monthly Git
reference identities; it does not rerun the full historical minute-source parse.

From this branch's checked-out repository, with the existing environment:

```bash
bash research/mark-trade-dislocation-20261012/reproduce.sh /workspace/mark-trade-reproduction
```

Use a new destination for another run. No model refit or bootstrap resampling is
needed. Fixed one-CPU/thread, 4GB per-process address space, sampled descendant
RSS stop2GB, hoststop8GB, swap0/GPU0 and 15GiB disk reserve remain unchanged.
Resource receipts and all 23 original snapshot bindings are in evidence/COMPLETION.json.
All source/config hashes are in SOURCE_SHA256.txt. No other distribution-study
files, lost2026 ledger fiction, Library, keys, credential creation, pay/live/
deployment/main/force push. No source/permission blocker remains for this module;
economic execution is intentionally NOT_RUN because the information gate failed.
The next independent mechanism metadata decision is in NEXT_MECHANISM.json.
