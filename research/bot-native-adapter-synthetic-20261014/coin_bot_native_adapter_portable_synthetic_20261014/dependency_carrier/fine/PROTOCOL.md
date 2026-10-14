# CORE5 quantity-resolution sensitivity: review gate

Status on 2026-10-13 UTC: **prepared only; zero fine-grid historical wallets executed.** Parent review and a separate GO are required. This is an offline simulation of one accounting assumption, with no order transport, credentials, uploads, downloads, new optimization, or new strategy choice. The existing coarse histories are read as already completed and are never rerun.

## Question and fixed design

How much of the observed profit, drawdown, unfilled reduction, terminal residue and account-halt behavior comes from the coarse assumed base-asset lot grid? Run the same frozen CORE5 daily targets, Binance trade/mark/funding observations, BASE27 5.5 bp taker fee plus 4 bp half-spread plus 4 bp slippage per side, prior-minute quote-volume × 0.001 participation capacity, 10,000 USDT one-way isolated 1× wallet, 0.005 MMR, shared free cash, no top-up, 0.30 per-asset/0.60 gross caps, causal minute timing, closing exemption and five genuine terminal reduction attempts. The sole financial assumption changed is quantity resolution, including the assumed minimum quantity equal to a single step. The protective policy is the **same frozen 50% isolated-equity full-exit adapter**, enabled or disabled as a second fixed mode. Its fill feasibility can change *because* the lot step changes.

The coarse conditional grid is BTC 0.001, ETH 0.01, SOL 1, XRP 100 and DOGE 1000 base units; its byte identity is `94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf`. The new single fine/integer-neutral limit is the shared account's pre-existing `InstrumentProfile()` default for every symbol: **0.00000001** base units, with assumed minimum quantity one step, unchanged **10 USDT minimum notional for openings only**, and **minimum-notional exemption for closing legs**. This `FINE_PROFILE.json` has SHA-256 `ac2deafbd26546e511fc3f43e40164c15f4da81822dde2ddc89add666b8d07a8`. The exercise does **not** assume this fine grid is an actual Bybit filter. The current Bybit public instruments-info read returned 403 in the separate source review; do not retry it here, work around it, or infer dated 2023–25 filters from current docs. Exchange fees, risk tiers, liquidation mechanics and historical market provenance remain conditional. There is no new performance promise or out-of-sample claim.

There are **six fixed year/arm pairs × two modes = at most 12 new fine-grid wallets**:

- 2023: `STATIC50` (CS + HOLD) and `COMBINED` (exact half of STATIC50 + SMA200_10PCT)
- 2024: `STATIC50` and `EXACTHALF` (same exact half-sum)
- 2025: `STATIC50` and `COMBINED`

Each gets ORIGINAL and GUARD50 fine-grid modes. All six coarse originals and all six coarse GUARD50 cases are existing results; **zero coarse reruns**. No arm, year, guard threshold, grid increment or fill rule is selected by these outcomes. Fine-grid runs must start from fresh 10,000 USDT state, never a coarse checkpoint. The 2023 STATIC50 comparator is the *executed* portfolio-risk-budget P2 target archive beginning `e81bf92d`, not the older `023ebb19` component input. All 12 cells share the exact archived daily matrices. The full binding for each pair, including year source index and target archive/array SHA-256, published baseline identity, local coarse result hashes where present, and guarded result/binding hashes is in `CASE_BINDINGS.json` (SHA-256 `68379d5adf916f06695bb64163f9dcf33b593a60167db26a8ec2782456eac9a2`). `preflight.py` verifies it against the frozen guard manifest, baseline identity audit, all source months, source daily/events records and exact target arrays. The 2024 window keeps its previously documented ten-mark overlay unchanged.

## Outputs and interpretation

