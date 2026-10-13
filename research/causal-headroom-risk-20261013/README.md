# Fixed causal headroom risk candidate: preflight only

This is one economic candidate with three prescribed wallets, 2021/2023/2024 original fine STATIC50/CSH. No historical candidate wallet has run in this preregistration. Existing base, guard50, daily reentry, SHORT50 and earlier-terminal experiments remain separate, including their failures.

The only new decision is the reviewed execution_headroom_buffer_v1 trigger on the current candidate account's own signed quantity, isolated collateral/equity and completed mark. The unchanged GUARD50 execution methods preserve real costs/capacity, full-exit persistence, hard-risk priority, same-sign lock/reset and the original five-open year-end convention. PROTECTIVE_STOP is persistent beyond five attempts; ordinary TERMINAL is not. Missing, derived, invalid or short feature windows add no protection and remain visible as coverage gaps. Historical stress maxima are empirical envelopes, not future risk bounds.

2025 is inferred no-op reuse of its original complete 525600-minute financial path, based on every hash-verified original chunk and the false-gate identity proof. It is not a newly executed candidate wallet. Its original five-open marked PnL and residual positions are preserved; paid_flat remains false. Never substitute the distinct later terminal60 account.

## Portable layout

The preregistration folder contains common candidate code and runtime_dependencies with 45 exact original dependency files in their original relative layout. Market-minute sources and feature NPZ archives are deliberately not committed. inputs contains byte-identical existing target archives and original 2024 derived-cell provenance for independent preparation.

Use an existing trusted Python environment with numpy and polars. Set B to the absolute preregistration folder. For remote use, W is B/runtime_dependencies; locally W is the existing workspace root. Source roots, target archives, feature archives and state output paths can be passed explicitly; paths are recorded separately from the immutable input identities.

The pure feature rebuild needs no financial simulation. With a restored original2024source S, use:

python "$B/run_cases.py" --workspace-root "$W" --years 2024 --source-root "$S" --derived-csv "$B/inputs/2024_DERIVED_MARK_OHLC.csv" --rebuild-features /absolute/fresh/Y2024.npz

The rebuild rejects any source-index/month/provenance mismatch and must reproduce the exact frozen feature archive and every float64/ready/reason array hash. No interpolation, source download, fit or wallet is permitted in preparation.

Check the restored2024 inputs without starting a wallet:

python "$B/run_cases.py" --check-only --workspace-root "$W" --years 2024 --source-root "$S" --target-archive "$B/inputs/Y2024_TARGETS.npz" --feature-archive /absolute/fresh/Y2024.npz

Synthetic tests can use the same dependencies:

COIN_HEADROOM_WORKSPACE="$W" python "$B/test_synthetic.py"

Only after exact-byte independent review, verified remote publication, fresh resource admission and a separate parent GO may the controller run. Local years2021/2023 run serially in one executor batch; cloud2024 runs alone from the same code. The controller has one worker per executor, one CPU, 2GB sampled-RSS/4GB address space, 1200 CPU/wall seconds per wallet, no swap/GPU, shared host8GB and15GiB disk reserve, with250MB genuine state per case. Current worker RSS is already included in host used memory; only the unused portion of its reservation is added, avoiding the prior duplicate-reservation stop.

No automatic rerun or new wallet is allowed after a resource/program/integrity stop. An audited negative economic halt does not censor other prescribed cases. Genuine partial states and real residuals are retained; no fabricated fill or paid-flat claim is allowed.

Objective: establish whether this fixed risk policy avoids the2024halt, quantify any2021/2023return damage, and preserve2025noninjury. This is seen-sample execution/risk evidence, not guaranteed strategy improvement or live APR.
