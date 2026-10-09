# Covered prequential63 frozen-request adapter

The native tape fold is **2024-01-01 through 2024-03-04 exclusive**, 63 daily
requests at UTC midnight, CORE5 ordered BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT /
DOGEUSDT. Each asset has 90,720 actual trade and mark minutes plus quote-USDT
volume; all five total 945 actual signed funding events. No wallet, model fit,
inference or market download was performed for this preparation.

[TAPE_INVENTORY.json](TAPE_INVENTORY.json) identifies the public H1 input pack
and its original archive/data hashes. The 2023-07-03–2023-09-04 and
2023-10-02–2023-12-04 exclusive folds have daily/funding history but lack native
trade/mark/previous-quote tapes in the inspected recovered/public inventories.
No 2023 acquisition is started. This is a nine-week 2024 block, not a full quarter.

## Adapter and original financial contract

`../evaluate_requests63.py` is a small covered-fold entrypoint over the existing
`../evaluate_requests61.py`, now accepting optional calendar parameters. The
original financial engine is unchanged, SHA256
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.
[ADAPTER_CONTRACT.json](ADAPTER_CONTRACT.json) binds every current helper and
financial source, exact calendar, original financial assumptions, source packets
and fixed-control coefficients. The independent native61 auditor takes the same
explicit calendar; it retains financial, actual-fill/capacity/mark/fee/funding
checks. Model tensors and optimizer states are only hashed, never deserialized.

Fresh startup is the **original** `previous_quote=None`, zero initial capacity,
zero positions and 10,000 USDT. The external 2023-12-31 23:59 trade/mark minute
is absent and is neither synthesized nor imported. The first delayed execution
uses completed in-block quote capacity. First funding before the first completed
mark has no held position. A different contract requiring a prestart quote,
prestart mark or carried position is unsupported.

The account is conditional isolated 1x/MMR .005, guard OFF, with fees 5.5 bp each
side, halfspread/slippage 4/4 bp, signed funding scale1, gross/asset target caps
.6/.3, past30-day covariance/10% annual risk, original .99*currentNAV sizing,
expert daily L1≤.1 after mandatory eligibility release, previous-minute quote
participation .1%, lot1e−8, minimum opening notional10, delayed/partial execution,
reductions first, five-attempt expiry, funding strictly before fills on strictly
prior completed marks, and paid terminal-flat closure with final-day target zero.
The original financial source and original E5 source remain hash-bound. Historical
publication and exchange/account/filter rules remain uncertified assumptions.

Existing 61-day contracts and results remain immutable at commit
`85fa946b4be3d9b3b2b7ffad2ee058f8b33e9014`. Their frozen source contracts bind the
old helper bytes; reproduce those historical versions from that commit. The
current changed helpers require this new contract for the new fold. No frozen
61 contract was rewritten or its source check bypassed.
[LEGACY61_COMPATIBILITY.json](LEGACY61_COMPATIBILITY.json) confirms exact saved
budget/target bytes for both completed weighting paths and a read-only financial
and actual-input audit of the retained date wallet with the default61 parameters.

## Canonical context for the producer

[CANONICAL_CONTEXTS63.npz](CANONICAL_CONTEXTS63.npz) contains:

| Array | Shape | Meaning |
|---|---|---|
| `decision_us` | 63 int64 | Exact daily UTC microsecond grid |
| `symbol_order` | 5 strings | Exact CORE5 order |
| `expert_order` | 6 strings | Original E5 plus appended short slot5 |
| `expert_targets` | 63×6×5 float64 | Unramped covariance-scaled signed expert fractions |
| `expert_eligible` | 63×6 bool | Flat and ineligible remain distinct |
| `target_available_us` | 63×6 int64 | Saved causal availability proxy |
| `past_returns30` | 63×30×5 float64 | Original E5 past covariance inputs |
| `market_close` | 63×5 float64 | Original completed decision-day prices |
| `market_state13` | 63×13 | Original E5 source state, not a substituted feature architecture |
| `market_state13_available_us` | 63 int64 | Original state clocks |

