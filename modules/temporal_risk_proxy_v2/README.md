# Charged boundary risk proxy v2

Versioned diagnostic correction, separate from the four original temporal fits. Nothing in `modules/temporal_two_expert` or its model/Adam/RNG snapshots is changed. No corrected fitting has run.

The original proxy rejected following-mark exposure drift even when requested and filled targets were within the original caps. The frozen native scheduler instead freezes a uniform reduce-only quantity intent at `min(1, .99*.3*NAV/max_notional, .99*.6*NAV/gross)`, waits one minute plus 1 μs, executes reductions before increases against previous-minute capacity, charges each actual partial fill, and stops on unresolved breach after five attempts. Funding at the fill boundary belongs to the pre-fill quantity and uses a strictly past mark. Native openings retain the .3 asset/.6 gross checks.

`charged_boundary_path` implements the smallest **continuous daily-boundary surrogate** of that correction: explicit frozen reduction intents, individually charged partial fills, five-trial expiry, unchanged hard target/opening caps, full chronological cash/position feedback, original funding coefficients, original downside/log-return utility and paid terminal cash. Every output carries its objective and execution-plan identity. `BoundaryPlan` requires a diagnostic capacity declaration; there is no inferred historical liquidity. Fees remain 5.5 bp at the adverse fill price, half-spread/slippage each 4 bp. No reduction is netted away against the next rebalance.

This is **not minute-native**: it fills at the immediate constant boundary midpoint, aggregates interval funding, and omits intermediate marks, minute latency, actual liquidity, lot rounding and isolated-margin liquidation. The native contract tests import the unchanged, SHA-bound scheduler and invoke its actual methods against synthetic test accounts. Native imports need the already authorized 2 GB address-space launcher; the first attempt under the smaller recovery launcher failed to map PyArrow. No scheduler body or import binding is bypassed, and no historical native wallet is replayed.

`request_loss_and_gradient_v2(requests, episode, original_prototype, plan=...)` returns mean loss, exact request VJP for this continuous surrogate and its report, using the unchanged original `mapped_path` and `mapping_vjp`. `charged_path_loss` exposes that VJP to a Torch neural head. Inputs remain a complete chronological E5 request path (only slots 0/1/4 used), the original immutable episode and an explicit boundary plan. No wallet features, hindsight labels, artificial episode stitching, optimizer or checkpoint rewriting are added. Derivatives are piecewise; cap activation, absolute-value/max ties, capacity/min switches and quantized native lots are discontinuities. Finite differences test stable branches, not a smoothed native derivative.

Reuse the installed dependencies and [pinned recipe](requirements.txt); Torch CPU wheels use the existing official recipe. From the repository root:

```bash
PYTHONPATH=.:src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python -m modules.temporal_two_expert.bounded_comparison \
  --report /tmp/charged-proxy-resources.json \
  python -m pytest modules/temporal_risk_proxy_v2 -q

PYTHONPATH=.:src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python research/two-expert-exact-recovery-20261009/runtime-delta/source/bounded_recovery.py \
  --report /tmp/charged-witness-resources.json \
  python -m modules.temporal_risk_proxy_v2.diagnose \
  --state /path/to/verified/temporal-two-expert-state \
  --output /tmp/charged-witness.json
```

The 182 original reference dates have identical no-reduction NAV, utility and request gradients. The saved 62-day stochastic witness still triggers the original stop at day 49: gross .6005080861. This declared full-fill surrogate charges .088131118 USDT, scales quantity .9891623673 and leaves gross .5940052188, then completes a paid close. Three mapped-request finite differences around that witness agree within 3e-12 absolute error. These are simulated diagnostic quantities, not a native result or a new fitted model.

Corrected native fitting remains gated: the available packet has daily endpoints and funding coefficients, with existing funding-event Parquets, but no minute trade/mark/previous-quote tape. Identical daily endpoints can hide different native mandatory reductions. Existing declared research filters and risk assumptions can remain fixed; historical exchange certification is not an added prerequisite. `require_native_resume_data` fails closed until minute/event source and declared native contract are bound, and a native differentiated bridge is actually implemented and tested.

Saved Adam moments/RNG are valid for an explicitly versioned warm restart under a changed objective. That would be a resumed corrected-objective experiment, not a clean four-fit comparison. Future stage metadata must retain parent checkpoint SHA/step, objective and tape identities, separate convergence history, and the existing model/split/seed/cost/risk/resource limits. No matched rerun is justified merely by changing objective; no rerun or resume occurred here. See the [numerical receipt](../../research/temporal-risk-proxy-v2-20261009/NUMERICAL_RECEIPT.json) and [test receipt](../../research/temporal-risk-proxy-v2-20261009/TEST_RECEIPT.json).
