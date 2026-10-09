# Interpretation of three frozen forward paths

July contains favorable conditional timing, heavily concentrated in a few dates. October reduced exposure too far during profitable periods; January favored an expensive signed cross-sectional book that largely canceled its own price gains. These are descriptions of three historical daily-surrogate wallets, not proof of stable alpha, universal failure or overfitting. The frozen worst-fold screen still fails. No models, requests, scalers, protocol or training source changed.

`READ_FROZEN_PATHS.py` verifies every forward manifest file, reads saved arrays, and reconciles 189 paired daily observations to both wallets' saved NAV, costs, signed funding and utility. It performs **zero model inferences, optimizer updates, economic rollouts, downloads or native wallets**. Model and primary have zero boundary risk events, so quantities follow exactly from saved start-NAV, targets and prices. Other controls' totals are read from their saved complete wallets. `RESULT.json` and `DAILY_ATTRIBUTION.csv` preserve all dates, not just favorable examples. Reconciliation tolerance is 2e-8 USDT and 2e-14 utility; Ruff passes.

## July: profitable portions of losing full-period experts

The actual mapped path was CASH-led July3–12, VOL-led July13–30, SHORT-led July31–August26, then VOL-led August27–September2, followed by paid closure. Its selected VOL/CS/SHORT legs contributed **+225.52/−28.47/+403.51 USDT of price PnL**, using the model wallet's actual budgets and own NAV. Funding added4.13 and execution cost removed22.86, yielding **+581.84 USDT**. Every standalone risky control lost across its own complete period; a variable-budget path need not inherit those full-period returns. They are not executable switch labels or a hindsight oracle, and costs are charged to the actual net transactions rather than arbitrarily assigned to expert legs.

Each date below identifies a decision-to-next-observation interval; mapped budget is distinct from actual notional exposure.

| Decision date | Mapped action and actual exposure | Model PnL | Primary PnL | Excess |
|---|---|---:|---:|---:|
| July13 |52.1% VOL budget;13.3% actual long gross |+273.98 |−79.75 |+353.73 |
| August15 |90.8% SHORT budget;31.5% actual short gross |+87.28 |−94.69 |+181.98 |
| August16 |92.3% SHORT budget;31.0% actual short gross |+84.87 |−82.00 |+166.88 |
| August17 |92.9% SHORT budget;30.0% actual short gross |+267.76 |−94.30 |+362.05 |

The saved July13 XRP and SOL interval returns were+73.4%/+18.5%; August17 BTC/XRP/SOL returns were−7.4%/−14.1%/−5.2%. Early long participation and the later short book explain the signs. All five assets contributed positive price PnL over July; XRP contributed249.34 and SOL147.73 of600.56 total. This is a realized path description, not evidence that those extreme moves were generally predictable.

For context, the full-period standalone SHORT wallet lost478.81 on July13, when the model had only0.64% mapped SHORT budget; the standalone VOL wallet earned312.44 that day. On August17 the standalone VOL wallet lost281.55 while SHORT earned270.41, and the model already had92.93% mapped SHORT budget. These are saved observations from different continuous wallets, not rows that can be spliced into a feasible strategy. The frozen model path and its L1 ramp preceded forward scoring; none of these dates was used to alter its requests.

Concentration is substantial. The top three profit dates (July13, August17, August15) contributed629.02; all other saved contributions sum to−47.18. The top five excess dates account for76.7% of positive excess mass. Excess after omitting the top three contributions is+89.76; after omitting five it is−129.23. These are sums of existing contributions, **not rerun wallets**: removing a date from trading would change later NAV, positions and costs. The ramp also kept substantial SHORT budget during rebounds; August14/19/23 had excess−79.40/−50.05/−83.02.

## Exposure, composition and costs

| Exact model component, USDT | July | October | January |
|---|---:|---:|---:|
| Price PnL |+600.56 |+761.30 |+10.33 |
| Signed funding |+4.13 |−10.42 |+13.81 |
| Execution cost (subtracted) |22.86 |14.48 |53.53 |
| Net PnL |+581.84 |+736.40 |−29.39 |
| Primary price PnL |−376.27 |+989.88 |+447.66 |

For price-PnL excess, a symmetric algebraic decomposition separates differences in net-target gross magnitude, normalized signed asset composition, and own-wallet NAV scale:

| Descriptive price-excess component, USDT | July | October | January |
|---|---:|---:|---:|
| Exposure magnitude |−32.97 |−579.02 |+168.55 |
| Signed asset composition |+1,009.12 |+353.18 |−604.54 |
| Own NAV scale |+0.68 |−2.73 |−1.33 |
| Total price excess |+976.84 |−228.58 |−437.33 |
| Funding excess |+6.78 |+3.26 |+36.19 |
| Execution cost saving |+3.89 |+11.38 |−22.98 |
| Net PnL excess |+987.51 |−213.94 |−424.11 |