Original E5 slots are CASH / VOL_MANAGED_HOLD / PUBLIC_SMA50_200_SIGNED /
DONCHIAN_EXIT10 / CSMOM21. MOMENTUM30_SHORT_ONLY is appended at slot5. Learned
admitted actions are exactly CASH / VOL / CS / MOM30 short. Export either this
four-name compact order or the canonical six-name order; in the six-name order,
SMA/Donchian requests and admitted masks must be zero/false. Never relabel either
old slot as a private RANK action. Private producer coordinates CASH/VOL/CS/SHORT
lift to canonical0/1/4/5 by their names.

[MOMENTUM_SHORT_CONTEXTS63.npz](MOMENTUM_SHORT_CONTEXTS63.npz) separately preserves
that unchanged short recipe's targets, raw signals, masks, asset clocks and
200-contiguous-bar warmup witnesses. Context generation reuses the existing
momentum recipe and independent scalar checker on past-only daily bars. All
original E5 fields are exact; short raw/state/eligibility and target checks have
zero error. These packets are evaluation inputs, not training labels. Model
training and scalers must use separately bound strict prefixes before Jan1.
The short hypothesis was selected after seeing June2024, so fresh prefix fitting
does not make the strategy-selection history unseen.

## Exact frozen export interface

Use manifest schema `SOURCE_HASHED_FROZEN_NATIVE63_REQUESTS_V1`. Preserve the
existing adapter fields: `arm_id`, `objective_version:2`,
`prediction_role:HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS`, `source_files`,
`files`, `request_file`, `producer_commit`, `expert_order`, `allowed_actions`,
`uses_feedback_features`, `training_cutoff_us`,
`maximum_training_label_available_us`, `maximum_scaler_input_available_us`, and
`actual_fit_completed_UTC`. `files` maps safe relative names to integer `bytes`
and lowercase SHA256 `sha256`; source files must include actual producer Python.
Pin the external manifest SHA and the published adapter contract SHA.

Additional required learned fields are:

- `calendar`: the exact five-field calendar object in ADAPTER_CONTRACT.json.
- `adapter_contract_sha256`: SHA256 of that complete contract file.
- `policy_role:LEARNED_FROZEN`.
- `model_file`, `scaler_file`, `training_plan_file`, `initial_state_file`,
  `initialization_file`, `training_clock_file`, `training_data_files`, `context_file`.
  Every member must be present in `files`; training datasets are bound separately
  from the current evaluation packet and the clock proof.
- `model_sha256`, `scaler_sha256`, `training_plan_sha256`, `initial_state_sha256`
  matching their actual bound members.

`context_file` is a byte-identical copy of CANONICAL_CONTEXTS63.npz. The saved
feature clock must cover the canonical current expert/state clocks, and feature
availability ≤ request availability ≤ decision. Additional model input recipes
remain source-bound producer responsibilities; this packet does not assert
identity to a different feature architecture.

`initialization_file` is JSON with `kind:FRESH_RANDOM_NO_WARM_START`, integer
`seed`, `parent_checkpoint_sha256:null`, `optimizer_updates:0`, and
`initial_state_sha256` matching the actual initial model/Adam/RNG snapshot.
`training_plan_file` is real source-bound JSON containing `prefix_only:true`,
`warm_start:false`, `fold_start_us:1704067200000000`, and the producer's actual
training specification. Keep the real 2026 fit completion timestamp separate
from historical feature/label clocks; never backdate the fitting operation.

`training_clock_file` is a bounded NPZ of five nonnegative int64 vectors:
`sample_decision_us`, `feature_available_us`, `expert_input_available_us`,
`label_available_us`, `scaler_input_available_us`. The first four have one entry
per actual selected training sample. Scaler clocks describe every scaler input
sample. Features/expert inputs ≤ their sample decision, labels > that decision;
all training, label and scaler clocks are strictly before Jan1. Saved maxima
must equal manifest maxima, and training cutoff equals fold start. Source hashes
and these records verify the declared prefix schedule; this worker does not
independently replay the producer optimizer or certify hidden training behavior.

`request_file` is a bounded no-pickle NPZ containing exactly:

| Array | Shape/type |
|---|---|
| `decision_us` | 63 int64 |
| `symbol_order`, `expert_order` | Exact ordered name strings |
| `desired_expert_budget` | 63×exported_experts float64 simplex |
| `action_eligible` | Same shape, bool; canonical eligibility AND admitted actions |
| `feature_available_us`, `request_available_us` | 63 int64 microseconds |

