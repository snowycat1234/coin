# Completed-path jump-share risk information experiment

One fixed recipe failed its frozen information gates. Adding past completed-day
RV−BV share to the matched HAR/semivariance/price/sampling-ratio control did not
improve next-day realised-variance prediction on both complete old calendars.
Project remains ACTIVE; economic references and native wallets are **NOT_RUN**.
These are risk forecast losses, not investment returns, profit or losses.

| Calendar, complete365×5 | Control meanQLIKE | Jump meanQLIKE | Relative improvement | Joint daily loss increment 14-day95CI | Assets improving |
| --- | ---: | ---: | ---: | --- | ---: |
| 2023 | .5222906652962137 | .525309168022311 | −.577935% | [−.02217664035,+.00885277123] | 4/5 |
| 2025 | .5231102687111107 | .5271735780645829 | −.776760% | [−.00773862246,−.00057407009] | 2/5 |

Both full-source gates PASS, both ≥2% pooledQLIKE and positiveCI-lower gates
FAIL; 2025 asset breadth also FAILS. 2023 logRV MSE improved (.86035116→.84635340)
and four assets individually improved QLIKE, but neither rescues the prespecified
pooledQLIKE gate. 2025 logRV MSE worsened (.68649603→.70118885). CIs measure
absolute QLIKE loss difference, not relative percentage gain, and are conditional
on this old-seen fixed experiment, without research-selection adjustment.

## Formula, target and independent information

