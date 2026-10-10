# One prefix-selected static expert benchmark

Choose the largest mature-prefix arithmetic mean of cost-after 21-active-day
standalone returns among VOL, CS and MOM30 short/cash. Use exactly the common
371/462/553/644 labels from the closed direct-contrast study. Original gaps,
full label maturity and paid-terminal exclusions remain intact; no alternative
weighting, lookback, threshold or choice rule. CASH is excluded as a candidate,
including when all means are negative. Expert inactivity and mapper cash remain.

Choices are SHORT/VOL/VOL/VOL for July/October/January/April. They are frozen
before forward evaluation; no forward data enters the choice function. The
constant one-hot request persists for all63 decisions. The unchanged mapper
starts in CASH, takes20 decisions to reach full expert budget (L1<=.1/day),
respects current eligibility and .6 gross/.3 asset caps, and pays final closure.
Each fold is one continuous10k shared CORE5 wallet. Same funding, costs and
charged risk reductions. Existing Static50 and Cash50 are independent controls.

Reuses cached standalone histories and the existing surrogate engine; no
training, new data, downloads or native replay. Four selected paths will be
checked bitwise against their cached controls. The benchmark is not a learned
selector. These repeatedly examined blocks are historical development, not
novel OOS or statistical-strength evidence. Prefix means use overlapping,
state-conditioned standalone labels; they are not realizable switching returns.

[Choices/means/maturity](FROZEN_SELECTIONS.json), [rule/source hashes](PROTOCOL.json),
[duplicate check](DUPLICATE_CHECK.json). Three causal/negative-mean/tie/identity
checks pass. Python3.12/NumPy2.5.3; installed Torch2.6 CPU for surrogate replay,
pytest9.1.1/Ruff0.16.9 for tests. No installation. Through the existing bounded
guards, with checkout/src in PYTHONPATH:

```bash
python -m modules.temporal_prefix_static_baseline.baseline --root CHECKOUT --destination NEW_SELECTIONS.json
python -m modules.temporal_prefix_static_baseline.evaluate --root CHECKOUT --state STATE --selections NEW_SELECTIONS.json --producer-commit FROZEN_COMMIT --destination NEW_OUTPUT
```

The selection file must exist in FROZEN_COMMIT at its public canonical path
before evaluation. Export canonical seven-field E6 native63 requests with
selection/source/context identities, current masks/clocks, fresh cash startup
and paid terminal contract. Native rollout remains NOT_RUN pending a decision.
Stop after this specification.
