# Explicit surrogate v2 warm restarts

Resume the same four temporal arms from their original terminal model, Adam moments and saved RNG. Original files remain immutable; new stage output lives under an exclusive `surrogate-v2` directory. Objective v2 uses the separately tested charged daily-boundary continuous surrogate with declared full fills. It is conditional simulated execution, not minute-native, exchange-certified or unseen validation.

Features, CORE5 order, real64-day masks, train-only scaler, 778 training dates/five real wallets,61 seen development dates, seed20261009, dropout.1, Adam.001, clip1, costs, mapper, action pool and paid terminal rules remain unchanged. No model-observed wallet state is added. Each v2 stage receives the same1024-update/1200-second budget. Saved Adam step/moments remain cumulative; convergence uses the unchanged rule on a fresh v2 training-only loss/gradient baseline. No old or development-selected epoch is used.

`check` verifies all four exact parent snapshots, finite v2 training loss/gradients and preserved RNG without optimizer steps. `run` schedules at most two independent workers, one CPU/2GB each, under the existing shared8GB/swap0/GPU0 limit. Atomic checkpoints retain the parent SHA/step, v2 source identities, optimizer/RNG and convergence history. Failures retain the last atomic completed update and are explicitly reported. `score` requires all four terminal snapshots; it exports seen surrogate metrics, terminal model/Adam/RNG and daily request paths for the separate native-validation task.

Reuse [the correction dependency recipe](../temporal_risk_proxy_v2/requirements.txt). Commands from the repository root:

```bash
PYTHONPATH=.:src python -m modules.temporal_two_expert.bounded_comparison \
  --report /tmp/v2-tests.json python -m pytest modules/temporal_surrogate_resume_v2 -q

PYTHONPATH=.:src python -m modules.temporal_two_expert.bounded_comparison \
  --report /tmp/v2-check.json python -m modules.temporal_surrogate_resume_v2 check \
  --state /path/to/verified/temporal-state --output /path/to/verified/temporal-state/surrogate-v2

PYTHONPATH=.:src python -m modules.temporal_surrogate_resume_v2.bounded_controller \
  --report /tmp/v2-controller.json python -m modules.temporal_surrogate_resume_v2 run \
  --state /path/to/verified/temporal-state --output /path/to/verified/temporal-state/surrogate-v2
```

Eight synthetic safeguard tests cover all-four-arm gradient/dropout replay, exact warm Adam/RNG continuation, interruption, failure retention, unchanged parent bytes and the all-terminal export barrier. They perform no historical economic optimizer updates. The previous77 correction/original tests remain valid and their frozen sources stay unchanged.
