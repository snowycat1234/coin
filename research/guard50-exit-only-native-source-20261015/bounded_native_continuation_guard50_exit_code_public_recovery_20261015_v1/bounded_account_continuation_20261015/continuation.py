"""Generated-only bounded continuation candidate. No history/API/order transport.

Starts a NEW wallet. Never wraps, rewinds, imports or resumes a halted wallet.
Finance/fills/funding are the unchanged pinned Decimal kernel. Conditional
settlement reuses only the pinned takeover method, not its modern LP trigger.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal as D, localcontext
from hashlib import sha256
import json
from pathlib import Path

from vendor_quant.perpetual_account import (USDTLinearPerpetualAccount, HALTS,
    decimal, timestamp, ZERO, _numbers, InstrumentProfile)
from vendor_quant.bybit_isolated_account import BybitIsolatedAccount
from vendor_quant.execution_contract import ExecutionContractV2
from headroom_buffer import spend_capacity

HERE = Path(__file__).resolve().parent
MINUTE = 60_000_000
POLICY_ID = 'GENERATED_ONLY_BOUNDED_CONTINUATION_V1'
MODES = ('UNKNOWN_UNSETTLED', 'CONDITIONAL_COLLATERAL_FORFEITURE')
PRIMITIVE_PINS_SHA256 = 'b715ed772ab61530a3195d559af2ea8fc8fce0e75b43ece82825c0839833951f'

def verify_primitives():
    raw = (HERE/'PRIMITIVE_PINS.json').read_bytes()
    if sha256(raw).hexdigest() != PRIMITIVE_PINS_SHA256:
        raise ValueError('PRIMITIVE_MANIFEST_CHANGED')
    for row in json.loads(raw):
        path = HERE/row['path']
        if path.is_symlink() or not path.is_file():
            raise ValueError('ORDINARY_PINNED_PRIMITIVE_REQUIRED')
        body = path.read_bytes()
        if len(body) != row['bytes'] or sha256(body).hexdigest() != row['sha256']:
            raise ValueError('PINNED_PRIMITIVE_BYTES_CHANGED:'+row['path'])
    return True


def _identity(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)


class BoundedContinuationAccount(USDTLinearPerpetualAccount):
    """Separate research account, not a baseline class or certified exchange.

    Fixed trigger: existing Guard50 equity <= 50% actual isolated balance,
    Top-up target: restore equity to PRE-transfer actual balance (no fit knob).
    Budget: free wallet above 1000 and TOTAL isolated margin below 8500.
    Deterministic allocator: smallest equity/maintenance, then account order.
    """
    VERSION = POLICY_ID

    def __init__(self, config=None, *, generated_scope, settlement_mode,
                 policy_variant='TOPUP_THEN_CONTINUE', **kwargs):
        verify_primitives()
        if generated_scope != 'GENERATED_FAKE_ORIGIN_ONLY':
            raise ValueError('GENERATED_ONLY_ROOT_REVIEW_GO_REQUIRED_FOR_OTHER_SCOPE')
        if settlement_mode not in MODES:
            raise ValueError('EXPLICIT_CONDITIONAL_SETTLEMENT_MODE_REQUIRED')
        if policy_variant not in {'NATIVE_STOP_REFERENCE', 'CONTINUE_ONLY', 'TOPUP_THEN_CONTINUE'}:
            raise ValueError('FROZEN_THREE_POLICY_ATTRIBUTION_VARIANT_REQUIRED')
        self.generated_scope, self._settlement_mode = generated_scope, settlement_mode
        self._policy_variant = policy_variant
        self._policy_enabled = policy_variant != 'NATIVE_STOP_REFERENCE'
        self._topup_enabled = policy_variant == 'TOPUP_THEN_CONTINUE'
        self.transfer_journal, self.monitor_journal, self.settlement_journal = [], [], []
        self.operation_ids, self.pending_exits, self.capacity_used = {}, {}, {}
        self.capacity_registrations, self.transfer_ids = {}, {}
        self.cash_watch_reason = None
        self.liquidations, self.blocked_signals = [], {}
        self.liquidation_callback = None
        self._exact_closing = None
        self.mark_quality = {}
        self.quantity_profile_binding = 'FROZEN_COARSE_RESEARCH_PROFILE'
        if kwargs.get('instrument_profiles') is None:
            profile = json.loads((HERE/'QUANTITY_PROFILE.json').read_text())['rows']
            symbols = kwargs.get('symbols', ('BTCUSDT', 'ETHUSDT'))
            if any(s not in profile for s in symbols):
                raise ValueError('FROZEN_FIVE_SYMBOL_QUANTITY_PROFILE_REQUIRED')
            kwargs['instrument_profiles'] = {s:InstrumentProfile(quantity_step=profile[s]['quantity_step'],
                min_notional=profile[s]['min_notional']) for s in symbols}
        else:
            self.quantity_profile_binding = 'EXPLICIT_GENERATED_BOUNDARY_OVERRIDE'
        kwargs.setdefault('closing_min_notional_exempt', True)
        super().__init__(config, **kwargs)
        if self.config.initial_cash != D(10000):
            raise ValueError('ONE_SHARED_10000_WALLET_REQUIRED')

    @property
    def settlement_mode(self):
        return self._settlement_mode

    @property
    def policy_enabled(self):
        return self._policy_enabled

    @property
    def policy_variant(self):
        return self._policy_variant

    @property
    def topup_enabled(self):
        return self._topup_enabled

    def contract_metadata(self):
        result = super().contract_metadata()
        result.update(continuation_policy=POLICY_ID, generated_only=True,
            settlement_mode=self.settlement_mode, policy_enabled=self.policy_enabled, policy_variant=self.policy_variant, topup_enabled=self.topup_enabled,
            free_cash_floor='1000', total_isolated_ceiling='8500',
            trigger_scope='UNCHANGED_FIXED_005_EQUITY_MAINTENANCE_MODEL_NOT_BYBIT_LP',
            partial_liquidation='UNKNOWN_NOT_SIMULATED', quantity_profile_binding=self.quantity_profile_binding,
            native_liquidation_certified=False, historical_risk_tiers_certified=False,
            snapshot_recovery_certified=False, scheduler_integration_certified=False)
        return result

    def _risk(self, phase):
        # Permanent real debt is never erased, nor can any existing HALT rewind.
        if self.status in HALTS or not self.policy_enabled:
            return super()._risk(phase)
        if self.unpaid_liability:
            return super()._risk(phase)
        if self.settlement_mode == 'UNKNOWN_UNSETTLED':
            return super()._risk(phase)
        # This is a NEW, explicitly conditional account from inception. This
        # hook settles only native-triggered positions, before base whole-case
        # HALT assignment. There is intentionally no top-up in this hook.
        for symbol in self.symbols:
            p = self.positions[symbol]
            if not p.quantity:
                continue
            mark = self._mark(symbol)
            equity = p.isolated_balance + p.quantity * (mark-p.entry_price)
            mm = abs(p.quantity)*mark*self.config.maintenance_margin_rate
            if equity > mm:
                continue
            if not self._known_fresh(symbol, self.clock_us):
                return super()._risk(phase)
            before_nav, before_cash = self.nav(), self.free_cash
            tier = dict(riskLimitValue=None, maintenanceMargin='0.005',
                mmDeduction='0', initialMargin='1', maxLeverage='1', isLowestRisk=1)
            # Exact pinned method. Removes actual remaining collateral once.
            BybitIsolatedAccount._takeover(self, symbol, mark, phase, tier)
            # Explicitly identify discontinuity versus marked liquidation:
            # positive => conditional insurance/overshoot absorption; negative
            # => forfeited positive residual. Never ordinary trading alpha.
            adjustment = -equity
            assert self.free_cash == before_cash
            assert self.nav() - before_nav == adjustment
            support, forfeiture = max(ZERO, -equity), max(ZERO, equity)
            assert equity+support-forfeiture == 0
            self.settlement_journal.append(_numbers(dict(symbol=symbol,
                event_us=self.clock_us, phase=phase, pre_settlement_equity=equity,
                pre_settlement_maintenance=mm, conditional_NAV_adjustment=adjustment,
                conditional_overshoot_absorption=support,
                conditional_positive_residual_forfeited=forfeiture,
                marked_equity_before=equity,
                conditional_insurance_value_received=support,
                conditional_forfeiture_value_paid=forfeiture,
                settlement_value_cashflow=support-forfeiture,
                marked_equity_after=ZERO, value_ledger_error=equity+support-forfeiture,
                NAV_before=before_nav, NAV_after=self.nav(),
                value_cashflow_scope='EXPLICIT_CONDITIONAL_CLEARING_VALUE_NOT_OBSERVED_WALLET_CASH',
                free_cash_credit=ZERO, additional_liquidation_fee=ZERO,
                scope='CONDITIONAL_COLLATERAL_FORFEITURE_NOT_MARKET_FILL_OR_NATIVE_INSURANCE',
                partial_liquidation_known=False)))
            self.pending_exits.pop(symbol, None)
        return super()._risk(phase)

    def update_marks(self, observation_us, marks, *, quality=None):
        if quality is None:
            quality = dict.fromkeys(marks, 'DIRECT_GENERATED_OBSERVATION')
        if set(quality) != set(marks) or any(x not in {'DIRECT_GENERATED_OBSERVATION', 'UNKNOWN_OR_DERIVED'} for x in quality.values()):
            raise ValueError('EXPLICIT_MARK_QUALITY_REQUIRED')
        previous = dict(self.mark_quality)
        self.mark_quality.update(quality)
        try:
            return super().update_marks(observation_us, marks)
        except Exception:
            self.mark_quality = previous
            raise

    def _known_fresh(self, symbol, event_us):
        rows = self.marks[symbol]
        return bool(rows and self.mark_quality.get(symbol) == 'DIRECT_GENERATED_OBSERVATION'
                    and rows[-1]['available_us'] <= event_us
                    and 0 <= event_us-rows[-1]['close_us'] < MINUTE)

    def _begin(self, operation_id, identity):
        if type(operation_id) is not str or not operation_id:
            raise ValueError('OPERATION_ID_REQUIRED')
        key = _identity(identity)
        if operation_id in self.operation_ids:
            previous = self.operation_ids[operation_id]
            if previous['identity'] != key:
                raise ValueError('CONFLICTING_OPERATION_ID')
            return deepcopy(previous['receipt'])
        return None

    def _save(self, operation_id, identity, receipt):
        self.operation_ids[operation_id] = dict(identity=_identity(identity), receipt=deepcopy(receipt))
        return receipt

    def _transfer(self, symbol, amount, event_us, transfer_id):
        """Atomic internal transfer, only after known healthy native event."""
        self._symbol(symbol)
        p = self.positions[symbol]
        amount, event_us = decimal(amount), timestamp(event_us)
        if type(transfer_id) is not str or not transfer_id:
            raise ValueError('TRANSFER_ID_REQUIRED')
        identity = (symbol, str(amount), event_us)
        if transfer_id in self.transfer_ids:
            prior = self.transfer_ids[transfer_id]
            if prior['identity'] != identity:
                raise ValueError('CONFLICTING_TRANSFER_ID')
            return deepcopy(prior['receipt'])
        if event_us != self.clock_us:
            raise ValueError('TRANSFER_AT_CURRENT_NATIVE_CLOCK_ONLY')
        if (self.status in HALTS or self.unpaid_liability or amount <= 0
                or not p.quantity or not self._known_fresh(symbol, event_us)):
            raise ValueError('HEALTHY_FRESH_POSITION_REQUIRED_FOR_TRANSFER')
        mark = self._mark(symbol)
        equity = p.isolated_balance+p.quantity*(mark-p.entry_price)
        if equity <= abs(p.quantity)*mark*self.config.maintenance_margin_rate:
            raise ValueError('NO_RETROACTIVE_TOPUP')
        isolated = sum((x.isolated_balance for x in self.positions.values()), ZERO)
        if amount > max(ZERO, self.free_cash-D(1000)) or isolated+amount > D(8500):
            raise ValueError('TRANSFER_EXCEEDS_INTERNAL_BUDGET')
        before_nav, cash, margin = self.nav(), self.free_cash, p.isolated_balance
        before_totals = (self.fees, self.realized_PnL, self.funding_cash, self.execution_cost)
        # No callbacks or fallible external calls inside the commit.
        self.free_cash, p.isolated_balance = cash-amount, margin+amount
        assert self.nav() == before_nav
        assert (self.fees, self.realized_PnL, self.funding_cash, self.execution_cost) == before_totals
        row = _numbers(dict(id=transfer_id, symbol=symbol, event_us=event_us,
            amount=amount, free_cash_before=cash, free_cash_after=self.free_cash,
            isolated_before=margin, isolated_after=p.isolated_balance,
            NAV_before=before_nav, NAV_after=self.nav(), PnL=ZERO, fee=ZERO,
            quantity_before=p.quantity, quantity_after=p.quantity))
        self.transfer_journal.append(row)
        self.transfer_ids[transfer_id] = dict(identity=identity, receipt=deepcopy(row))
        return row

    def monitor(self, operation_id, event_us, *, headroom_features=None):
        """Call after all native marks and same-clock funding, before intents.

        Only fixed Guard50 is admitted. The prior headroom feature source is
        retained for review, not an optional outcome-dependent policy switch.
        """
        event_us = timestamp(event_us)
        if headroom_features is not None:
            raise ValueError('HEADROOM_TRIGGER_NOT_ADMITTED_FIXED_GUARD50_ONLY')
        identity = dict(kind='MONITOR', event_us=event_us, features=headroom_features)
        replay = self._begin(operation_id, identity)
        if replay is not None:
            return replay
        if event_us != self.clock_us:
            raise ValueError('MONITOR_MUST_FOLLOW_NATIVE_EVENT_AT_SAME_CLOCK')
        if not self.policy_enabled:
            return self._save(operation_id, identity, dict(status='DISABLED_BASELINE_UNCHANGED'))
        if self.status in HALTS:
            self.cash_watch_reason = ('UNPAID_DEBT' if self.unpaid_liability else 'UNRESOLVED_NATIVE_HALT')
            return self._save(operation_id, identity, dict(status=self.mode(event_us), reason=self.cash_watch_reason))
        actions, ranked = [], []
        for index, symbol in enumerate(self.symbols):
            p = self.positions[symbol]
            if not p.quantity:
                continue
            if not self._known_fresh(symbol, event_us):
                self.pending_exits.setdefault(symbol, dict(signal_us=event_us, reason='STALE_OR_UNKNOWN_MARK'))
                self.cash_watch_reason = 'STALE_OR_UNKNOWN_MARK'
                continue
            mark = self._mark(symbol)
            equity = p.isolated_balance+p.quantity*(mark-p.entry_price)
            mm = abs(p.quantity)*mark*self.config.maintenance_margin_rate
            wanted = max(ZERO, p.isolated_balance-equity) if equity <= p.isolated_balance/D(2) else ZERO
            reason = 'LEGACY50_RESTORE_PRETRANSFER_BALANCE'
            if wanted > 0 and self.topup_enabled:
                ranked.append((equity/mm, index, symbol, wanted, reason))
        with localcontext() as ctx:
            ctx.prec = 40
            for _, _, symbol, wanted, reason in sorted(ranked):
                isolated = sum((p.isolated_balance for p in self.positions.values()), ZERO)
                budget = max(ZERO, min(self.free_cash-D(1000), D(8500)-isolated))
                amount = min(wanted, budget)
                if amount > 0:
                    actions.append(self._transfer(symbol, amount, event_us, operation_id+':'+symbol))
                if amount < wanted:
                    self.pending_exits.setdefault(symbol, dict(signal_us=event_us, reason='INSUFFICIENT_TOPUP_BUDGET'))
                    self.cash_watch_reason = 'REDUCTION_REQUIRED'
                actions.append(dict(symbol=symbol, wanted=str(wanted), transferred=str(amount), reason=reason,
                    full_actual_position_exit_required=symbol in self.pending_exits))
        result = dict(status=self.mode(event_us), event_us=event_us, actions=actions,
                      pending_exits=deepcopy(self.pending_exits))
        self.monitor_journal.append(deepcopy(result))
        return self._save(operation_id, identity, result)

    def _floor(self, symbol, quantity):
        if self._exact_closing == (symbol, quantity):
            return quantity
        return super()._floor(symbol, quantity)

    def execute_fill(self, symbol, side, quantity, event_us, signal_us, fill_id, **kwargs):
        # Native known-ID semantics take precedence over new policy state.
        if fill_id in self.fill_requests:
            return super().execute_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
        if not self.policy_enabled:
            return super().execute_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
        p = self.positions[symbol]
        reducing = bool(p.quantity and (1 if side == 'BUY' else -1)*p.quantity < 0)
        if not kwargs.get('reduce_only', False):
            if symbol in self.blocked_signals and signal_us <= self.blocked_signals[symbol]:
                raise ValueError('FRESH_NORMAL_SIGNAL_REQUIRED_AFTER_LIQUIDATION')
            if self.pending_exits or not self.can_increase(event_us):
                raise ValueError('NEW_INCREASE_FAIL_CLOSED')
        if not kwargs.get('reduce_only', False):
            probe = self.fork_for_preview()
            USDTLinearPerpetualAccount.execute_fill(probe, symbol, side, quantity,
                event_us, signal_us, fill_id, **kwargs)
            if (probe.free_cash < D(1000) or sum((x.isolated_balance for x in probe.positions.values()), ZERO) > D(8500)
                    or probe.unpaid_liability or probe.status in HALTS
                    or len(probe.settlement_journal) != len(self.settlement_journal)):
                raise ValueError('CHARGED_POST_FILL_CAPITAL_GUARD_REJECTED')
        # Existing actual lots may be closed in full when actual capacity covers
        # them, even if a later assumed research lot table is coarser.
        available_input = kwargs.get('available_quantity')
        available = decimal(quantity if available_input is None else available_input)
        exact = abs(p.quantity) if (reducing and kwargs.get('reduce_only') is True
            and decimal(quantity) >= abs(p.quantity) and available >= abs(p.quantity)) else None
        self._exact_closing = (symbol, exact) if exact is not None else None
        try:
            return super().execute_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
        finally:
            self._exact_closing = None

    def attempt_reductions(self, operation_id, event_us, quotes):
        """Paid native reduce-only fills, only at real shared causal capacity.

        Caller must share this bucket with ALL other legs via consume_capacity.
        No same-open top-up can retroactively prevent a mark-triggered takeover.
        Full-close intent persists after partial capacity; reduction alone is
        never assumed to improve equity/value when it releases pro-rata margin.
        """
        event_us = timestamp(event_us)
        identity = dict(kind='REDUCE', event_us=event_us, quotes=quotes)
        replay = self._begin(operation_id, identity)
        if replay is not None:
            return replay
        self._clock(event_us)
        rows, prepared = [], []
        # Parse/validate every eligible quote before any financial mutation.
        for symbol in self.symbols:
            if symbol not in self.pending_exits or not self.positions[symbol].quantity:
                continue
            intent = self.pending_exits[symbol]
            earliest = ExecutionContractV2().earliest_execution_us(intent['signal_us'])+1
            if event_us < earliest:
                continue
            q = quotes.get(symbol)
            if not q:
                continue
            open_us = timestamp(q['open_us'])
            if (event_us != open_us+1 or open_us % MINUTE
                    or timestamp(q['quote_close_us']) != open_us
                    or timestamp(q['quote_available_us']) > open_us
                    or q.get('source_scope') != 'GENERATED_COMPLETED_PRIOR_MINUTE'):
                raise ValueError('EXACT_CAUSAL_OPEN_AND_PRIOR_COMPLETED_QUOTE_REQUIRED')
            key = (symbol, open_us)
            used = self.capacity_used.get(key, ZERO)
            raw, total = spend_capacity(abs(self.positions[symbol].quantity), q['quote_volume'], q['open_price'], used)
            if used > total:
                raise ValueError('REGISTERED_OTHER_LEGS_EXCEED_REAL_SHARED_CAPACITY')
            if operation_id+':'+symbol in self.fill_requests:
                raise ValueError('POLICY_FILL_ID_ALREADY_OWNED_REJECT_WHOLE_BATCH')
            prepared.append((symbol, intent, q, key, used, raw, total, earliest))
        self.clock_us = event_us
        for symbol, intent, q, key, used, raw, total, earliest in prepared:
            # Five actual eligible opens, as in the reused finite executor.
            # Expiry refresh is a new causal order; never fill an expired one.
            if event_us > earliest+4*MINUTE:
                intent['signal_us'] = event_us
                intent['renewals'] = intent.get('renewals', 0)+1
                continue
            receipt = self.execute_fill(symbol, 'SELL' if self.positions[symbol].quantity > 0 else 'BUY',
                str(abs(self.positions[symbol].quantity)), event_us, intent['signal_us'],
                operation_id+':'+symbol, execution_mid_price=q['open_price'],
                quote_available_us=q['quote_available_us'], available_quantity=str(raw), reduce_only=True)
            done = decimal(receipt['decimal_strings']['executed_quantity'])
            self.capacity_used[key] = used+done
            assert self.capacity_used[key] <= total
            rows.append(receipt)
            if not self.positions[symbol].quantity:
                self.pending_exits.pop(symbol, None)
            if self.status in HALTS:
                break
        return self._save(operation_id, identity, dict(fills=rows, mode=self.mode(event_us)))

    def consume_capacity(self, symbol, open_us, quantity, *, fill_id):
        """Integration seam: register actual fills by other scheduler legs."""
        self._symbol(symbol); timestamp(open_us)
        quantity = decimal(quantity)
        if quantity < 0:
            raise ValueError('NONNEGATIVE_ACTUAL_CAPACITY_USE_REQUIRED')
        if type(fill_id) is not str or not fill_id:
            raise ValueError('ACTUAL_FILL_ID_REQUIRED')
        identity = (symbol, open_us, quantity)
        if fill_id in self.capacity_registrations:
            if self.capacity_registrations[fill_id] != identity:
                raise ValueError('CONFLICTING_CAPACITY_FILL_ID')
            return
        key = (symbol, open_us)
        self.capacity_used[key] = self.capacity_used.get(key, ZERO)+quantity
        self.capacity_registrations[fill_id] = identity

    def request_terminal_exit(self, operation_id, event_us):
        timestamp(event_us)
        identity = dict(kind='TERMINAL', event_us=event_us)
        replay = self._begin(operation_id, identity)
        if replay is not None:
            return replay
        self._clock(event_us)
        if event_us != self.clock_us:
            raise ValueError('TERMINAL_INTENT_AT_CURRENT_NATIVE_CLOCK_ONLY')
        for symbol in self.symbols:
            if self.positions[symbol].quantity:
                self.pending_exits.setdefault(symbol, dict(signal_us=event_us, reason='TERMINAL_PAID_EXIT'))
        return self._save(operation_id, identity, dict(pending_exits=deepcopy(self.pending_exits)))

    def can_increase(self, event_us):
        return (self.status not in HALTS and self.nav() > 0 and not self.unpaid_liability
            and self.free_cash >= D(1000) and not self.pending_exits
            and sum((p.isolated_balance for p in self.positions.values()), ZERO) <= D(8500)
            and all(self._known_fresh(s, event_us) for s in self.symbols))

    def mode(self, event_us=None):
        event_us = self.clock_us if event_us is None else event_us
        if self.status in HALTS:
            if self.unpaid_liability:
                return 'DEBT_SETTLEMENT_BLOCKED'
            return 'INSOLVENT_HALT' if self.nav() <= 0 else 'CASH_WATCH_UNRESOLVED'
        if self.pending_exits:
            return 'REDUCE_ONLY_MONITOR'
        return 'CONTINUE_CONDITIONAL' if self.can_increase(event_us) else 'CASH_ONLY_MONITOR'

    def fork_for_preview(self):
        """In-memory owned fork only; no snapshot restore/restart claim.

        Immutable profiles may be shared. All wallet, transfer/idempotency,
        liquidation, pending and capacity state is deeply independent.
        External callbacks are suppressed in hypothetical branches.
        """
        clone = deepcopy(self, {id(self.instrument_profiles): self.instrument_profiles})
        clone.liquidation_callback = None
        return clone

    def snapshot(self):
        result = super().snapshot()
        result.update(continuation_policy=POLICY_ID, settlement_mode=self.settlement_mode,
            transfer_journal=deepcopy(self.transfer_journal), transfer_ids=deepcopy(self.transfer_ids),
            monitor_journal=deepcopy(self.monitor_journal),
            settlement_journal=deepcopy(self.settlement_journal),
            pending_exits=deepcopy(self.pending_exits), operation_ids=deepcopy(self.operation_ids),
            mark_quality=deepcopy(self.mark_quality), blocked_signals=deepcopy(self.blocked_signals),
            liquidations=deepcopy(self.liquidations), cash_watch_reason=self.cash_watch_reason,
            capacity_used={s+':'+str(t):str(v) for (s,t),v in self.capacity_used.items()},
            capacity_registrations={k:[s,t,str(v)] for k,(s,t,v) in self.capacity_registrations.items()},
            snapshot_recovery_certified=False)
        return result

    @classmethod
    def from_snapshot(cls, snapshot, **kwargs):
        raise NotImplementedError('CONTINUATION_SNAPSHOT_REPLAY_NOT_CERTIFIED_NO_HALT_RESET')

    def economic_report(self):
        result = self.summary()
        adjustment = sum((decimal(r['decimal_strings']['conditional_NAV_adjustment']) for r in self.settlement_journal), ZERO)
        result.update(policy_variant=self.policy_variant, continuation_mode=self.mode(),
            market_and_paid_cost_net_PnL_excluding_conditional_settlement_value=str(self.nav()-self.config.initial_cash-adjustment), transfers=deepcopy(self.transfer_journal),
            conditional_settlements=deepcopy(self.settlement_journal),
            conditional_NAV_adjustment_USDT=str(sum((decimal(r['decimal_strings']['conditional_NAV_adjustment'])
                for r in self.settlement_journal), ZERO)),
            paid_flat=(not any(p.quantity for p in self.positions.values()) and not self.unpaid_liability
                       and self.status not in HALTS and not self.settlement_journal),
            settled_flat_under_declared_model=(not any(p.quantity for p in self.positions.values())
                and not self.unpaid_liability and self.status not in HALTS),
            conditional_insurance_overshoot_absorption_USDT=str(sum((decimal(r['decimal_strings']['conditional_overshoot_absorption'])
                for r in self.settlement_journal), ZERO)),
            native_settlement_certified=False, historical_replays_run=0)
        return result
