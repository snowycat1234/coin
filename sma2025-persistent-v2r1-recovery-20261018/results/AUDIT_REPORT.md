# Independent saved-output audit: SMA2025 v2r1

PASS: saved identities, full calendar, chronological native40 arithmetic, causal clocks and paid terminal state. No engine, account, policy or financial advance was imported or invoked. Original saved outputs were hash-checked again after inspection.

- 365 days; 525,600 contiguous minutes; 18,921,600 saved float64 cells match independent native40 arithmetic converted to float64 exactly.
- Paid NAV: 9829.62804019943618961520 USDT from 10,000 USDT. Exact net return: -1.70371959800563810384800%.
- Maximum drawdown: 12.26397695339534353972673986743644580545% (native40 ratio). Exact fraction is (10876.08166038559878742020 - 9542.24151212345133498020) / 10876.08166038559878742020; peak 1755145620000000, trough 1760131260000000. Saved float64 MDD: 0.12263976953395339.
- Fees 12.05056983306000; adverse execution costs 17.528043920; signed funding -50.70684604750381038480 USDT. Costs already embedded in paid fills are not deducted twice. Exact accounting residual: 0E-20.
- 3107 financial ledger rows, 48 paid trade legs, 5470 account funding rows checked. Funding reconciles: 5,475 source events = 5 no-past-mark fresh-flat skips + 5,470 account rows; 3,059 nonzero owned funding ledger rows.
- Actual observed gross weight max 0.3230021518169185797442972229964666298957; largest asset weight max 0.1825987636984293664448874380025379580525; minimum shared free cash 7083.84640571457875654020; maximum isolated balance 2568.624777600 USDT. Maximum causal rolling daily-covariance sigma of held positions 0.24209547289531333. This is materially above the 10% admission target; admission-time forecast risk does not guarantee held positions stay at 10% as prices and covariance drift.
- All five actual positions are exactly zero, with no debt, collateral, native/policy pending request, delayed acknowledgement, transfer, top-up, conditional settlement or settlement value. One external reduction is backed by an actual paid native close.
- Saved execution guard reports zero forbidden reads/writes/finance/execution/network/process/deletion/outside-calendar events.

Limits: seen DEV only; no out-of-sample, original-code-equivalence, actual source-arrival timing, funding-unit/publication, venue-filter/risk-tier or native liquidation/no-liquidation certification. MDD observation scope excludes intraminute extremes. No run restart or old-year stitching.

Receipt SHA256: 98eb900afed1647972e4034cf34279a455ca38382df3f1d62199ed99cfb9d778
