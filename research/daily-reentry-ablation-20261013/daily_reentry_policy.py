"""Single-factor removal of the original guard's stopped-direction lock."""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal

from reentry_freeze import verify
verify()
from protective_policy import ProtectiveFullExitSimulator, sign
from quant.perpetual_account import ZERO
from scripts.investment.resumable_perpetual import NativeDailySimulator

POLICY_ID = 'isolated_half_equity_full_exit_fresh_daily_reentry_v1'

class FreshDailyReentrySimulator(ProtectiveFullExitSimulator):
    VERSION = 'native_half_equity_full_exit_fresh_daily_reentry_v1'

    def __init__(self, *args, **kwargs):
        verify()
        super().__init__(*args, **kwargs)
        self.reentry_events: list[dict] = []
        self.terminal_attempt_observations: dict[str, dict] = {}

    def schedule(self, target, signal, kind, only_symbols=None):
        symbols = self.symbols if only_symbols is None else tuple(only_symbols)
        for symbol in symbols:
            order_kind = kind[symbol] if isinstance(kind, dict) else kind
            # An ended/terminal/halted wallet cannot reopen even if schedule()
            # is called explicitly. Frozen terminal/reduction handling remains.
            if order_kind == 'DAILY_TARGET' and (
                    self.terminal or self.stop is not None or self.account.status != 'ACTIVE'):
                continue
            lock = self.protective_locks.get(symbol)
            if lock is not None and self.account.positions[symbol].quantity == ZERO:
                flat = lock['flat_us']
                if (order_kind != 'DAILY_TARGET' or flat is None
                        or int(signal) <= flat or self.account.status != 'ACTIVE'
                        or self.terminal or self.stop is not None):
                    continue
                desired = Decimal(str(target[symbol]))
                same = sign(desired) == lock['stopped_sign']
                self.reentry_events.append({
                    'kind': 'SAME_DIRECTION_REENTRY_ALLOWED' if same else 'FRESH_DAILY_RESET',
                    'symbol': symbol, 'event_us': int(signal), 'signal_us': int(signal),
                    'flat_us': flat, 'trigger_us': lock['trigger_us'],
                    'stopped_sign': lock['stopped_sign'], 'new_sign': sign(desired),
                    'target_quantity': str(desired), 'actual_quantity': '0',
                    'account_status': self.account.status})
                # Directly use the frozen generic schedule after consuming the
                # lock; no old target is cached or reused at a paid-flat fill.
                del self.protective_locks[symbol]
                NativeDailySimulator.schedule(self, target, signal, kind, only_symbols=(symbol,))
                continue
            # Live exposure, hard-cap priority, persistent reduce-only exit,
            # below-lot deferral, and all unaffected symbols follow old guard.
            super().schedule(target, signal, kind, only_symbols=(symbol,))

    def attempt(self, open_us, market_row):
        # Count the frozen scheduler's actual eligible attempts during global
        # terminal mode by kind. Do not call an ongoing protective attempt a
        # TERMINAL attempt, and do not count below-one-lot deferred minutes.
        tracked = list(self.pending.items()) if self.terminal else []
        before = {s: o['attempts'] for s, o in tracked}
        result = super().attempt(open_us, market_row)
        for symbol, order in tracked:
            increment = order['attempts'] - before[symbol]
            if increment:
                key = symbol + ':' + order['kind']
                row = self.terminal_attempt_observations.setdefault(key, {
                    'symbol': symbol, 'kind': order['kind'], 'actual_attempts': 0,
                    'first_attempt_us': int(open_us) + 1, 'last_attempt_us': int(open_us) + 1})
                row['actual_attempts'] += increment
                row['last_attempt_us'] = int(open_us) + 1
        return result

    def snapshot(self):
        image = super().snapshot()
        image['daily_reentry_policy'] = {'policy_id': POLICY_ID,
                                        'freeze_manifest_SHA256': verify()['freeze_manifest_SHA256']}
        image['state']['reentry_events'] = deepcopy(self.reentry_events)
        image['state']['terminal_attempt_observations'] = deepcopy(self.terminal_attempt_observations)
        return image

    @classmethod
    def from_snapshot(cls, snapshot, window, *, account_class):
        if snapshot.get('daily_reentry_policy') != {
                'policy_id': POLICY_ID, 'freeze_manifest_SHA256': verify()['freeze_manifest_SHA256']}:
            raise ValueError('Daily-reentry recovery identity differs')
        if not {'reentry_events', 'terminal_attempt_observations'} <= set(snapshot.get('state', {})):
            raise ValueError('Daily-reentry recovery journal missing')
        result = super().from_snapshot(snapshot, window, account_class=account_class)
        for event in result.reentry_events:
            if (event['symbol'] not in result.symbols or event['kind'] not in
                    ('SAME_DIRECTION_REENTRY_ALLOWED', 'FRESH_DAILY_RESET')
                    or not event['trigger_us'] <= event['flat_us'] < event['signal_us']
                    or event['event_us'] != event['signal_us']
                    or event['actual_quantity'] != '0' or event['account_status'] != 'ACTIVE'
                    or not event['signal_us'] <= result.account.clock_us
                    or event['stopped_sign'] not in (-1, 1)
                    or event['new_sign'] != sign(Decimal(event['target_quantity']))
                    or (event['kind'] == 'SAME_DIRECTION_REENTRY_ALLOWED') !=
                       (event['new_sign'] == event['stopped_sign'])):
                raise ValueError('Daily-reentry recovery event invalid')
        return result

    def result(self):
        result = super().result()
        result['daily_reentry_policy'] = {
            'policy_id': POLICY_ID, 'events': deepcopy(self.reentry_events),
            'terminal_attempt_observations': deepcopy(self.terminal_attempt_observations),
            'first_same_direction_signal_us': min((e['signal_us'] for e in self.reentry_events
                if e['kind'] == 'SAME_DIRECTION_REENTRY_ALLOWED'), default=None)}
        result['summary']['daily_reentry_policy_id'] = POLICY_ID
        return result