For targets `a,b`, let gross be their L1 norms `g,h`, and normalized signed vectors `u=a/g,v=b/h` (zero when gross is zero). The identity is `a-b = .5(g-h)(u+v) + .5(g+h)(u-v)`. Multiplying by average saved NAV, .99 sizing and observed asset returns gives the first two rows; the remaining NAV difference gives the third. This decomposition is exact but conventional and **descriptive**, not a causal estimate of timing skill or a comparison to a newly executed exposure-matched policy.

July's advantage is overwhelmingly signed composition; lower average gross alone does not explain it. Model/primary active mean actual fill gross was10.89%/15.19%, but daily return standard deviation was0.511%/0.306%, because favorable extreme dates increased dispersion. Lower drawdown (0.765%/4.625%) is therefore not general risk dominance.

October's selected VOL leg earned673.25 and CS88.05 of price PnL. Its SHORT leg contributed only0.0023: SHORT was eligible throughout but had a zero target on41/62 active dates. Mean mapped budget devoted to those flat targets was37.91%, compared with3.71% mean raw CASH request. Low CASH request did not imply high invested notional. The SHORT-led November7–December2 phase averaged2.03% actual gross, zero actual short gross, and underperformed the primary by193.89. November10 and15 still earned55.40/15.18, but the primary earned194.89/111.80; these were missed gains, not model losses. Direction/composition helped descriptively, yet exposure reduction more than offset it. Funding and cost savings together were only14.64.

January was CS-led for49 active dates, with68.49% mean mapped CS budget over the full active block. Mean actual gross was35.64% versus22.96% for the primary; maximum drawdown was2.223% versus1.770%. The model's asset price contributions were BTC+426.16, ETH+82.93, SOL−217.89, XRP−208.98 and DOGE−71.87. Long/short composition canceled most price gains, and53.53 execution cost exceeded price plus funding income. February26–March3 contributed−124.99 model PnL versus+220.70 primary, excess−345.69. February28 made77.71 but trailed155.13; February29 lost129.26 versus71.10; March1 lost4.43 versus a63.80 gain. Composition, not simply fees or insufficient gross, dominated the shortfall.

## Independent-fold averages and temporal stability

Equal-weight summaries below average three distinct full-capital wallets. They neither stitch episodes nor compute APR.

| Measure | Model mean / median | Primary mean / median |
|---|---:|---:|
| Net PnL, USDT |429.62 /581.84 |313.13 /394.72 |
| Maximum drawdown |1.314% /0.954% |2.731% /1.798% |
| Daily net-return standard deviation |0.422% /0.391% |0.388% /0.360% |
| Active mean allocated gross before netting |22.38% /15.98% |26.62% /27.95% |
| Active mean actual fill gross |18.84% /10.89% |19.35% /19.91% |
| Execution cost, USDT |30.29 /22.86 |27.72 /26.75 |

PnL excess mean/median is **+116.49/−213.94 USDT**; utility excess mean/median is **+0.012645/−0.018638**. The positive mean is driven by July; the negative median and worst utility−0.043231 retain the failed screen. No population confidence or convergence claim follows from three observed folds.

Frozen inference was bitwise reproducible in the earlier export check. Across the62 active decisions, requests are variable and partly near-binary, while ramped execution changes more slowly:

| Active-path diagnostic | July | October | January |
|---|---:|---:|---:|
| SHORT gate `r` below.01 or above.99 |45.2% |77.4% |33.9% |
| `r(1-r)` below.001 |11.3% |30.6% |14.5% |
| Investment gate `s` above.99 |35.5% |35.5% |54.8% |
| Largest whole request above.95 |22.6% |24.2% |0.0% |
| Dominant requested / mapped action changes |6 /3 |5 /2 |6 /1 |
| Median requested daily L1 change |.074 |.050 |.118 |
| Maximum requested daily L1 change |1.785 |.929 |1.598 |

The investment gate has no active derivative below.001 in any fold. October's short gate is often near-binary, while January's whole request remains mixed despite strong CS preference. July/January have2/3 requested daily L1 jumps above1; the mapper limits discretionary change to.1 and has median total budget change.1 in every fold. The paths therefore contain persistent regime preferences and some abrupt intents, not constant frozen predictions. This does not establish stability under other seeds or small input perturbations; neither was tested or tuned here. Forced terminal closure is excluded from these gate/action summaries.

## One conditional next action

After independent native validation, preregister **one additional63-decision chronological block with complete native tapes**, choosing dates from coverage before examining its outcomes. Freeze dates/source hashes and use the unchanged architecture, seed,512-update recipe, objective, caps, horizon and six controls. Its purpose is to check whether rare signed-composition timing repeats beyond these observed folds. Make no blend, gate, seed, threshold or horizon change based on this interpretation. This is a proposal only; no additional fit or wallet was launched.

Original daily execution/publication-clock limitations remain. January native replay belongs to the separate executor; the two2023 native tape sets are missing here. No native outcome is inferred from these daily results. Reproduction needs only installed NumPy2.5.3:

```sh
python research/temporal-prequential-transfer-20261009/interpretation/READ_FROZEN_PATHS.py \
  --root research/temporal-prequential-transfer-20261009 \
  --destination /path/to/new/interpretation-output
```
