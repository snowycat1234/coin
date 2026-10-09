# Four completed v2 models: observed native61 attribution

The main shortfall was price PnL, concentrated in May's CS-heavy positions and
June's retained long exposure. Higher exposure explains part of the damage,
but it does not explain the whole ordering. These are read-only comparisons of
the **already completed 2024 May 1–July 1 exclusive** fresh 10,000 USDT accounts.
No wallets, fits, model inference or provider downloads were run.

NoCash arms use **Static50**; WithCash arms use **Cash50**. Those controls have
the corresponding admitted action sets, but they are not matched for realized
risk. Static50 ended at −189.01 USDT; Cash50 ended at −110.89 USDT. Each journal
includes actual signed funding, fees, execution costs and a paid terminal-flat
closure. All six accounts completed 87,840 minutes with no liquidations.

## Where the extra loss came from

All amounts are arm minus primary reference, in USDT. Negative fee/execution
effects mean additional costs. Price accounts for 81–96% of the extra loss.

| Arm | Net difference | Price | Funding | Fee effect | Execution effect | May net difference | June net difference |
|---|---:|---:|---:|---:|---:|---:|---:|
| GRU noCash | −322.38 | −308.80 | +0.96 | −5.93 | −8.62 | −212.47 | −109.91 |
| GRU withCash | −362.07 | −326.41 | −6.61 | −11.84 | −17.22 | −210.77 | −151.30 |
| MLP noCash | −99.58 | −81.07 | +5.17 | −9.65 | −14.03 | −200.81 | **+101.23** |
| MLP withCash | −366.84 | −332.11 | −4.47 | −12.33 | −17.93 | −198.68 | −168.16 |

MLP noCash did better than Static50 in June; its May damage exceeded that
recovery. Extra trading costs mattered, but they were not the leading cause.

## Requests, the ramp, and held positions

Expert simplex weights below are **VOL / CS / CASH**, averaged over dates.
They are not literal percentages of NAV. Covariance scaling, expert netting,
sizing, realized prices and actual fills produce the recorded exposure.

| Arm | May requested | May ramped budget | June requested | June ramped budget | First ramped VOL > CS | Active request dominance changes |
|---|---|---|---|---|---|---:|
| GRU noCash | 9.1 / 90.9 / 0.0% | 2.4 / 66.9 / 30.6% | 99.5 / 0.5 / 0.0% | 81.5 / 18.5 / 0.0% | June 6 | 1 |
| GRU withCash | 13.5 / 85.8 / 0.7% | 5.3 / 63.7 / 31.0% | 88.7 / 11.1 / 0.2% | 80.8 / 19.0 / 0.2% | June 4 | 3 |
| MLP noCash | 1.8 / 98.2 / 0.0% | 0.2 / 69.1 / 30.6% | 75.5 / 24.5 / 0.0% | 49.2 / 50.8 / 0.0% | June 17 | 7 |
| MLP withCash | 6.7 / 90.8 / 2.4% | 1.4 / 67.6 / 31.0% | 95.8 / 4.1 / 0.2% | 74.8 / 25.0 / 0.2% | June 8 | 3 |

Dominance changes exclude June 30, whose final targets were forced flat. This
was mostly a CS-to-VOL regime change. MLP noCash oscillated more in its requests;
the daily ramp kept its budget CS-dominant through June 16. The large initial
May cash budget reflects the original daily ramp from a fresh account. The
cash-enabled heads subsequently chose very little cash.

| Arm | May mean actual gross / reference | June mean actual gross / reference |
|---|---:|---:|
| GRU noCash | 32.6 / 18.0% | 22.8 / 27.7% |
| GRU withCash | 31.2 / 11.2% | 20.2 / 13.8% |
| MLP noCash | 33.5 / 18.0% | 33.1 / 27.7% |
| MLP withCash | 32.9 / 11.2% | 24.5 / 13.8% |

There were 17 June dates with a negative equal-weight CORE5 actual UTC mark
return. All four arms were net long in **every recorded minute on those dates**.
Their mean net exposures were respectively 18.6%, 18.1%, 11.7% and 17.6%, versus
Static50's 10.7% and Cash50's 5.3%. This is an ex-post market descriptor, not a
new traded benchmark or an assertion that every held asset fell on every date.

## Exposure magnitude versus composition and timing

Observed price PnL is reconstructed from prior inventory times actual mark
changes, plus each recorded signed fill's actual-mid-to-minute-mark effect.
At each minute, scale the reference's recorded prior inventory by the arm's
absolute-USDT gross divided by reference gross. The proportional part is
called **gross size** below; the remaining signed inventory difference is
**composition/timing**. Their price contributions plus the fill-to-mark
difference exactly reconcile the observed price difference.