Optional fields are `feedback_available_us` (strictly before each decision;
matching `uses_feedback_features:true`) and the paired `ramped_expert_budget` /
`mapper_target_fractions`. If exported, native budgets/targets must be bit-identical
including forced zero execution targets on the last day. Every unavailable
request must be exact zero. Availability release precedes discretionary L1 .1;
its compulsory transfer to CASH is not a license for excess discretionary ramp.
No synthetic timestamps, translated calendar or unbound context arrays are accepted.

Fixed controls may export `policy_role:FIXED_CONTROL`, `arm_id:STATIC50` or
`CASH50`, actual source/request members, and an actual bound `training_plan_file`
used as an export plan: `{policy_role:FIXED_CONTROL,fits:0,calendar:<exact>,control:<arm>}`.
They have `model_sha256:null`, `scaler_sha256:null`,
`actual_fit_completed_UTC:null`, real `actual_export_completed_UTC`, and training/
scaler maxima0. The `training_plan_sha256` binds that export plan. No learned
initialization/training packet is required for a fixed rule. Their canonical
request coefficients are exactly STATIC50 `[0,.5,0,0,.5,0]` and CASH50
`[.5,.25,0,0,.25,0]`. These are expert request coefficients, not literal NAV weights;
all native ramp/risk/cost rules still apply.

## Preparation and future execution

Use the existing dependency recipe, one CPU, 6 GB address space, 600 seconds and
15 GiB disk reserve. From the checkout, with COIN_STATE set to the saved cloud
state directory, preparation is:

```bash
PYTHONPATH="$COIN_STATE/deps" python3 research/recover-frozen-runner-20261009/evaluate_requests63.py readiness --state "$COIN_STATE"
```

With a real published export, `check` additionally requires `--manifest`,
`--manifest-sha256` and `--contract-sha256`; it performs no wallet. `run` further
requires a public request-specific execution plan, external plan SHA, its commit
and a fresh output. The plan must bind request/contract/arm, this calendar and
`authorization:USER_AUTHORIZED_REAL_FROZEN63_NATIVE_EVALUATION`. Only actual user
authorization permits creating that plan; the string does not supply approval.
Current status is **NO_REQUESTS / NO_WALLETS_AUTHORIZED_OR_RUN**. No output or
request ledger is reserved by readiness or check. No fallback policy is launched.

76 fixture cases validate default61 compatibility and the new63 calendar,
source hashes, strict prefix clocks, fresh initialization, masks/slots,
availability release/ramp, control parity, zero first capacity, costs, signed
funding/prior marks, resource counters and paid closure. Synthetic journal tests
stub the financial auditor and explicitly do not represent account outcomes.
Actual63 trade/mark/funding grids and source bytes are separately checked in
READINESS.json. All testing uses private cloud-state basetemps, no market fetches.

## Completed matched512 native61 results

The separately completed fresh10k May1–July1 exclusive2024 pair is at immutable
commit `85fa946b4be3d9b3b2b7ffad2ee058f8b33e9014`:

- README: `research/recover-frozen-runner-20261009/temporal-weighting512-native61-results/README.md`
- Exact results: `research/recover-frozen-runner-20261009/temporal-weighting512-native61-results/RESULTS.json`

| Completed native61 metric | Date weighting | Half-date / half-equal-episode |
|---|---:|---:|
| Full net PnL, USDT | −467.419024 | −500.488833 |
| May net PnL | −259.285063 | −283.989078 |
| June net PnL | −208.133961 | −216.499755 |
| Full minute drawdown | 6.365858% | 6.458817% |
| Mean actual gross / NAV | 23.205418% | 20.695048% |
| Maximum actual gross / NAV | 45.454263% | 39.240717% |
| Mean actual net signed / NAV | +7.361099% | +7.246290% |

Mixed minus date is −33.069809 USDT, May−24.704015 and June−8.365795. Both shared
initialization, architecture/13,699 parameters and exactly512 updates; only
whole-episode loss weighting changed. Date was publicly preserved before mixed.
Both were complete, independently audited, paid-flat and zero-liquidation.
May–June is already seen development; actual risks differ; proxy−502.47/−521.17
are not these native results. No OOS efficacy, convergence or switching gain is
asserted. Existing references were reused without wallets or fits being rerun.
