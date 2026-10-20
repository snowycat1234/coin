# Fixed 2023 settlement-window attribution

A single prespecified retrospective economic diagnostic using recovered public CORE5 2023 sources. It is not a shared-wallet simulation or executable strategy return. No funding-sign or outcome filter, no window or parameter search, no model, no held-out2026 data.

SPEC.json and analyze.py are published before outcome calculation. Each event/reference and control is separately normalized to one USDT initial trade-OPEN reference notional; this is not an executable minimum-size order. Fixed SHORT windows are [T−5min,T+5min] and [T+55min,T+65min] at every UTC00/08/16 slot. Funding uses a fixed strictly-past mark CLOSE proxy under the conditional raw-fraction convention. Minute OPENs are not BBO mids or guaranteed fills. Full spread/slippage and fill-notional commissions are charged once.

Primary summaries use equal calendar-day weights. The paired observations within one date stay together in a fixed 14-day circular bootstrap. Pooled sample means and all asset/month summaries are separately descriptive, never used to select a profitable period. The five unavailable first-day prewindows are the only predeclared boundary exclusions. Unexpected funding clocks or source gaps stop the analysis.

Run with normal Python and NumPy: `python analyze.py --source ../public_2023_source_restore/reconstructed_source --output result`. A fresh output directory is mandatory. Source files are checked against the exact published reconstruction certificate before calculating outcomes.

## Bounded duplicate check

No equivalent event-window study was found in210 retained remote heads and targeted settlement/funding-capture/event-study commit searches. This does not prove absence in compressed or unpublished history. Related but different work:

- Settled21-day funding direction: https://github.com/snowycat1234/coin/blob/53357f33f4e6ccb536af762fbff39b269c24d837/research/settled-funding-direction-20261012/REPORT.md
- Funding-adjusted CS rank: https://github.com/snowycat1234/coin/blob/899f7e9a198a48b84aaaf3ebe2374e7ee9bdd962/research/funding-target-discriminator-20261014/PROTOCOL.json
- Daily mark/trade forecast: https://github.com/snowycat1234/coin/blob/5e02066526d9accad56915991600f2ac5c31aab0/research/mark-trade-dislocation-20261012/REPORT.md
- Actual funding charge-point authority remains unresolved: https://github.com/snowycat1234/coin/blob/de14c492e8efbbbab1f039507f4905e1fee7c892/research/funding-charge-evidence-20261011/README.md
