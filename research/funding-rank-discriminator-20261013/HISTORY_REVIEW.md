# Narrow novelty finding, with prior failures retained

No exactly equivalent fixed weekly CS21 simple-return-minus-actual-settled-rate
asset ranking was identified in the bounded inspected source/history. This is
not proof of absence across all research, and funding is not a new feature.
GitHub code search returned no hits even for known funding code and therefore
its empty results were not treated as novelty evidence.

Original CS uses 22 completed closes for21 simple-return days, top2/bottom2,
stable CORE5 input-order ties, all-tied cash, and a fixed2024Jan1+7k rank clock.
It restores the preceding ownership rank rather than reranking at year start.
The current CSH mask also requires genuine200-close HOLD admission across all
five members. The failed min4 availability variant is not reused.

## Exact relevant prior recipes

- Carry account, pair trim, and D032: fixed BTC/ETH spot-long/perp-short pairs,
  not cross-sectional ranking. D032 exits permanently when pooled held funding
  cash over[D-8d,D-1d) is nonpositive after at least8 held days.122d/90d
  increments versus pair trim were-12.606683/+2.578361USDT, failing the two-window
  adoption criterion. Exact current-main docs verified against local archives
  at ef67d636a51fd3fa9e804f651aab5775f6bae5f8:
  docs/CONDITIONAL_CARRY_ACCOUNT_20261003.md,
  docs/CONDITIONAL_CARRY_PAIR_TRIM_20261003.md,
  docs/CONDITIONAL_CARRY_90D_20261003.md,
  docs/CARRY_PAST_FUNDING_EXIT_20261003.md.
- Joint named24 models already contain funding, premium, own momentum, breadth
  and volatility. See FEATURE_MANIFEST.json and NON_DUPLICATION.md in
  research/short-funding-residual-20261011 at
  e347fa4f8dc5d65c9a419b45eb330476d8c734ed. This discriminator does not claim
  a new factor or superiority to that broader input set.
- Seven-day funding/premium financial-zero sign bins already described selected
  SHORT errors. Associations reversed across fitted TRAIN/2023/2024 and did not
  justify a filter. research/temporal-short-input-diagnosis-20261010/RESULTS.md
  at3acfcd0fc44907c25e6eb4c0d66776b97ff5f572.
- Lagged7day per-asset funding residual: price/symbol/volatility Ridge1 baseline
  versus identical baseline plus one settled-rate sum. Two2021 fits and
  2022H1/H2 training diagnostics: MSE gain1.411591%, but standardized funding
  coefficient-.09823997 contradicted preregistered crowding sign and calendar
  price-cost increment was-4.163982bp/week. STOP, no sign-flip rescue.
  research/short-funding-residual-20261011/{PROTOCOL.json,README.md} at
  cf394f9e81e2d10f27cbeb9b012b2c3bb4cc5e8c.
- Funding direction: -sign(mean21 complete daily raw settled sums), an extra
  full-day availability lag, .12 per active member, daily risk scaling, and
  constant SHORT control. No price or relative rank. Full2023/2025 candidate
  references net-386.025346/-170.811789USDT; STOP in both mandatory years.
  research/settled-funding-direction-20261012/{PROTOCOL.json,REPORT.md,core.py}
  at53357f33f4e6ccb536af762fbff39b269c24d837.
- Dual-speed daily rank21-rank1 versus same-daily SLOW and SKIP controls changed
  rankings, but had no funding feature. DUAL net-2222.87USDT in456-day
  Apr2021-Jun2022 and-1029.07 in full2023; STOP, no cadence/window rescue.
  research/cs-dual-speed-ranking-20261012/{PROTOCOL.json,REPORT.md}
  at31fe7210a18de8a6029fa08906ce4ed7b20940ba.
- Rank persistence routing used correlation of current21day ranks versus ranks
  seven completed days earlier, one training-median/two-mean model, and failed
  all three confidence gates. It did not rank price-minus-funding. The saved
  direction attribution also shows2023 short PRICE loss-2600.300829USDT,
  partially offset by funding receipts+113.902068; funding was not the main
  explanation for that failure. research/rank-persistence-routing-20261012/
  README.md at9b44ec7a208e51b2769e41772e843116b0469e05.
- Earlier learned selectors, CPD, agreement/sign filters, cost/execution,
  risk/sizing, exits and the new signed-serial persistence STOP are not reopened.
  V7/V8 flow families inspected in the cached archives were not funding
  rankers: V7 flow/return XGB-S lacked actual perp funding; V8's478 feature
  contract contained no funding feature names. They must not be confused with
  the separate named24 daily joint models.

## Scientifically useful but minimal next question

The signed historical financing adjustment is a different deterministic way of
ordering the same assets. It might change nothing, because return gaps can
dominate funding differences. Therefore the first test is exact same-lag signed
basket identity, not another wallet. It is an approximation: subtracting raw
rates from simple price return omits changing charge-mark/notional weights,
transaction costs and reinvestment. Even nonzero basket differences provide no
evidence of future benefit or executable net return.

The24h source-availability proxy requires shifting BOTH21day windows. The
identical-lag price control is primary; unlagged original CS is descriptive.
Positive funding reduces the long-oriented score; shorting the lower score
naturally receives positive funding, with no separate sign reversal.

The reported min4 availability result is a motivating conversation summary
only: its local outputs were lost on the workspace reset before publication.
No new byte-level evidence or restored result is manufactured from that text.

Source-admission implementation correction is preserved in ATTEMPTS.json:
the borrowed daily_rates edge check projected the final preceding funding
interval forward and failed asymmetric cadence. This finding concerns this
new source-only discriminator. No prior native event-accounting error or
invalidity of the old2023/2025 financing-direction results is established.

All2021/23/24/25 remain seen development. Locked2026Mar1-Sep1 and unknown
holdouts remain closed. The economic direction, sign, lookback and lag are
frozen once; no parameter search, post-result sign flip or calendar rescue.