For every new case, preserve source/target/profile/code binding, lossless 30-day and terminal checkpoints, full account trade/funding/rejection/protection journals, daily NAV, numerical minute fingerprint, independent signed-inventory and Decimal NAV bridge, resource receipt and result. Report completed versus required minutes, halt/status, paid-flat eligibility, marked-at-stop PnL, minute maximum drawdown, accepted trade legs and rejected-intent reason counts, actual gross exposure, terminal residual quantity/gross marked notional, protection triggers/full exits and deferred no-lot minutes. Distinguish a model halt from an exchange liquidation: there is no simulated liquidation fill. PnL is a **paid cash return only when the full calendar completes and the terminal inventory is flat**. A full year with residual inventory yields marked PnL, not paid PnL. A halted case has only partial marked-at-stop PnL; never compare it to a full-year return. For drawdown/exposure comparisons of unequal horizons, use a common observed prefix and label it; never report a spurious full-calendar difference.

The primary paired contrasts are fine minus coarse within each exact year/arm/guard mode, plus guard minus unguarded within each grid for the 2025 adverse-effect check. Display all six pairs and both guard modes, including negative or stopped outcomes. Report absolute and relative trade acceptance/rejection changes by reason, mean/max realized gross exposure, profit/marked-value status, DD, residue, and halts; leave a metric null if the published coarse original lacks its required journal or common-prefix evidence. There must be no silent favorable-case selection. The output is assumption sensitivity, not a tradability verdict or venue certification.

## Safety and runtime

`run_cases.py --check-only` and `test_pure.py` are nonhistorical checks. `run_cases.py` cannot launch a history without `--parent-go` plus a fresh `state*` root directly under this module. The controller then binds a nonce and exact code/input hashes before any worker; direct workers require this binding. It reuses the reviewed guard runner's resource admission, one-CPU/4GB address-space process limits, 2GB sampled RSS stop, 1200-second wall/CPU cap, 250MB per-wallet state cap, 8GB host-used RAM cap, zero-swap check and 15GiB disk reserve, with at most two independent workers. A resource or wallet failure stops the remaining queue and retains genuine partial state; it cannot be relabeled complete. Python optimization is forbidden so the frozen source assertions remain active. No credential, remote API, live market action, payload publishing or uploader access is in scope.

Before financial or frozen-transport imports, the stdlib-only `freeze_bootstrap.py` verifies exact SHA-256 bytes for `fine_account.py`, `run_cases.py`, `preflight.py`, `PROTOCOL.md`, `FINE_PROFILE.json`, `CASE_BINDINGS.json`, and `test_pure.py` against `FROZEN_CODE.json`. Its SHA-256 is pinned in the separate `REVIEW_RECEIPT.json`, avoiding a self-hash cycle. The fine account hash and freeze-manifest hash also enter each controller/worker run binding. A synthetic test tampers with a copied fine-account source and verifies fail-closed rejection. Any reviewed-module edit requires a new manifest, receipt, review and GO; the frozen coarse/guard source is never modified.

Observed coarse guarded timings were roughly 221–365 seconds per wallet; earlier unguarded half/2024 wallets were roughly 187–229 seconds. The 1e-8 grid may substantially raise fill/journal work, so a cautious **4–8 minutes per fine wallet, about 25–60 minutes for 12 with two admitted workers** is only a planning estimate, plus cold audit/reporting. Every wallet retains a hard 20-minute cap; budget stops are partial results, never imputed. Recheck RAM, disk and CPU at GO.

Review commands from the workspace root:

```sh
PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python coin_quantity_resolution_20261013/run_cases.py --check-only
PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python coin_quantity_resolution_20261013/test_pure.py
```

Only after parent review and a separate GO, the launch shape would be:

```sh
PYTHONDONTWRITEBYTECODE=1 coin_native_half_mix_20261013/.venv/bin/python coin_quantity_resolution_20261013/run_cases.py --parent-go --state-root coin_quantity_resolution_20261013/state_GO_DATE
```

Do not run that launch command during preparation. This module does not access or repackage the separate blocked 2025 checkpoint uploader payload.
