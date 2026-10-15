# Bounded isolated-margin account continuation V1

Status: generated-only primitive candidate for root review. No historical wallet was created or replayed, and no live API, keys, orders, external capital, historical market-source downloads, holdout access or publication were used. The existing frozen NO_TOPUP baselines are unchanged. This directory is a new module, not a patch that resets their HALTs.

## Frozen comparison and attribution

The three variants are fixed at account construction and cannot be changed through their public properties:

- A, NATIVE_STOP_REFERENCE: no transfer or conditional position settlement. Exact native finance and whole-case stopping behavior remain the reference. BASE27 and STRESS43 generated goldens match.
- B, CONTINUE_ONLY: unchanged strategy/admission plus the same explicitly conditional position settlement and continuation. It has no new Guard50 warning transfer or warning exit.
- C, TOPUP_THEN_CONTINUE: the bounded margin-management package: Guard50 monitor, internal top-up first, then paid reduce-only exit if the budget cannot complete the top-up, plus the same conditional settlement used by B.

C minus B is the effect of this whole management package. It is not a pure transfer-only causal increment. There is no fourth policy, parameter search, or optional headroom-trigger axis. Comparing C's completed-calendar return with A's unfinished HALT prefix is not a valid annual-return improvement claim.

The high-level fact that baseline isolated shorts had halted was already known before this candidate was written. The new formula uses no failed-case date, trigger price or fitted outcome. POLICY.json is frozen before any candidate historical outcome, not a claim of ignorance of the old baseline diagnostics.

## Fixed policy

Start with the same shared 10,000 USDT wallet, isolated one-way 1x positions and the existing coarse quantity assumptions. The default constructor loads QUANTITY_PROFILE.json: BTC .001, ETH .01, SOL 1, XRP 100, DOGE 1000. These are research assumptions, not historical or current venue filters. Fine-grid profiles appear only as explicitly labeled generated boundary-test overrides.

After a healthy native event, calculate actual isolated equity E = B + q(mark-entry), where B is actual remaining isolated collateral. In C only, trigger at E <= .5B, the existing Guard50 fraction. Request x = max(0, B-E). A completed transfer restores equity to the pre-transfer B; the new collateral becomes B+x. No new hysteresis or fitted threshold is introduced.

Allocate existing free cash only, with free wallet at least 1000 and total isolated collateral at most 8500 after every transfer. Rank positions by equity/maintenance, ties by frozen account symbol order. This is deterministic sequential allocation, not a claim of economically optimal allocation. A shortage spends only the available budget and creates a persistent full-actual-position reduce-only intent. The C exit lock blocks new increases while an exit remains pending. No quantity is added, averaged down or rounded upward for exposure.

Transfers have their own exact journal and idempotency keys. NAV, quantities, fees, funding and realized PnL are unchanged by each internal transfer. A transfer is allowed only at the current native event clock, using a genuine fresh observation, while that position is still healthy. Stale or explicitly unknown/derived observations permit neither top-up nor new increase. There is no top-up in the liquidation-trigger hook and no rewind after a native trigger.

Paid reductions use the native Decimal close accounting, fee/friction, min-notional close exemption, execution latency and five eligible opens. Expired requests renew causally and wait again. Capacity is the reused .001 participation calculation on the completed prior-minute quote volume, shared per symbol/open with all other legs. The adapter must register other actual fills with unique IDs via consume_capacity. Partial fills retain the full-close intent. Proportional collateral release alone does not improve the remaining isolated E/value ratio; a generated test proves that identity. Full existing actual lots may close without imposing a newly coarser assumed research step, when actual capacity covers the lot.

The cash floor constrains internal transfers and new increases. It does not block a paid reduction or close. Positive solvent remaining capital below the floor stays in CASH_ONLY_MONITOR and can advance the clock. Actual unpaid liabilities remain permanent BANKRUPT_HALT. Such debt can exist while other locked collateral keeps whole-wallet NAV positive; this is labeled DEBT_SETTLEMENT_BLOCKED, not automatically whole-wallet insolvency. No debt-settlement path is implemented or silently promised. A generated two-position test preserves that positive-NAV debt boundary.

## Explicit settlement uncertainty

The settlement mode is independently frozen at construction for the whole experiment:

1. UNKNOWN_UNSETTLED: a native-triggered HALT stays unresolved. Keep inventory, debt and witness; cash monitoring is not an assertion that the inventory was settled.
2. CONDITIONAL_COLLATERAL_FORFEITURE: use the existing fixed .005 E <= maintenance trigger as a research model, then reuse the exact _takeover method from the pinned c4919c7 Bybit-style source. This is a conditional position-level own-collateral-loss scenario, not a venue-certified fill or historical liquidation process. The modern Bybit LP formula in that source is deliberately not substituted into the existing native trigger.

A takeover removes only the affected position and its actual remaining collateral, realizes that collateral loss once, blocks stale signals, and recalculates the remaining wallet. There is no separate invented liquidation fee and no observed free-wallet cash credit. Other positions may continue only if solvent and under the unchanged gates. Genuine unpaid funding/fill debt is checked before any hypothetical takeover and is never forgiven.

