"""Single fixed trigger replacement; the reviewed GUARD50 executor is reused."""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from quant.perpetual_account import HALTS, ZERO
from scripts.investment.perpetual_directional import MINUTE
from scripts.investment.resumable_perpetual import NativeDailySimulator
from protective_policy import ProtectiveFullExitSimulator, sign
from headroom_buffer import assess, VERSION as BUFFER_VERSION
from feature_tape import FeatureTape

HERE = Path(__file__).resolve().parent
POLICY_ID = 'causal_execution_headroom_full_exit_v1'


def metadata(window):
    tape = window.get('headroom_features')
    if not isinstance(tape, FeatureTape) or tuple(window['symbols']) != tape.symbols:
        raise ValueError('Exact symbol-ordered immutable feature tape required')
    return {'policy_id': POLICY_ID, 'buffer_id': BUFFER_VERSION,
            'feature_binding': deepcopy(tape.binding),
            'protocol_SHA256': hashlib.sha256((HERE/'PROTOCOL.json').read_bytes()).hexdigest(),
            'reused_execution': 'GUARD50_SCHEDULE_ATTEMPT_ADVANCE_DAY_UNCHANGED',
            'terminal_opens': 5, 'persist_cash_close': False, 'final_day_target_zero': False}


class HeadroomFullExitSimulator(ProtectiveFullExitSimulator):
    VERSION = 'native_daily_scheduler_with_causal_execution_headroom_full_exit_v1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.persist_cash_close or self.final_day_target_zero:
            raise ValueError('Original cash/terminal settings must stay false')
        metadata(self.window)
        self.headroom_coverage = {s: {'ready_invested_hook_evaluations': 0,
                                    'not_ready_invested_hook_evaluations': 0,
                                    'not_ready_reasons': {}} for s in self.symbols}

    def risk_schedule(self, stamp):
        # Copy only the reviewed causal clock gate. Every same-clock funding
        # event has completed, and the latest own mark must close exactly at t.
        same_clock_funding_left = (self.event_cursor < len(self.window['events'])
            and self.window['events'][self.event_cursor]['event_us'] == int(stamp))
        if self.account.status not in HALTS and int(stamp) % MINUTE == 0 and not same_clock_funding_left:
            for symbol in self.symbols:
                position = self.account.positions[symbol]
                if not position.quantity or symbol in self.protective_locks:
                    continue
                marks = self.account.marks[symbol]
                if not marks or marks[-1]['close_us'] != int(stamp):
                    continue
                mark = marks[-1]['price']
                balance = position.isolated_balance
                equity = balance + position.quantity * (mark-position.entry_price)
                ready, reason, feature = self.window['headroom_features'].at(symbol, stamp, mark)
                coverage = self.headroom_coverage[symbol]
                if not ready:
                    coverage['not_ready_invested_hook_evaluations'] += 1
                    coverage['not_ready_reasons'][reason] = coverage['not_ready_reasons'].get(reason, 0)+1
                    continue
                coverage['ready_invested_hook_evaluations'] += 1
                stress = assess(float(position.quantity), float(equity), float(mark), **feature)
                if not bool(stress['trigger']):
                    continue
                self.protective_locks[symbol] = {
                    'stopped_sign': sign(position.quantity), 'trigger_us': int(stamp),
                    'flat_us': None, 'deferred_no_lot_minutes': 0}
                self.protective_events.append({
                    'kind': 'FULL_EXIT_SIGNAL', 'symbol': symbol, 'event_us': int(stamp),
                    'quantity': str(position.quantity), 'mark': str(mark),
                    'isolated_balance': str(balance), 'isolated_equity': str(equity),
                    'stress_features': feature,
                    'stress_assessment': {k: float(v) for k, v in stress.items() if k != 'trigger'}})
                # Call the base scheduling method exactly as original GUARD50.
                NativeDailySimulator.schedule(self, {symbol: ZERO}, int(stamp),
                                              'PROTECTIVE_STOP', only_symbols=(symbol,))
        # Never call GUARD50.risk_schedule: that would add the old 50% trigger.
        NativeDailySimulator.risk_schedule(self, stamp)

    def snapshot(self):
        image = super().snapshot()
        image['protective_policy'] = metadata(self.window)
        image['state']['headroom_coverage'] = deepcopy(self.headroom_coverage)
        return image

    @classmethod
    def from_snapshot(cls, snapshot, window, *, account_class):
        if snapshot.get('protective_policy') != metadata(window):
            raise ValueError('Exact headroom feature/protocol recovery binding required')
        if not {'protective_locks', 'protective_events', 'headroom_coverage'} <= set(snapshot.get('state', {})):
            raise ValueError('Headroom protective recovery state missing')
        # Reuse the original guard's full lock/intent recovery validation.
        # Only its fixed metadata envelope is translated, never financial state.
        from protective_policy import POLICY_ID as OLD_ID, PROTOCOL_SHA256, TRIGGER_FRACTION
        image = deepcopy(snapshot)
        image['protective_policy'] = {'policy_id': OLD_ID,
            'protocol_sha256': PROTOCOL_SHA256, 'trigger_fraction': str(TRIGGER_FRACTION)}
        result = ProtectiveFullExitSimulator.from_snapshot.__func__(
            cls, image, window, account_class=account_class)
        if set(result.headroom_coverage) != set(result.symbols):
            raise ValueError('Coverage symbol recovery mismatch')
        for row in result.headroom_coverage.values():
            if set(row) != {'ready_invested_hook_evaluations', 'not_ready_invested_hook_evaluations', 'not_ready_reasons'}:
                raise ValueError('Coverage recovery schema mismatch')
            counts = [row['ready_invested_hook_evaluations'], row['not_ready_invested_hook_evaluations'],
                      *row['not_ready_reasons'].values()]
            if any(type(v) is not int or v < 0 for v in counts):
                raise ValueError('Coverage recovery count invalid')
        return result

    def result(self):
        case = super().result()
        case['protective_policy'] = {**metadata(self.window),
            'events': deepcopy(self.protective_events), 'open_locks': deepcopy(self.protective_locks),
            'coverage': deepcopy(self.headroom_coverage)}
        case['summary']['protective_policy_id'] = POLICY_ID
        return case