| Arm | Full-period price: gross size | Full-period price: composition/timing | Fill-to-mark difference |
|---|---:|---:|---:|
| GRU noCash | −49.44 | −260.92 | +1.56 |
| GRU withCash | −123.90 | −203.75 | +1.24 |
| MLP noCash | −64.61 | −18.98 | +2.51 |
| MLP withCash | −134.01 | −199.89 | +1.78 |

GRU noCash's June gross was lower than Static50, yet its June net difference
was −109.91. June composition/timing contributed −113.68 while gross size
contributed +5.62. MLP noCash held more June gross and gained +101.23 relative
to Static50: its June composition/timing contribution was +118.32, against a
−10.44 gross-size contribution. Thus exposure magnitude alone cannot explain
the results. For the cash arms, greater exposure and composition/timing both
contributed substantial losses.

This is an **algebraic partition**, dependent on its stated basis. No scaled
NAV, orders or executable account were constructed. The residual includes
asset/sign composition and timing; it is not an isolated causal expert-choice
effect. When reference gross is zero, the ratio is defined as one.

## Largest incremental loss dates

Each row gives the three largest arm-minus-reference daily losses.

| Arm | First | Second | Third |
|---|---|---|---|
| GRU noCash | May 20: −81.77 | June 17: −75.78 | May 21: −72.88 |
| GRU withCash | May 21: −105.82 | June 28: −53.18 | June 11: −52.74 |
| MLP noCash | May 20: −82.03 | May 21: −73.12 | June 28: −66.75 |
| MLP withCash | May 21: −106.49 | June 28: −66.87 | June 18: −61.72 |

On May 20, ETH's actual mark rose **19.35%**. The noCash arms averaged about
**15.3% NAV short ETH**, versus Static50's **5.9% short ETH**, while requesting
over 99% CS. ETH's incremental price contributions were −176.16 and −176.93
USDT, partly offset by the other assets. On May 21 the models remained almost
entirely CS; their gross exposures were about 58–59%, versus Static50's 31.0%
and Cash50's 15.5%.

On June 17 GRU noCash was effectively VOL, with 18.5% gross and net long
exposure, versus Static50's 30.9% gross but only 9.7% net long. SOL and DOGE
fell 5.32% and 6.12%, contributing −47.96 and −54.33 of incremental price PnL.
On June 28 all five marks fell, including SOL −6.47% and DOGE −3.20%; the arms
in the largest-loss table remained 22–24% net long. The full daily file records
actual asset returns, signed exposures, requests, budgets and contributions.

## Did they choose the weaker expert?

Existing teacher candidate ranks provide only a limited association check.
Across 60 nonterminal dates, the ramped dominant VOL/CS pair was the weaker
old-teacher candidate on **32 / 32 / 31 / 32 dates**, respectively. Requested
dominance counts were 36 / 34 / 31 / 35. That is roughly half the dates, not
evidence that the models selected the weaker candidate every day.

Those candidate evaluations start from the **old greedy teacher's own carried
state**, including Jan–April history, rather than these model accounts' states.
No pure standalone native VOL/CS May–June wallets are available in this
diagnostic. Candidate payoffs are not summed; no oracle switching gain or
native regret is claimed. Net actual positions cannot uniquely be assigned
back to VOL and CS after their target netting.

All four source training exports were capped and not converged, with unequal
update counts. These journals do not establish overfitting. A controlled
same-exposure allocation/timing ablation was **NOT_RUN**.

## Evidence and reproduction

- [ATTRIBUTION.json](ATTRIBUTION.json): exact bridges, source hashes, all four
  decompositions, allocation summaries and loss-date details.
- [DAILY_DIFFERENCES.csv](DAILY_DIFFERENCES.csv): all 244 arm-date comparisons.
- [CHECK.json](CHECK.json): delivery arithmetic and byte checks.
- [Source](../attribute_v2_native61.py): read-only computation from the retained
  state and the [existing dependency recipe](../requirements-native61.txt).
- Original immutable journals: [noCash](../temporal-v2-native61-results/README.md),
  [withCash](../temporal-v2-native61-cash-results/README.md),
  [references](../comparison61/README.md).

The source checks 36 used account files against the preserved member hashes,
15 original actual mark partitions against the original dataset manifest,
the exact guard-OFF engine SHA256
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`,
and the frozen request adapter. All six mappings reproduce the 305 recorded
daily asset targets bit for bit. The maximum daily price/funding/cost/NAV bridge
error is below 1.9e−12 USDT. Historical publication, venue rules and the
cross-venue conditional account assumptions remain uncertified.

```sh
PYTHONPATH=/path/to/restored-state/deps OPENBLAS_NUM_THREADS=1 POLARS_MAX_THREADS=1 \
python3 research/recover-frozen-runner-20261009/attribute_v2_native61.py \
  --state /path/to/restored-state --output /path/to/new-output
```

The output directory must not already exist. The script is limited to one CPU,
2 GB address space and 120 CPU seconds. The restored original state is required;
this diagnostic does not recover data or contact providers.
