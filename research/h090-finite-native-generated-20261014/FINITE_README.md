# Fixed finite BTC candidate: generated native integration

This package adds the fixed finite BTC candidate to an unchanged reviewed H090 CONTROL. The inherited README.md and PROTOCOL.json remain byte-identical CONTROL documentation; FINITE_PROTOCOL.json defines the candidate. Nothing here is historical performance research, trading permission, or a profitability finding.

## Fixed strategy and one-wallet ownership

CSH uses the newly fixed 8/9 mapping of the CONTROL proposal. Its 8,000 USDT original-capital budget is current attributed native isolated margin plus cumulative actual fees, funding debits, and owner actual-fill realized losses. Profit and funding credit do not replenish consumed costs or losses.

The finite long-BTC program reserves 1,000 USDT once, with four maximum margin orders of 150, 187.50, 234.3750, and 292.968750 USDT. Actual paid fills, rather than intended quantities, advance each index. Adds use completed causally available marks at or below actual owner fill basis times .95. Stored causal authorizations bind the order index, signal, source decision, trigger, and actual fill request. The -200 USDT owner net-PnL threshold is an exit signal that can be overshot. Original BTC nonpositive decisions permanently retire additions and require a paid finite exit before any CSH short opens.

One native Decimal wallet performs all finance. Owners have no cash accounts, synthetic transfers, opposing virtual positions, or fabricated split receipts. Actual owner economics and native blended-basis realized/unrealized classifications have explicit reconciliation bridges. Tiny cumulative Decimal rounding differences are reported rather than pushed into an owner's PnL. Original account, source readiness, sizing, clock, funding, and cost bodies stay unchanged.

## Reproduction

From this directory, using the externally supplied final SOURCE_FREEZE.json SHA256:

    PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python run_finite_verified.py --freeze-sha SHA256 tests
    python run_finite_checks.py --freeze-sha SHA256 --receipt-dir NEW_DIRECTORY

The bounded command runs the complete inherited and finite tests, a generated four-order demo, and exact owner-budget witnesses under one CPU, one math thread, 4 GiB address space, 60 CPU seconds and 120 wall seconds per subprocess. All receipts use new directories. No historical mode exists. Cold imports compile verified source bytes and reject changed code or cached project-module substitution.

Coverage includes exact 8,000 USDT admission, one cash or quantity tick over-budget rejection, no replenishment by funding credits or realized profits, retained reservations for partial inventory, paid exit before short, shared capacity, causal triggers, actual basis differences, generated funding precision, stop overshoot, and unsupported recovery.

The revised suite has 86 tests: 51 unchanged CONTROL tests and 35 finite/owner tests. An eight-event fractional funding witness exposes a native-minus-grouped-owner rounding bridge of -1e-43 USDT; chronological versus owner-grouped additions are retained. The bridge is never treated as profit or cash. Exact -200 and +/-1e-20 USDT neighbor probes preserve the intended owner-PnL exit decision. A separate engineered add-trigger mark does distinguish the corrected Decimal40 multiplication from prior ambient Decimal28: the threshold increases by 2.77279031500e-27 USDT/BTC for that actual basis. This microscopic boundary change is disclosed, with its exact basis and both thresholds in the owner-boundary evidence.

The rejected 2bf251 revision and its independent failed probes are preserved. Its two admission gaps are corrected only in candidate routing: every causal witness field is rederived from the signal-interval source decision, actual pre-signal owner receipts, and a retained immutable signal-mark tuple; every new reduce-only request is checked against actual owner quantity and direction before native finance. Current owner quantity and basis must match native fill history. Partial adds keep their original signal basis after native two-mark history rolls forward. Native duplicate replay still occurs first, and genuine reductions remain exempt from source/risk/cost increase gates. New regressions compare full native account and owner/program state before and after each rejection.

## Scope and preserved evidence

The inherited loader checksum-reads two already-public 2023/2025 target NPZ archives totaling 50,586 bytes, without parsing or using their arrays. This is not zero historical-file access. Real provider arrival authority, historical source admission, filters and funding certification, independent review and explicit parent GO remain separate gates. Historical wallets and live trading remain NO_GO. Full restore/fork remain unimplemented.

The first generated DEMO.json and prior test outputs are preserved. Development failures remain evidence, including the reproduced cumulative owner-funding roundoff failure that prompted an explicit reconciliation bridge. The recovery directory preserves the pre-continuation candidate source and freeze; no prior receipts are overwritten.