A mark jump can leave negative marked position equity. Eliminating that negative equity assumes value support from a conditional insurance/clearing mechanism. It is not merely 'no cash credit'. Every settlement explicitly balances:

marked equity before + conditional insurance value received - positive residual forfeited = zero equity after.

The same signed settlement value cashflow equals the before/after NAV difference and has a zero-error ledger. Positive residual forfeiture is also explicit. Economic reports separately show cumulative conditional insurance overshoot absorption and marked/paid-cost PnL excluding the conditional settlement value. This excluded-value calculation is an accounting decomposition at the observed mark, not a realizable exit-price claim. The native summary's ordinary realized/net numbers alone must never be used to hide the support assumption.

No native partial-liquidation sequence, historical tier, intraminute trigger, insurance sufficiency, ADL or execution latency is certified. UNKNOWN_UNSETTLED and conditional forfeiture are alternate disclosed scenarios, not proven best/worst bounds for all venue outcomes. Never switch modes after seeing returns. An unsettled case cannot receive a full-calendar paid return. A conditional settlement is not reported as ordinary paid_flat; settled_flat_under_declared_model is separate.

## Source reuse and verification

SOURCE_PROVENANCE.json and PRIMITIVE_PINS.json contain exact paths, hashes and references. The constructor checks the fixed manifest SHA and primitive bytes. Existing native _leg and apply_funding are inherited unchanged. Native fills are reused rather than reimplemented; the wrapper adds gates and the exact full-existing-lot closing exception. The existing headroom module is retained, but only spend_capacity is active in V1. Headroom-trigger inputs are rejected.

The fetched takeover source is exact Git blob 5c630ff8ebccebff69ddb17318bd39c5e4c0dac5, 13,844 bytes, at c4919c71144d5e94eb0a20f644f6f12fa44869c8. Only _takeover is called. Its parent-base snapshot validation is not reused to imply compatibility with this different account.

Current official help references were verified read-only and recorded in OFFICIAL_REFS.json. They support broad isolation/takeover and fee distinctions only. They do not validate the generated model or historical 2024 behavior. The official margin-calculation change starts in September 2025, so a modern rule must not silently certify earlier history.

## Tests and recovery limits

Run, from this directory:

python -B -m unittest -v test_continuation

Tests use generated observations only. They cover native BASE27/STRESS43 goldens, pre-crossing transfer, direct mark jump, stale/unknown marks, cash/isolated ceilings, five symbols including the default coarse profile, no transfer PnL, paid partial/full/terminal closure, proportional release, genuine unpaid debt, insurance/forfeiture ledger, known-ID replay/conflicts, shared capacity, latency/expiry, global policy clock, invalid-batch atomic rejection and fill-ID collisions.

snapshot() is evidence export only. from_snapshot() intentionally raises. fork_for_preview() is an independent in-memory copy of all new financial/journal/blocked/pending/capacity state; immutable profiles may be shared and external callbacks are suppressed. A generated test proves fork isolation. This does not certify restart/recovery. New increases reject a charged probe that forces conditional settlement.

The full native V3 32-corner preview, shared pending wallet, mark-quality sidecar, scheduler retry/terminal behavior and persistent-journal integration have not been admitted or certified. A plain-account clone must not discard continuation state. No historical entry point exists in this candidate.

## Minimum next experiment plan, requiring separate root GO

1. Seal primitive source/policy/tests after independent generated review. Keep all frozen baseline outputs, code and HALT witnesses immutable.
2. Build a separate generated-only native V3 integration. Preserve mark/funding/fill ordering, all charged 32-corner previews and shared pending capacity. Every hypothetical fork must retain all continuation state; any new OPEN requiring forced hypothetical settlement must be rejected. Prove native baseline-disabled golden equality and no actual mutation across every corner.
3. Freeze the precise event phases. The current scheduler processes funding strictly before the minute close, then the native close mark/_risk, then same-clock funding, then risk scheduling; funding uses a strictly prior causal mark. Do not interchange these phases. Run the C monitor only after the complete healthy same-clock mark/funding batch, before new intents. A native mark that already triggers cannot be rescued by later monitoring. Exercise same-clock ownership and debt cases in generated integration tests.
4. If recovery is required, separately prove restart by complete event/journal replay, including transfers, blocked signals, policy operations, pending reductions, native fill/funding identities, capacity and settlement value. Until then, reject resume and rerun only from an explicitly admitted fresh genesis.
5. Obtain root historical admission for exact source hashes, existing unlocked sources, strategy/tier/cost, full calendar and fixed A/B/C plus settlement mode. No 2025 part004403 access, bypass, holdout downloads or publication. The original strategy/tier/quantity/cost axes stay fixed. Do not tune on failed historical dates.
6. First execute one predeclared full-calendar generated-proven integration pilot with runtime/memory envelope; inspect ledgers, paid terminal exit, all liabilities, forced-settlement counts and mode/quality coverage. Additional finite jobs require root approval. Compare C versus B as the entire management-package effect over identical completed calendars. Report A's halted prefix separately with null annual return. Show insurance/forfeiture amounts, unmodeled risk and unresolved cases beside every return; no venue-certified or robust profit claim.
