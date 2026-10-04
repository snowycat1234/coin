"""Pinned Turtle hooks -> fill-driven research orders, never a financial ledger.

Completed 4h signals and observed completed-minute stops are COIN adaptations.
The supplied shared account alone owns fills, cash, funding, margin and NAV.
Callbacks commit once per logical tranche's first actual fill, not per capacity
fragment. This is not native Jesse/Bybit execution or intrabar-stop replication.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import sys
from copy import deepcopy
from decimal import localcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Union

import numpy as np
import polars as pl

from quant.execution_contract import ExecutionContractV2
from quant.paths import ROOT
from quant.perpetual_account import D, ZERO, HALTS, SYMBOLS, USDTLinearPerpetualAccount, decimal, timestamp
from scripts.investment import public_rsi2_indicator as installed
from scripts.investment import public_sma_perpetual as risk
from scripts.investment import perpetual_risk_reduction_research_v2 as reduction

VERSION = 'TURTLE_ORDERED_FILL_BRIDGE_V3_EXACT_CANDIDATE'
STRATEGY_ID = 'COIN_JESSE_TURTLE_S1_4H_USDT_PERPETUAL_ADAPTER'
BAR_US, MINUTE_US, DAY_US = 14_400_000_000, 60_000_000, 86_400_000_000
LOCKED_US = 1_772_323_200_000_000
VENDOR = ROOT / 'third_party/jesse_example_turtle_rules'
VENDOR_PINS = {
    'turtle_rules_original.py': '35e4c3cd69010ca81402277693cb6f7deaf52a284153f20f25d4cf605701408a',
    'atr_indicator_original.py': '398a12258dbc59b350c8c9ed8a1199a57cd89e7503c7dcd3fa002030c77df06c',
    'LICENSE': '80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d',
}
RULES = dict(timeframe_minutes=240, scalar_indicator_window=240, entry_period=20,
    exit_period=10, ATR_period=20, ATR_stop_multiplier=2, maximum_levels=4,
    pyramid_threshold_ATR=.5, system='S1_RAW_IMPLEMENTATION',
    channel_includes_current_completed_bar=True, high_low_equal_triggers=True,
    entry_long_and_exit_short_priority_on_both_sides=True,
    balance='SETTLED_FREE_PLUS_ISOLATED_MINUS_LIABILITY_EXCLUDES_UNREALIZED',
    callback_price='LATEST_COMPLETED_4H_CLOSE_NOT_FILL_OR_MARK',
    callback_scope='ONCE_PER_LOGICAL_ENTRY_ADD_FIRST_POSITIVE_FILL',
    residual_fragment_stop_quantity='ACTUAL_INVENTORY_NO_ADDITIONAL_LEVEL',
    zero_fill_expiry='ROLLBACK_INITIAL_GO_SIDE_EFFECTS',
    stop='COMPLETED_MINUTE_TRADE_RANGE_OBSERVATION_THEN_ORIGINAL_LATENCY',
    stop_active_scope='ARMED_BEFORE_MINUTE_OPEN_NO_INTRAMINUTE_PATH_INFERENCE',
    stop_fill='ACTUAL_ELIGIBLE_TRADE_OPEN_WITH_ORIGINAL_COST_NOT_STOP_PRICE',
    maximum_actual_attempts=5, sizing_buffer=.99, annual_vol_target=.10,
    asset_abs_cap=.3, gross_cap=.6, past_completed_daily_covariance=30,
    proposed_unit='RAW_ONE_PERCENT_SETTLED_WALLET_DIVIDED_BY_OFFICIAL_ATR',
    S1_filter_not_theoretical_complete=True, native_Jesse_execution=False,
    native_Bybit_execution=False, new_financial_ledger=False)
KINDS = ('ENTRY', 'ADD', 'EXIT', 'STOP', 'RISK_REDUCTION', 'TERMINAL')
REDUCING = ('EXIT', 'STOP', 'RISK_REDUCTION', 'TERMINAL')
PRIORITY = {'TERMINAL': 0, 'STOP': 1, 'EXIT': 2, 'RISK_REDUCTION': 3, 'ENTRY': 4, 'ADD': 5}
STATE_KEYS = ('current_pyramiding_levels', 'last_opened_price', 'last_was_profitable')


def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
        separators=(',', ':')).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class _StrategyAPI:
    """Only the upstream inherited no-op lifecycle signatures, no engine."""
    def __init__(self):
        self.vars = {}
        self.buy = self.sell = self.stop_loss = self.take_profit = None

    def on_open_position(self, order):
        pass

    def on_reduced_position(self, order):
        pass

    def on_close_position(self, order, closed_trade):
        pass


def official_context():
    require(set(VENDOR_PINS) == {'turtle_rules_original.py', 'atr_indicator_original.py', 'LICENSE'},
        'Official Turtle/ATR/license pins are not finalized')
    for name, sha in VENDOR_PINS.items():
        require(file_sha(VENDOR / name) == sha, 'Pinned official source changed: ' + name)
    # The prior supplementary runtime already binds Python/NumPy/wheel/binary.
    old_namespace, old_receipt = installed._context()
    package = sys.modules['jesse_rust']
    require(callable(getattr(package, 'atr', None)) and callable(getattr(package, 'atr_last', None)),
        'Official fixed runtime must expose ATR and scalar ATR kernels')
    indicator_path = ROOT / 'third_party/jesse_example_donchian/donchian_indicator_original.py'
    require(file_sha(indicator_path) == 'b7e96ebe3ba476c771a65b353c269a84d02e04587f0d76166c5f322bbbb3a401',
        'Unmodified official inclusive Donchian indicator')
    from collections import namedtuple
    namespace = dict(np=np, Union=Union, slice_candles=old_namespace['slice_candles'],
        rust_atr=package.atr, rust_atr_last=package.atr_last, rust_donchian=package.donchian,
        DonchianChannel=namedtuple('DonchianChannel', 'upperband middleband lowerband'))
    nodes = []
    for path, name in ((VENDOR / 'atr_indicator_original.py', 'atr'), (indicator_path, 'donchian')):
        chosen = [n for n in ast.parse(path.read_text()).body
                  if isinstance(n, ast.FunctionDef) and n.name == name and not n.decorator_list]
        require(len(chosen) == 1, 'One original undecorated official indicator')
        nodes += chosen
    tree = ast.Module(body=nodes, type_ignores=[])
    exec(compile(tree, str(VENDOR / 'atr_indicator_original.py'), 'exec'), namespace)
    namespace.update(Strategy=_StrategyAPI, utils=None)
    classes = [n for n in ast.parse((VENDOR / 'turtle_rules_original.py').read_text()).body
               if isinstance(n, ast.ClassDef) and n.name == 'TurtleRules']
    require(len(classes) == 1, 'One unmodified original TurtleRules class')
    original = ast.Module(body=classes, type_ignores=[])
    exec(compile(original, str(VENDOR / 'turtle_rules_original.py'), 'exec'), namespace)
    return namespace['TurtleRules'], dict(vendor_sha256=VENDOR_PINS,
        indicator_ast_sha256=hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest(),
        class_ast_sha256=hashlib.sha256(ast.dump(original, include_attributes=False).encode()).hexdigest(),
        supplementary_runtime=old_receipt, rules=RULES)


class TurtlePerpetualBridge:
    def __init__(self, account, *, allow_pyramiding=True, _restoring=False):
        require(isinstance(account, USDTLinearPerpetualAccount), 'Only the shared perpetual account')
        require(type(allow_pyramiding) is bool, 'Explicit Boolean proactive ADD permission')
        require(account.config.initial_cash == 10000 and account.config.max_asset_weight == D('.3')
            and account.config.max_gross_weight == D('.6'), 'Original independent10k account and caps')
        require(_restoring or not account.trades and all(p.quantity == 0 for p in account.positions.values()),
            'Fresh flat strategy; restore only with a bound account snapshot')
        cls, self.source_receipt = official_context()
        self.account = account
        self.symbols = risk.symbol_order(account.symbols)
        require(tuple(account.positions) == self.symbols, 'Ordered account inventory identity')
        self._allow_pyramiding = allow_pyramiding
        self.source_receipt = dict(self.source_receipt, configuration=self.configuration())
        self.rules = {s: cls() for s in self.symbols}
        self.contexts = {}
        self.intents = {}
        self.pending = {s: None for s in self.symbols}
        self.stops = {s: None for s in self.symbols}
        self.processed = {}
        self.callbacks = {}
        self.journal = []
        self.target_rows = []
        self.risk_receipts = []
        self.bar_receipts = {}
        self.sequence = 0
        self.clock_us = 0
        self.consumed_trade_rows = 0
        self.terminal = False
        self.halt_reason = None

    @property
    def allow_pyramiding(self):
        return self._allow_pyramiding

    def configuration(self):
        return dict(symbols=list(self.symbols), allow_pyramiding=self.allow_pyramiding,
            original_maximum_levels=4, maximum_accepted_levels=4 if self.allow_pyramiding else 1,
            disabled_scope='PROACTIVE_ADD_ONLY', covariance_column_order=list(self.symbols))

    def _clock(self, stamp):
        stamp = timestamp(stamp)
        require(stamp <= LOCKED_US and stamp >= self.clock_us, 'Chronological unlocked event or final logical close')
        self.clock_us = stamp
        return stamp

    def _state(self, symbol):
        obj = self.rules[symbol]
        return {k: deepcopy(getattr(obj, k)) for k in STATE_KEYS}

    def _state_set(self, symbol, state):
        require(set(state) == set(STATE_KEYS) and type(state['current_pyramiding_levels']) is int
            and 0 <= state['current_pyramiding_levels'] <= (4 if self.allow_pyramiding else 1)
            and type(state['last_was_profitable']) is bool
            and math.isfinite(state['last_opened_price']) and state['last_opened_price'] >= 0,
            'Valid original strategy state')
        for key, value in state.items():
            setattr(self.rules[symbol], key, deepcopy(value))

    def _sync(self, symbol):
        obj = self.rules[symbol]
        quantity = self.account.positions[symbol].quantity
        obj.position = SimpleNamespace(qty=float(quantity))
        obj.is_long, obj.is_short = quantity > 0, quantity < 0
        with localcontext() as ctx:
            ctx.prec = 40
            obj.balance = float(self.account.free_cash + sum((p.isolated_balance
                for p in self.account.positions.values()), ZERO) - self.account.unpaid_liability)
        require(math.isfinite(obj.balance), 'Known finite settled wallet, not NAV')
        if symbol in self.contexts:
            c = self.contexts[symbol]
            obj.candles = np.asarray(c['candles'], dtype=np.float64)
            obj.price, obj.high, obj.low = map(float, obj.candles[-1, [2, 3, 4]])
        return obj

    def _cancel(self, intent, reason):
        if not intent['active']:
            return
        intent['active'] = False
        intent['finished_reason'] = reason
        if self.pending[intent['symbol']] == intent['id']:
            self.pending[intent['symbol']] = None
        if intent['kind'] == 'ENTRY' and decimal(intent['filled_quantity']) == 0:
            self._state_set(intent['symbol'], intent['state_before'])
            self.journal.append(dict(event='ZERO_FILL_GO_ROLLBACK', intent_id=intent['id'], reason=reason))

    def _new(self, symbol, side, quantity, signal, kind, *, target=None, state_before=None,
             staged_state=None, proposed_stop=None, raw_quantity=None):
        require(symbol in self.symbols and kind in KINDS and side in ('BUY', 'SELL'), 'Known intent/product')
        quantity = decimal(quantity)
        require(quantity > 0, 'Positive gross research intent')
        if kind == 'ADD' and not self.allow_pyramiding:
            self.journal.append(dict(event='PROACTIVE_ADD_SUPPRESSED', symbol=symbol, side=side,
                signal_us=timestamp(signal), raw_quantity=str(quantity)))
            return None
        old_id = self.pending[symbol]
        if old_id:
            old = self.intents[old_id]
            if old['kind'] in REDUCING and PRIORITY[old['kind']] <= PRIORITY[kind]:
                self.journal.append(dict(event='PRIORITY_BLOCKED', symbol=symbol, kind=kind, prior=old_id))
                return None
            self._cancel(old, 'SUPERSEDED_BY_' + kind)
        self.sequence += 1
        identity = f'{symbol}:{kind}:{self.sequence}'
        intent = dict(id=identity, symbol=symbol, side=side, quantity=str(quantity),
            target_quantity=None if target is None else str(decimal(target)), signal_us=timestamp(signal),
            kind=kind, reduce_only=kind in REDUCING, attempts=0, active=True,
            filled_quantity='0', first_fill_us=None, callback_committed=False,
            fill_ids=[], attempt_ids=[], state_before=state_before, staged_state=staged_state,
            proposed_stop=None if proposed_stop is None else str(decimal(proposed_stop)),
            raw_quantity=None if raw_quantity is None else str(decimal(raw_quantity)))
        self.intents[identity] = intent
        self.pending[symbol] = identity
        self.journal.append(dict(event='INTENT_SUBMITTED', **deepcopy(intent)))
        return identity

    def on_bar_close(self, decision_us, candles_by_symbol, past30_returns, risk_last_close_us,
                     *, availability_us_by_symbol=None):
        """One completed4h decision, actual holdings; no warmup virtual position."""
        decision = timestamp(decision_us)
        require(decision % BAR_US == 0 and decision < LOCKED_US
            and set(candles_by_symbol) == set(self.symbols), 'All configured assets at a completed UTC4h close')
        require(timestamp(risk_last_close_us) == decision // DAY_US * DAY_US,
            'Risk returns end at the latest completed UTC day')
        contexts = {}
        for symbol in self.symbols:
            values = np.asarray(candles_by_symbol[symbol], dtype=np.float64)
            require(values.shape == (240, 6) and np.isfinite(values).all()
                and np.all(values[:, 0] == np.floor(values[:, 0]))
                and np.all(values[:, 0] >= 0) and np.all(values[:, 0] < LOCKED_US / 1000),
                'Exactly240 finite completed official-layout candles with integer milliseconds')
            opens = values[:, 0].astype(np.int64) * 1000
            require(np.array_equal(opens, np.arange(decision - 240 * BAR_US, decision, BAR_US))
                and np.all(values[:, 1:5] > 0) and np.all(values[:, 5] >= 0)
                and np.all(values[:, 4] <= np.minimum(values[:, 1], values[:, 2]))
                and np.all(values[:, 3] >= np.maximum(values[:, 1], values[:, 2])),
                'Complete coherent 4h warmup; missing days/bars never rolled away')
            if availability_us_by_symbol is None:
                available = opens + BAR_US
            else:
                require(set(availability_us_by_symbol) == set(self.symbols), 'All configured availability arrays')
                available = np.asarray(availability_us_by_symbol[symbol])
                require(available.shape == (240,) and available.dtype.kind in 'iu', 'Integer exact availability')
            require(np.all(available >= opens + BAR_US) and np.all(available <= decision),
                'All signal bars completed and available before decision')
            contexts[symbol] = dict(decision_us=decision, candles=values.tolist(),
                available_us=available.tolist(), availability_scope='CLOSED_BAR_PROXY_NOT_PUBLICATION_CERTIFIED')
        returns = np.asarray(past30_returns, dtype=np.float64)
        require(returns.shape == (30, len(self.symbols)) and np.isfinite(returns).all(),
            'Ordered configured assets, exactly30 past daily returns')
        identity = digest(dict(contexts=contexts, returns=returns.tolist(), risk_close=risk_last_close_us))
        if str(decision) in self.bar_receipts:
            require(self.bar_receipts[str(decision)]['input_hash'] == identity, 'Conflicting decision identity')
            return deepcopy(self.bar_receipts[str(decision)])
        self._clock(decision)
        require(not self.terminal and self.account.status not in HALTS, 'No new alpha after terminal/halt')
        self.contexts = contexts
        proposals = {}
        prices = {s: decimal(contexts[s]['candles'][-1][2]) for s in self.symbols}
        nav = self.account.nav()
        for symbol in self.symbols:
            obj = self._sync(symbol)
            obj.before()
            require(obj.balance > 0, 'No new strategy sizing with nonpositive settled wallet')
            require(obj.vars == dict(unit_risk_percent=1, entry_dc_period=20, exit_dc_period=10,
                atr_period=20, atr_multiplier=2, maximum_pyramiding_levels=4,
                pyramiding_threshold=.5, system_type='S1'), 'Unchanged raw Turtle fixed configuration')
            require(math.isfinite(float(obj.atr)) and obj.atr > 0, 'Finite positive official ATR, no zero kernel substitute')
            if self.pending[symbol]:
                continue
            before = self._state(symbol)
            obj.buy = obj.sell = None
            exited = [False]
            obj.liquidate = lambda flag=exited: flag.__setitem__(0, True)
            if self.account.positions[symbol].quantity:
                obj.update_position()
                if exited[0]:
                    self._state_set(symbol, before)
                    q = self.account.positions[symbol].quantity
                    self._new(symbol, 'SELL' if q > 0 else 'BUY', abs(q), decision, 'EXIT', target=0)
                    continue
                if not self.allow_pyramiding:
                    if obj.buy is not None or obj.sell is not None:
                        self.journal.append(dict(event='PROACTIVE_ADD_SUPPRESSED', symbol=symbol,
                            signal_us=decision, raw_order=list(obj.buy if obj.buy is not None else obj.sell)))
                    obj.buy = obj.sell = None
                    self._state_set(symbol, before)
                    continue
                kind = 'ADD'
            else:
                long, short = bool(obj.should_long()), bool(obj.should_short())
                require(not (long and short), 'Original Turtle must choose one direction')
                if not (long or short) or not all(f() for f in obj.filters()):
                    continue
                if long:
                    obj.go_long()
                else:
                    obj.go_short()
                kind = 'ENTRY'
            order = obj.buy if obj.buy is not None else obj.sell
            if order is not None:
                side = 'BUY' if obj.buy is not None else 'SELL'
                raw_quantity, price = map(decimal, order)
                require(raw_quantity > 0 and price == prices[symbol], 'Original positive unit at frozen signal close')
                stop = None if obj.stop_loss is None else decimal(obj.stop_loss[1])
                protection = prices[symbol] + (D(-2) if side == 'BUY' else D(2)) * decimal(float(obj.atr))
                require(protection > 0 and (stop is None or stop > 0), 'Positive raw protective stop before an actual order')
                proposals[symbol] = dict(kind=kind, side=side, raw_quantity=raw_quantity,
                    state_before=before, staged_state=self._state(symbol), proposed_stop=stop)
            self._state_set(symbol, before)
        raw = []
        candidates = {}
        for symbol in self.symbols:
            p = proposals.get(symbol)
            q = self.account.positions[symbol].quantity
            candidate = q + (p['raw_quantity'] if p['side'] == 'BUY' else -p['raw_quantity']) if p else q
            candidates[symbol] = candidate
            raw.append(float(candidate * prices[symbol] / nav))
        weights, details = risk.signed_risk_weights(raw, returns)
        submitted = []
        for symbol, weight, raw_weight in zip(self.symbols, weights, raw, strict=True):
            p = proposals.get(symbol)
            q = self.account.positions[symbol].quantity
            # Unchanged risk weights preserve exact inventory/candidate identity.
            bounded = (candidates[symbol] if float(weight) == raw_weight
                else decimal(float(weight)) * nav / prices[symbol])
            risk_reduced = abs(bounded) < abs(q) and q * bounded >= 0
            if risk_reduced and not self.pending[symbol]:
                target = bounded * D('.99')
                self._new(symbol, 'SELL' if q > 0 else 'BUY', abs(q-target), decision,
                    'RISK_REDUCTION', target=target)
            elif p:
                target = bounded * D('.99')
                direction = D(1) if p['side'] == 'BUY' else D(-1)
                allowed = min(p['raw_quantity'], max(ZERO, direction*(target-q)))
                if allowed > 0:
                    submitted.append(self._new(symbol, p['side'], allowed, decision, p['kind'],
                        state_before=p['state_before'], staged_state=p['staged_state'],
                        proposed_stop=p['proposed_stop'], raw_quantity=p['raw_quantity']))
                else:
                    self.journal.append(dict(event='RISK_CLIPPED_TO_ZERO', symbol=symbol, decision_us=decision))
            self.target_rows.append(dict(available_us=decision, symbol=symbol, target_weight=float(weight),
                raw_signed_target=raw_weight, mode='LONG_SHORT',
                proposed_ATR_quantity=None if not p else float(p['raw_quantity']),
                actual_quantity_at_decision=float(q), signal_price=float(prices[symbol])))
        receipt = dict(input_hash=identity, decision_us=decision, intents=[i for i in submitted if i],
            risk_last_close_us=risk_last_close_us, **details)
        self.risk_receipts.append(deepcopy(receipt))
        self.bar_receipts[str(decision)] = receipt
        return deepcopy(receipt)

    def force_targets(self, target_dict, signal_us, kind):
        signal = self._clock(signal_us)
        require(set(target_dict) == set(self.symbols) and kind in ('RISK_REDUCTION', 'TERMINAL'), 'Only original risk/terminal target dispatch')
        if kind == 'TERMINAL':
            self.terminal = True
            self.journal.append(dict(event='TERMINAL_STARTED', signal_us=signal))
        result = []
        for symbol in self.symbols:
            target, q = decimal(target_dict[symbol]), self.account.positions[symbol].quantity
            require(q*target >= 0 and abs(target) <= abs(q), 'Reduce-only force target cannot add or cross zero')
            if kind == 'TERMINAL':
                require(target == 0, 'Terminal cannot retain a speculative target')
                self.stops[symbol] = None
            if target != q:
                result.append(self._new(symbol, 'SELL' if q > 0 else 'BUY', abs(q-target), signal, kind, target=target))
            elif self.pending[symbol] and self.intents[self.pending[symbol]]['kind'] in ('ENTRY', 'ADD'):
                self._cancel(self.intents[self.pending[symbol]], 'CANCELLED_BY_' + kind)
        return [r for r in result if r]

    def observe_stop(self, close_us, minutes_by_symbol):
        """Known completed-minute ranges; never fill at a stop or invent path."""
        close = self._clock(close_us)
        require(close % MINUTE_US == 0 and set(minutes_by_symbol) == set(self.symbols), 'All configured complete UTC minute stop observations')
        triggered = []
        for symbol in self.symbols:
            bar = minutes_by_symbol[symbol]
            require(timestamp(bar['open_us']) + MINUTE_US == close
                and timestamp(bar['available_us']) == close, 'Exact completed-minute closure proxy')
            high, low = decimal(bar['high']), decimal(bar['low'])
            require(high >= low > 0, 'Coherent known trade range')
            stop = self.stops[symbol]
            if stop is None or self.terminal or not self.account.positions[symbol].quantity:
                continue
            known = stop if stop['armed_us'] <= bar['open_us'] else stop.get('previous')
            if known is None or known['armed_us'] > bar['open_us']:
                self.journal.append(dict(event='STOP_ARMED_WITHIN_OBSERVED_MINUTE_PATH_UNKNOWN', symbol=symbol, close_us=close))
                continue
            q = self.account.positions[symbol].quantity
            crossed = low <= decimal(known['price']) if q > 0 else high >= decimal(known['price'])
            if crossed and not stop['triggered']:
                stop.update(triggered=True, trigger_close_us=close, trigger_interval_open_us=bar['open_us'])
                identity = self._new(symbol, 'SELL' if q > 0 else 'BUY', abs(q), close, 'STOP', target=0)
                triggered.append(identity)
                self.journal.append(dict(event='OBSERVED_STOP_TRIGGER', symbol=symbol, close_us=close,
                    observed_stop_price=known['price'], interval_open_us=bar['open_us'], intent_id=identity))
        return [r for r in triggered if r]

    def due_orders(self, open_us, execution_mid_prices):
        open_us = timestamp(open_us)
        require(open_us % MINUTE_US == 0 and open_us < LOCKED_US and open_us + 1 >= self.clock_us
            and set(execution_mid_prices) == set(self.symbols), 'Actual causal unlocked minute execution opens for configured assets')
        require(self.halt_reason is None and self.account.status not in HALTS, 'No orders after real execution/account halt')
        event = open_us + 1
        orders = []
        for symbol in self.symbols:
            identity = self.pending[symbol]
            if not identity:
                continue
            intent = self.intents[identity]
            if event < ExecutionContractV2().earliest_execution_us(intent['signal_us']) + 1:
                continue
            q = self.account.positions[symbol].quantity
            if intent['kind'] in REDUCING:
                target = decimal(intent['target_quantity'])
                if reduction.risk_target_reached(target, q):
                    self._cancel(intent, 'TARGET_REACHED')
                    continue
                require(q*target >= 0 and abs(target) <= abs(q), 'Pending reduce target cannot reverse current inventory')
                if intent['kind'] == 'RISK_REDUCTION':
                    quantity = reduction.risk_reduction_request(q, target, execution_mid_prices[symbol],
                        dict(half_spread_bps=float(self.account.config.half_spread_bps),
                             slippage_bps=float(self.account.config.slippage_bps)))
                else:
                    quantity = abs(q)
            else:
                quantity = decimal(intent['quantity']) - decimal(intent['filled_quantity'])
            if quantity > 0:
                orders.append(dict(id=identity, symbol=symbol, side=intent['side'], quantity=quantity,
                    signal_us=intent['signal_us'], kind=intent['kind'], reduce_only=intent['reduce_only'],
                    attempts=intent['attempts']))
        return sorted(orders, key=lambda x: (PRIORITY[x['kind']], self.symbols.index(x['symbol'])))

    def _callback(self, name, intent, receipt, *, closed_trade=None):
        identity = intent['id'] + ':' + name
        require(identity not in self.callbacks, 'Lifecycle callback must be exactly once')
        obj = self._sync(intent['symbol'])
        order = SimpleNamespace(id=intent['id'], fill_id=receipt['fill_id'], kind=intent['kind'])
        if name == 'on_close_position':
            obj.on_close_position(order, closed_trade)
        else:
            getattr(obj, name)(order)
        witness = dict(event='CALLBACK', id=identity, name=name, intent_id=intent['id'],
            fill_id=receipt['fill_id'], context_close_us=self.contexts[intent['symbol']]['decision_us'],
            state_after=self._state(intent['symbol']))
        self.callbacks[identity] = witness
        self.journal.append(deepcopy(witness))

    def _protect(self, symbol, price, event_us):
        q = self.account.positions[symbol].quantity
        price = decimal(price)
        require(q and price > 0, 'Protect only actual inventory at positive original stop')
        previous = self.stops[symbol]
        self.stops[symbol] = dict(price=str(price), quantity=str(abs(q)), armed_us=event_us,
            context_close_us=self.contexts[symbol]['decision_us'], triggered=False,
            previous=None if previous is None else {k: v for k, v in previous.items() if k != 'previous'})

    def on_fill(self, intent_id, receipt):
        """Caller already executed through the original account; notify, no fill."""
        require(intent_id in self.intents and isinstance(receipt, dict), 'Known logical order and actual receipt')
        fill_id = receipt['fill_id']
        require(fill_id in self.account.fill_requests
            and self.account.fill_requests[fill_id]['receipt'] == receipt, 'Exact original account receipt, not fabricated trade')
        signature = digest(receipt)
        if fill_id in self.processed:
            require(self.processed[fill_id] == dict(intent_id=intent_id, receipt_hash=signature), 'Conflicting callback replay')
            return dict(replayed=True, fill_id=fill_id)
        intent = self.intents[intent_id]
        require(intent['active'], 'A cancelled order cannot receive an unregistered fill')
        identity = self.account.fill_requests[fill_id]['identity']
        require(identity['symbol'] == intent['symbol'] and identity['side'] == intent['side']
            and identity['signal_us'] == intent['signal_us'] and identity['reduce_only'] == intent['reduce_only'],
            'Actual order identity must match the pending strategy intent')
        event = self._clock(identity['event_us'])
        fills = receipt['fills']
        require(self.account.trades[self.consumed_trade_rows:] == fills, 'No orphan or reordered financial fills')
        self.consumed_trade_rows += len(fills)
        quantity = sum((decimal(r['decimal_strings']['quantity']) for r in fills), ZERO)
        intent['fill_ids'].append(fill_id)
        self.processed[fill_id] = dict(intent_id=intent_id, receipt_hash=signature)
        symbol = intent['symbol']
        if not quantity:
            return dict(replayed=False, filled_quantity='0', fill_id=fill_id)
        intent['filled_quantity'] = str(decimal(intent['filled_quantity']) + quantity)
        if intent['first_fill_us'] is None:
            intent['first_fill_us'] = event
        q = self.account.positions[symbol].quantity
        if intent['kind'] in ('ENTRY', 'ADD') and not intent['callback_committed']:
            if intent['kind'] == 'ENTRY':
                self._state_set(symbol, intent['staged_state'])
                self._callback('on_open_position', intent, receipt)
                price = intent['proposed_stop']
            else:
                self._callback('on_increased_position', intent, receipt)
                price = self.rules[symbol].stop_loss[1]
            intent['callback_committed'] = True
            self._protect(symbol, price, event)
        elif q and self.stops[symbol]:
            self.stops[symbol]['quantity'] = str(abs(q))
        if q and intent['kind'] in ('ENTRY', 'ADD') and self.stops[symbol]:
            stop = self.stops[symbol]
            mid = decimal(identity['execution_mid_price'])
            if not stop['triggered'] and (mid <= decimal(stop['price']) if q > 0 else mid >= decimal(stop['price'])):
                stop.update(triggered=True, trigger_close_us=event, trigger_interval_open_us=identity['quote_available_us'])
                gap_id = self._new(symbol, 'SELL' if q > 0 else 'BUY', abs(q), event, 'STOP', target=0)
                self.journal.append(dict(event='KNOWN_EXECUTION_OPEN_GAP_THROUGH_STOP', symbol=symbol,
                    event_us=event, observed_mid=str(mid), stop_price=stop['price'], intent_id=gap_id))
        if intent['kind'] in REDUCING:
            if q:
                # This no-op API callback is one logical reduction, not fragments.
                if intent['id'] + ':on_reduced_position' not in self.callbacks:
                    self._callback('on_reduced_position', intent, receipt)
            else:
                if intent['kind'] == 'STOP':
                    self._callback('on_stop_loss', intent, receipt)
                self._callback('on_close_position', intent, receipt,
                    closed_trade=SimpleNamespace(actual_quantity=0, cause=intent['kind']))
                self.rules[symbol].current_pyramiding_levels = 0
                self.stops[symbol] = None
        self.journal.append(dict(event='ACTUAL_FILL_NOTIFIED', intent_id=intent_id, fill_id=fill_id,
            filled_quantity=str(quantity), actual_quantity=str(q), callback_committed=intent['callback_committed']))
        return dict(replayed=False, filled_quantity=str(quantity), fill_id=fill_id)

    def note_attempt(self, intent_id, event_us, receipt):
        """One actual minute attempt, including reject; protective orders persist."""
        event = timestamp(event_us)
        intent = self.intents[intent_id]
        fill_id = receipt['fill_id']
        require(fill_id in self.processed and self.processed[fill_id]['intent_id'] == intent_id
            and event == self.account.fill_requests[fill_id]['identity']['event_us'], 'Notify the actual receipt before counting attempt')
        if fill_id in intent['attempt_ids']:
            return dict(replayed=True, halt_reason=self.halt_reason)
        intent['attempt_ids'].append(fill_id)
        intent['attempts'] += 1
        q = self.account.positions[intent['symbol']].quantity
        done = (reduction.risk_target_reached(decimal(intent['target_quantity']), q)
                if intent['kind'] in REDUCING else decimal(intent['filled_quantity']) >= decimal(intent['quantity']))
        if done:
            self._cancel(intent, 'FILLED_OR_REDUCTION_TARGET_REACHED')
        elif intent['attempts'] >= 5:
            if intent['kind'] in REDUCING:
                self.halt_reason = 'NOT_EVALUABLE_UNEXECUTABLE_' + intent['kind']
                # No cancellation, reset or free flat: retain exact residual.
                self.journal.append(dict(event='PROTECTIVE_EXECUTION_BUDGET_EXHAUSTED', intent_id=intent_id,
                    actual_quantity=str(q), halt_reason=self.halt_reason, event_us=event))
            else:
                self._cancel(intent, 'FIVE_ACTUAL_ATTEMPTS_EXPIRED')
        return dict(replayed=False, completed=not intent['active'], halt_reason=self.halt_reason)

    def summary_orders(self):
        return {s: None if self.pending[s] is None else deepcopy(self.intents[self.pending[s]]) for s in self.symbols}

    def targets_frame(self):
        schema = dict(available_us=pl.Int64, symbol=pl.String, target_weight=pl.Float64,
            raw_signed_target=pl.Float64, mode=pl.String, proposed_ATR_quantity=pl.Float64,
            actual_quantity_at_decision=pl.Float64, signal_price=pl.Float64)
        return pl.DataFrame(self.target_rows, schema=schema) if self.target_rows else pl.DataFrame(schema=schema)

    def meta(self):
        return dict(strategy_id=STRATEGY_ID, rules=RULES, source=self.source_receipt,
            configuration=self.configuration(), symbols=list(self.symbols), allow_pyramiding=self.allow_pyramiding,
            decision_receipts=self.risk_receipts, callbacks=list(self.callbacks.values()),
            journal=deepcopy(self.journal), pending=self.summary_orders(), stops=deepcopy(self.stops),
            halt_reason=self.halt_reason, candidate='NO_QUALIFIED_CANDIDATE', long_term_APR='NOT_EVALUABLE')

    def snapshot(self):
        return dict(version=VERSION, rules=RULES, source_receipt=self.source_receipt,
            configuration=self.configuration(), symbols=list(self.symbols), allow_pyramiding=self.allow_pyramiding,
            account_snapshot_sha256=digest(self.account.snapshot()),
            strategy_state={s: self._state(s) for s in self.symbols}, contexts=deepcopy(self.contexts),
            intents=deepcopy(self.intents), pending=deepcopy(self.pending), stops=deepcopy(self.stops),
            processed=deepcopy(self.processed), callbacks=deepcopy(self.callbacks),
            journal=deepcopy(self.journal), target_rows=deepcopy(self.target_rows),
            risk_receipts=deepcopy(self.risk_receipts), bar_receipts=deepcopy(self.bar_receipts),
            sequence=self.sequence, clock_us=self.clock_us, consumed_trade_rows=self.consumed_trade_rows,
            terminal=self.terminal, halt_reason=self.halt_reason)

    @classmethod
    def from_snapshot(cls, account, snapshot, *, allow_pyramiding=True):
        require(snapshot['version'] == VERSION and snapshot['rules'] == RULES
            and type(allow_pyramiding) is bool and snapshot['allow_pyramiding'] is allow_pyramiding
            and snapshot['symbols'] == list(account.symbols)
            and snapshot['account_snapshot_sha256'] == digest(account.snapshot()), 'Exact bridge/account snapshot binding')
        obj = cls(account, allow_pyramiding=allow_pyramiding, _restoring=True)
        require(snapshot['configuration'] == obj.configuration(), 'Exact ordered symbols and proactive ADD permission')
        require(snapshot['source_receipt'] == obj.source_receipt, 'No source/runtime change during recovery')
        for key in ('contexts', 'intents', 'pending', 'stops', 'processed', 'callbacks', 'journal',
                    'target_rows', 'risk_receipts', 'bar_receipts', 'sequence', 'clock_us',
                    'consumed_trade_rows', 'terminal', 'halt_reason'):
            setattr(obj, key, deepcopy(snapshot[key]))
        timestamp(obj.clock_us)
        context_clock = max((r['decision_us'] for r in obj.contexts.values()), default=0)
        require(obj.clock_us <= max(account.clock_us, context_clock)
            and obj.consumed_trade_rows == len(account.trades)
            and set(obj.pending) == set(obj.symbols) and set(obj.stops) == set(obj.symbols)
            and set(snapshot['strategy_state']) == set(obj.symbols)
            and set(obj.contexts) <= set(obj.symbols)
            and type(obj.sequence) is int and obj.sequence >= 0 and type(obj.terminal) is bool,
            'No future, orphan financial rows or malformed bridge snapshot')
        require(obj.terminal == any(r.get('event') == 'TERMINAL_STARTED' for r in obj.journal),
            'Terminal state must be an actual declared lifecycle event')
        for symbol, identity in obj.pending.items():
            require(identity is None or identity in obj.intents and obj.intents[identity]['symbol'] == symbol
                and obj.intents[identity]['active'], 'Pending pointer must identify its owned active logical order')
        seen_fills = []
        for identity, intent in obj.intents.items():
            require(identity == intent['id'] and intent['symbol'] in obj.symbols and intent['kind'] in KINDS
                and (obj.allow_pyramiding or intent['kind'] != 'ADD')
                and intent['side'] in ('BUY', 'SELL') and type(intent['active']) is bool
                and intent['reduce_only'] == (intent['kind'] in REDUCING)
                and intent['attempts'] == len(set(intent['attempt_ids']))
                and set(intent['attempt_ids']) <= set(intent['fill_ids']), 'Bound logical intent identity/attempts')
            actual_filled = ZERO
            for fill_id in intent['fill_ids']:
                require(fill_id in obj.processed and fill_id in account.fill_requests
                    and obj.processed[fill_id] == dict(intent_id=identity,
                        receipt_hash=digest(account.fill_requests[fill_id]['receipt'])), 'Bound actual receipt deduplication')
                actual_filled += sum((decimal(r['decimal_strings']['quantity'])
                    for r in account.fill_requests[fill_id]['receipt']['fills']), ZERO)
                seen_fills.append(fill_id)
            require(actual_filled == decimal(intent['filled_quantity']), 'Logical tranche actual quantity bridge')
            if intent['kind'] in ('ENTRY', 'ADD'):
                callback = 'on_open_position' if intent['kind'] == 'ENTRY' else 'on_increased_position'
                require(intent['callback_committed'] == (actual_filled > 0)
                    and (identity + ':' + callback in obj.callbacks) == (actual_filled > 0), 'First-positive callback exactly once')
            require(intent['active'] == (obj.pending[intent['symbol']] == identity), 'No orphan active pending order')
        require(len(seen_fills) == len(set(seen_fills)) and set(seen_fills) == set(obj.processed)
            and set(obj.processed) == set(account.fill_requests), 'All actual order requests belong to the restored bridge')
        for symbol in obj.symbols:
            obj._state_set(symbol, snapshot['strategy_state'][symbol])
            stop, q = obj.stops[symbol], account.positions[symbol].quantity
            if q and not obj.terminal:
                require(stop is not None and decimal(stop['quantity']) == abs(q)
                    and decimal(stop['price']) > 0 and timestamp(stop['armed_us']) <= obj.clock_us,
                    'Every restored owned position retains its actual-quantity protective stop')
            if not q:
                require(stop is None, 'Flat account cannot retain orphan protective inventory')
            if symbol in obj.contexts:
                require(obj.contexts[symbol]['decision_us'] <= obj.clock_us, 'No future context during restore')
                obj._sync(symbol)
        for identity, witness in obj.callbacks.items():
            require(identity == witness['id'] and witness['intent_id'] in obj.intents
                and witness['fill_id'] in obj.processed
                and obj.processed[witness['fill_id']]['intent_id'] == witness['intent_id']
                and identity == witness['intent_id'] + ':' + witness['name'],
                'Callback belongs to actual fill and logical order')
        return obj
