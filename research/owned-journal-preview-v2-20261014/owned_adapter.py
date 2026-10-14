"""Separate generated owned-journal adapter, with auditable narrow source delta.

The two inherited adapter hooks are preserved from frozen v4 except dependency
names and account snapshot comparisons replaced with exact owned-state tokens.
No financial or risk branch is rewritten. test_source_delta verifies this AST.
"""
from copy import deepcopy
from decimal import Decimal as D
from types import MethodType
from causal_adapter import CausalPartialAdapter, _stamp, S, ExecutionContractV2
from owned_preview import BoundedChargedPreview, BoundedFreshExecutionPreview

class OwnedCausalPartialAdapter(CausalPartialAdapter):

    def _signal_preview(self, signal_us):
        sim = self.simulator
        binding = self.source.bind(signal_us)
        if sim.previous_quote is None:
            raise ValueError('PAST_SIGNAL_CAPACITY_REQUIRED')
        for s in S:
            if not sim.account.marks[s] or any((row['available_us'] > signal_us or row['close_us'] > signal_us for row in sim.account.marks[s])):
                raise ValueError('SIGNAL_ACCOUNT_STATE_MUST_BE_CAUSAL')
        oracle = BoundedChargedPreview(sim.account, prices=dict(zip(S, binding.prices)), covariance=binding.covariance, pending=self._pending(), previous_quote=sim.previous_quote, event_us=ExecutionContractV2().earliest_execution_us(signal_us) + 1, signal_us=signal_us, covariance_available_us=binding.covariance_available_us, quote_available_us=signal_us, price_available_us=dict(zip(S, binding.price_available_us)))
        self.bindings[signal_us] = binding
        return oracle

    def attempt(self, open_us, market_row):
        sim, account = (self.simulator, self.simulator.account)
        event = _stamp(open_us) + 1
        prices = {s: D(str(market_row[s]['open'])) for s in S if s in market_row}
        capacity = {s: D(str(sim.previous_quote[s])) * D('.001') / prices[s] if sim.previous_quote is not None and s in prices else D(0) for s in S}
        raw_fill = account.execute_fill
        had_instance_method = 'execute_fill' in vars(account)
        previous_instance_method = vars(account).get('execute_fill')

        def guarded(_account, symbol, side, quantity, event_us, signal_us, fill_id, **kwargs):
            quantity = D(str(quantity))
            native_planned = account._floor(symbol, min(quantity, D(str(kwargs['available_quantity']))))
            if not kwargs.get('reduce_only', False) and native_planned > 0:
                before = account.preview_state_token()
                pending_before = deepcopy(sim.pending)
                try:
                    if event_us != event or set(prices) != set(S):
                        raise ValueError('COMPLETE_CURRENT_NATIVE_OPEN_VECTOR_REQUIRED')
                    if D(str(kwargs['execution_mid_price'])) != prices[symbol]:
                        raise ValueError('NATIVE_FILL_MIDPOINT_MUST_MATCH_CURRENT_OPEN')
                    binding = self.bindings.get(signal_us)
                    if binding is None:
                        raise ValueError('MISSING_SOURCE_BOUND_ORDER_SIGNAL')
                    live_capacity = dict(capacity)
                    live_capacity[symbol] = D(str(kwargs['available_quantity']))
                    preview = BoundedFreshExecutionPreview(account, binding=binding, prices=prices, price_available_us=dict.fromkeys(S, open_us), pending=self._pending(), capacity=live_capacity, event_us=event_us, signal_us=signal_us, quote_available_us=kwargs['quote_available_us'])
                    witness = preview.evaluate(self._pending(), D(1))
                    witness.update(source_sha256=binding.source_sha256, event_us=event_us, signal_us=signal_us, fresh_native_NAV=str(account.nav()), fresh_free_cash=str(account.free_cash), fresh_funding_cash=str(account.funding_cash), fresh_pending={s: str(q) for s, q in self._pending().items()}, current_available_opens={s: str(p) for s, p in prices.items()})
                except Exception as exc:
                    witness = {'allowed': False, 'reason': 'FRESH_GUARD_EXCEPTION:' + type(exc).__name__, 'detail': str(exc), 'event_us': event_us, 'signal_us': signal_us}
                if account.preview_state_token() != before or sim.pending != pending_before:
                    raise AssertionError('GUARD_CHANGED_LIVE_ACCOUNT_OR_PENDING')
                self.execution_receipts.append({'symbol': symbol, 'fill_id': fill_id, **witness})
                if not witness['allowed']:
                    return self._rejected(symbol, quantity, fill_id, 'FRESH_EXECUTION_RISK_GUARD', witness)
            before_trades = len(account.trades)
            receipt = raw_fill(symbol, side, quantity, event_us, signal_us, fill_id, **kwargs)
            used = sum((D(r['decimal_strings']['quantity']) for r in account.trades[before_trades:] if not r.get('liquidation_takeover')), D(0))
            capacity[symbol] = max(D(0), capacity[symbol] - used)
            return receipt
        account.execute_fill = MethodType(guarded, account)
        try:
            return self.original_attempt(open_us, market_row)
        finally:
            if had_instance_method:
                account.execute_fill = previous_instance_method
            else:
                del account.execute_fill
