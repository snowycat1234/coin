# Exact cached July continuation

The two immutable 256-update checkpoints and July comparison protocol from 27f8a91ecdde570bd837eaf89699a49b35ace65d are unchanged. This portable continuation restores the previously serialized numeric feature rows and economic contexts from 90b8fd65d092b52091b3fee7717c0478b265bc6e. Its reconstructed episode, every context array, and complete input binding match the original paired preflight exactly. Raw-event reconstruction is REUSED from the original producer's receipt, not independently rerun here. This avoids re-downloading market archives and preserves the known August 12 minute-mark gap.

The old saved Codex turn failed on usage quota. Its unpublished temporary output directory cannot be inspected from this computer. The latest public branch has only the zero-inference preflight; this checkout's 28 saved result receipts contain no exact checkpoint/calendar pair. The previous directory is not deleted or modified. This computer makes one recorded execution of the fixed pair, without outcome-based selection, new training, or alternate recipes. If an earlier unpublished result is recovered later, compare identities and deterministic outputs rather than treating it as a new trial.

Original frozen fitting and evaluation sources remain unchanged. The paired evaluation loop is copied verbatim into modules/temporal_cached_july/evaluate.py, with explicit imports of the cached loader and an additional source-identity publication gate. Two cache identity/tamper tests and four original paired tests pass. The portable resource launcher retains one CPU/thread, 2 GB process RSS, 4 GB address space, 1,200 seconds, no swap/GPU; because this computer lacks a cgroup mount, it additionally stops at 8 GB host used memory measured as MemTotal minus MemAvailable. No financial limits change.

Use Python 3.12 and research/temporal-added-history-july-20261010/requirements.txt, plus requests (a transitive import absent from that short requirements list). Restore the existing recovery ZIP into STATE/recovery. No feature or market download is required by the cached loader. Verify public code and PRESCORE bytes, then run once with an exclusive output directory:

    PYTHONPATH=.:src python research/temporal-cached-july-20261010/bounded_cloud.py --report STATE/PAIR_RUN.json python -m modules.temporal_cached_july.evaluate run --state STATE --economics STATE/unused --output STATE/paired-once --publication STATE/CACHED_PUBLIC_READBACK.json
    PYTHONPATH=.:src python -m modules.temporal_added_history_july.verify --output STATE/paired-once

The public readback receipt must include both original and cached PRESCORE paths and exact SHA256 values. Additional cache source hashes are bound before scoring. No predictions or wallets have been run at this preflight publication.

## Completed fixed comparison

Both wallets completed; no new fitting, normalization, control reruns, or native wallets. All 126 saved daily rows and model/source identities independently verified; maximum accounting residual 2.39e-12 USDT. Runtime 3.01 seconds including imports, peak RSS 467.3 MB. Frozen evaluation itself 0.99 seconds.

CORE5 BTC/ETH/SOL/XRP/DOGE, each wallet fresh 10,000 USDT. July 1, 2024 to September 1 00:01:00.000001 UTC paid close (63 decisions, 62 active intervals).

| Policy | Net USDT | Cumulative return | Daily MDD | Mean opening gross | Mean opening signed net |
|---|---:|---:|---:|---:|---:|
| 773 active-date model | +40.26 | +0.403% | 3.730% | 9.116% | +7.685% |
| 1137 active-date model | -22.98 | -0.230% | 3.973% | 9.976% | +8.642% |
| Reused Static50 | +137.07 | +1.371% | 2.390% | 18.636% | +6.441% |
| Reused Cash50 | +104.64 | +1.046% | 1.201% | 10.582% | +3.589% |

Expanded minus original is -63.24 USDT. July contributes -46.86, August -16.37, and paid-close difference -0.01. Price PnL difference -62.71, funding difference -0.60, cost saving +0.07. Asset contributions to the difference: BTC -3.03, ETH -30.13, SOL -15.74, XRP -0.10, DOGE -14.23 USDT. These are accounting attributions, not causal demonstrations of predictive skill.

Costs unchanged: fee 5.5 bp per side, half-spread 4 bp, slippage 4 bp; actual signed funding. Original isolated 1x context, target gross cap 60%, per-asset cap 30%, annual covariance-risk target 10%, daily budget L1 cap 0.1; realized exposures are reported separately. Daily full-fill model and terminal accounting are not a minute-native exchange simulation. Minute mark bars opened August 12 10:02/10:03 UTC remain missing; no synthetic fill or restriction bypass.

The previously reported Q4 daily improvement +184.05 USDT (native +179.25) does not generalize to this second seen period. This is a single-seed, fixed-update comparison, with common frozen scaler; more history changes the training mixture and compute per update. No claim that more history generally hurts, no selector impossibility conclusion, and no promotion.

Current comparison best raw net return is Static50, but risks differ; Cash50 achieves higher net and lower drawdown than both learned models in this period at similar gross exposure to the expanded model. Neither is evidence about the real Bybit robot population. No reliable live expected APR or CAGR estimate is available. Returns above are cumulative historical development returns and are not mechanically annualized.

Next: inspect the two saved paths and added-history feature distribution to separate changed exposure/allocation from genuine timing improvement before selecting another controlled training experiment. No extra wallets or training in this module.