The method is grounded in the actually readable independent primary author draft
[Measuring the impact of jumps in multivariate price processes using bipower covariation](https://www.bayes.citystgeorges.ac.uk/__data/assets/pdf_file/0004/64876/BarndorffNielsen-Shephard.pdf).
Printed pp7/10/12 specify the absolute-Gaussian normalization, finite-sample
factor and within-day pairs. For 288 five-minute returns:

```
RV = sum(r_i^2)
RSminus = sum(r_i^2 where r_i<0)
BV = (pi/2)*(288/287)*sum(i=2..288, abs(r_i)*abs(r_i-1))
J = max(RV-BV,0)/RV
```

The file explicitly labels itself an unfinished draft and ignores market
microstructure. J is our truncated ratio proxy, not a jump probability or formal
jump test. The blocked Oxford2004 full paper was not requested again or claimed
read. These finite-interval crypto trade-close features are an adaptation, not
the authors' empirical replication, continuous-price identification or venue
certification. Scaling returns preserves J; within-day permutation can change
BV while holding RV, semivariance and total price return unchanged. That
temporal path information motivates this experiment; a changed model name or
training period alone would not establish independence.

Control: log completed-dayRV, log past7 meanRV, log past30 meanRV,
RSminus/RV, completed-day price return and log(RV1m/RV5m). Candidate adds only J.
The sampling ratio was included before any historical arrays to match information
already used by the old minute selector. One pair of five-asset deterministic
OLS systems, 7/8 coefficients per asset (including intercept), full rank;
train-only shared seven-feature mean/std(ddof1). Each arm/asset maps its logRV
prediction through its own train-only mean-exp-residual smearing. No ridge,
optimizer/feature/window/threshold grid, clipping, validation fit or rescue.
LogOLS plus global smear does not directly optimize QLIKE or guarantee
heteroskedastic conditional mean calibration; failure is limited to this recipe.

Decision UTC00:00 uses the previous completed day and previous30 daily risk
observations. Exactly288 within-day five-minute returns require the preceding
day's actual final close and288 observed endpoints;287 products stay within
that day. Missing starting anchor stays UNKNOWN; RV=0 is invalid, not epsilon
repaired. Target is the forthcoming UTCday's actual RV, conservatively mature
at decision+2UTCdays. This label differs from owned trade00:01 return and wallet
NAV. Candle completion is an availability proxy, not observed network arrival.

## Actual sources and common mature training cohort

Immutable b4756ec8fb59457cfd8db74a79ca6a859f07f331 source-only
FIVE_MIN_CLOSES member SHA441ae2de4ac38bdc6f0490469a7a1f764f081ac6b6d53a83012b4252a398cb45
and306b58c4a52035ac9f374de7c25d40dff22fb658 phase source packets supply699 full
completed trade days through November2022. Only source members were decoded,
not old model coefficients/results. Raw daily trade stats from0d6db3fd515eea5de421bce6cf7123b3e15ec55f
SHA9a0e63c0b4f93b185310c65892d424e99307a6678930b5d559e421a1145edde9
bind first699 RV1m values; reconstructed5min RV/RS match existing primitives
at relative tolerance2e−14, with exact endpoint/symbol identities.

The genuine December2022 trade warmup gap was repaired after freeze, solely
five official monthly1m klines ZIPs, **8,465,771 bytes**, matching all original
hash-only receipt SHAs and official checksums, CRC, OHLC and44640-minute grids.
Previous Dec31 daily source final prices match bit-exact. This adds real
December2022 trade paths to training and supplies the full Jan1,2023 HAR30
window. No full December2022 mark recovery is claimed. No retry, alternative
venue, already-verified-body reGET or protected interval access.

2024December five raw trade months were reused from Gitd69e9ac94478c5be54cb46c622afec7aaf3c61f7
with multipart/wrapper/member/official-checksum checks and full minute paths,
not downloaded again. Both validation years' warm leading endpoints are real
known source values. Validation canonical monthly minute close/timestamp/NPZ
sources f38617c5a0917490c8b90fba355ecf0d5f1b87f4 and
534a18fbed0ec7a2f7ffbb298526c51b1a2a696c are reused with exact hash/size checks.
Saved actual price/funding/risk context53357f33f4e6ccb536af762fbff39b269c24d837
is retained only for source and any later frozen economics; no learned oracle.

Training natural2021/22 calendar730 dates yields **697 common all-five mature
dates**, same masks and indices both arms; source-first unknown anchor, 30-day
warmup and December30/31 strict maturity purge are retained. Maximum admitted
maturity1672444800000000 (2022December31) is strictly before2023Jan1. All
admitted/unknown/purge timestamps are in PREPARATION.json. Full2023/2025 each
365 dates/1825 pairs are mandatory old-seen development, not new OOS.

## Dedup, evidence and recovery

70 public heads, prior69 snapshot1934 source/protocol identities and targeted
current metadata were independently reviewed. Existing HAR5OLS/149days uses
RV1/7/30 and has its own failed QLIKE confidence gate; upward quantile5LP/211days
uses RSplus, excursion and trend for maximum-mark-up risk; minute selector3Ridge
uses RV1m/RV5m, adverseRS and joint covariance for utility and failed; tail
source-resolution diagnosis fitted no predictor. No existing adjacent absolute
return-product/BV or HAR-J experiment was identified in this bounded public
scope. No compressed-history-exhaustive absence claim. Public distribution
bf53ddff snapshot also lacks intradayBV; its WIP/STATE/arrays were not accessed
or modified. All old STOPs and both positive conditionalFOLLOW candidates remain.

Actual boundary acquisition11.890261s, projection8.452282s, one paired
historical fit.294230s, both-calendar score.283168s. Seeds: deterministic
training NONE; 14-natural-day circular joint5asset bootstrap1000 draws/year,
811752/811753. Four meaningful synthetic path/scale/maturity/future-suffix tests
passed twice before history (.22s initial,.21s final including stronger control),
40 synthetic assetOLS systems distinct from10 actual historical systems.
No actual source/model preparation failures or full-repository test claims.
Independent published-source/clock/maturity/gate review PASS.

Protocol/code/source/coefficients were normal-pushed and remote-SHA verified
before their dependent stages: e0d09f792e9044d7507cec37202d1383f62fea80 freeze;
6d519986ae0da44c97c1f52c41b1253e0d1cee5a exactINPUTS beforefit;
63256276cf7959c423c5e8266f08d7329fc077c4 MODEL beforebothscores;
f46229d072d82ad63553dc163d943d04e7b8f439 scores/cold code.

Public INPUTS/MODEL/SCORES total **17,069,639 bytes**,19 members, all source
five-minute paths/statistics/labels/model/predictions/losses/bootstrapstarts/means
and five original new monthly ZIPs/checksums. Fresh GitHub filtered shallow clone
and sparse checkout cold recovery PASS3.645363s:2,191,680 five-minute source
prices reconstructed,697 admissions/scalers/train smearing/OLS optimum checked,
7300 saved prediction scalars and2000 saved bootstrap means exact. Maximum
normal-equation residual2.7267077484793845e−12. Five new December raw minute ZIPs
were independently reparsed; historical699 1m stats match immutable Git values.
Validation1m RV is retained genuine-source stats with canonical month hash
references, not a full validation-minute reparse during cold. Verification
arithmetic performs zero new fits/RNG/providerGETs/accounts/originalSTATE opens.

```
bash research/jump-share-risk-20261012/reproduce.sh /workspace/jump-risk-reproduction
```

Use a new destination for another run. SOURCE_SHA256.txt binds code/config;
ATTEMPTS.json and evidence/COMPLETION.json retain full counters, sources and
resource proof. All23 original native snapshot SHA values remain unchanged.
Same oneCPU/thread/4GB address/2GB sampledRSS/8GB host/swap0/GPU0/15GiB reserve,
no budget or finance-rule expansion. Protected2026 and unknownreserve bodies,
lostledger fiction, Library, keys/credentials, pay/live/deploy/main/force and
other distribution files remain untouched. No source/method/permission blocker
remains for this completed recipe; economics is intentionally NOT_RUN_FAILED_INFORMATION.
The project remains ACTIVE; next independent metadata decision is saved separately.
