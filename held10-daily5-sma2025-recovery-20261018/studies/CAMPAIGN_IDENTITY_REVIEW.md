# Campaign and episode definitions



The reported 52 campaigns are genuine per-asset paid-inventory 0 -> nonzero -> 0 intervals. They are not partial-close chunks or 52 independent observations. All52 map to unique original policy ENTRY (symbol, episode) identities and their native fills in the JSON.



- HELD10: 55 OPEN legs = 52 starts + 3 same-sign partial-entry continuation legs. 76 CLOSE legs = 52 flat completions + 24 partial-position reductions.

- Owned27 cuts: 4 fully flatten; 23 leave a position. All27 order requests were fully filled, so those23 are partial-position reductions, not partial native fills.

- Remaining CLOSE legs: 45 original-policy exits to flat; 4 other native external terminal-window reductions, consisting of3 flat completions and1 partial-position reduction.

- Baseline:24 campaigns,24 OPEN and24 CLOSE legs; no partial-position legs.



Both runs see the same60 original direction episodes: BTC18, ETH14, SOL8, XRP10, DOGE10. HELD10 pays52 of those episodes and baseline24;23 are shared,29 only HELD10,1 only baseline. Each run issues ENTRY requests in59 source episodes. The common missing XRP7 episode has an exact original saved-frame coarse quantity of0 in both runs.



## Why the campaign counts differ

All29 HELD-only filled episodes have five matching baseline ENTRY attempts and no baseline paid increase. Of145 attempts,127 carry FRESH_TIER_EXECUTION_GUARD,5 BELOW_MIN_NOTIONAL_OR_CAPACITY, and13 have no native fill/rejection row but matching all-invalid charged-guard receipts select zero for that asset. This uses individual saved requests, native evidence and guard witnesses rather than inference from aggregate counts.

The one baseline-only episode, ETH8, has five HELD10 FRESH_TIER_EXECUTION_GUARD zero-paid receipts. All365 daily account statuses are ACTIVE in both runs, and neither retained policy history contains a GUARD50 event. The discrepancy therefore is not documented as Guard50 or a non-ACTIVE-account effect.

The same charged admission code encounters different actual inventory, NAV and collateral paths. Recorded guard/lot outcomes explain the observed filled-versus-skipped episode identities. This does not isolate a ceteris-paribus causal effect or imply that52 campaigns are better or independent.



## External reductions consume the episode

All31 HELD10 external reductions (27 owned +4 other native terminal-window receipts) are matched to genuine same-sign paid CLOSE chains. For each event, no actual paid OPEN/add/reopen occurs for that asset until its original source direction changes. The frozen policy InventoryReduction branch sets episode_consumed=True and clears entry. A separate consumed-state snapshot was not retained at every event; both the code semantics and actual no-topback consequence are documented.

The JSON includes all52 HELD10 campaigns, all24 baseline campaigns, all60 source-episode outcomes, full request/native/guard evidence, all31 external-consumption checks, and immutable terminal/source/policy identities. The sealed initial review and phase erratum remain unchanged.
