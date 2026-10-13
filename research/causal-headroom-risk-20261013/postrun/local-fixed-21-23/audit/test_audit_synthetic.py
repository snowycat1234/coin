"""Synthetic observer tests only. No historical account or source is opened."""
from copy import deepcopy
from decimal import Decimal as D, localcontext
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import sys

import cold_audit as audit
sys.path.insert(0, str(audit.MODULE))


def economic_fixture():
    exact = {'quantity': '1', 'mid_price': '100', 'fill_price': '100.08',
             'fee_amount': '0.055044', 'execution_cost': '.08', 'realized_PnL': '0',
             'margin_allocated': '100.08', 'position_delta': '1'}
    trade = {'symbol': 'A', 'side': 'BUY', 'leg': 'OPEN', 'event_us': 60_000_001, 'decimal_strings': exact}
    account = SimpleNamespace(fees=D('.055044'), execution_cost=D('.08'), realized_PnL=D(0),
        funding_cash=D(0), gross_fill_turnover=D('100.08'), free_cash=D('9899.864956'),
        unpaid_liability=D(0), positions={'A': SimpleNamespace(quantity=D(1), entry_price=D('100.08'), isolated_balance=D('100.08'))},
        marks={'A': [{'price': D(100)}]}, nav=lambda: D('9999.864956'))
    return account, {'trades': [trade], 'funding': []}, {'symbols': ['A'], 'events': []}


class ObserverTests(unittest.TestCase):
    def test_economic_bridges_use_signed_inventory(self):
        account, output, source = economic_fixture()
        proof = audit.ledger_proof(account, output, source)
        self.assertEqual(proof['capital_bridge_error_USDT'], '0.000000')
        self.assertEqual(proof['live_economic_NAV_USDT'], '9999.864956')

    def test_per_leg_changed_fee_rejected(self):
        account, output, source = economic_fixture()
        output['trades'][0]['decimal_strings']['fee_amount'] = '.05'
        with self.assertRaisesRegex(ValueError, 'per-leg 5.5bp fee'):
            audit.ledger_proof(account, output, source)

    def test_collateral_omission_rejected(self):
        account, output, source = economic_fixture()
        account.positions['A'].isolated_balance = D(0)
        with self.assertRaisesRegex(ValueError, 'capital'):
            audit.ledger_proof(account, output, source)

    def test_funding_ownership_spoof_rejected(self):
        account, output, source = economic_fixture()
        raw = {'symbol': 'A', 'event_us': 120_000_000, 'raw_rate': .001}
        output['funding'] = [{**raw, 'quantity': 0, 'owned': False, 'mark_price': 100,
            'mark_close_us': 60_000_000, 'signed_funding_USDT': 0, 'conditional_rate_scale': 1.0,
            'assumed_fraction_decimal': '.001', 'decimal_strings': {'quantity': '0', 'signed_funding_USDT': '0', 'mark_price': '100'}}]
        source['events'] = [raw]
        with self.assertRaisesRegex(ValueError, 'pre-funding signed inventory'):
            audit.ledger_proof(account, output, source)

    def test_forbidden_transitions_and_restoration(self):
        class Sim:
            def advance_day(self): return 'original'
        class Account:
            def apply_funding(self): return 'original'
        with audit.forbid_transitions(Sim, Account):
            with self.assertRaises(RuntimeError): Sim().advance_day()
            with self.assertRaises(RuntimeError): Account().apply_funding()
            with self.assertRaises(RuntimeError): Sim().schedule()
        self.assertEqual(Sim().advance_day(), 'original')
        self.assertEqual(Account().apply_funding(), 'original')
        self.assertNotIn('schedule', Sim.__dict__)

    def test_prefix_signed_zero_mismatch_rejected(self):
        import numpy as np
        class Minute:
            def __init__(self, a): self.a = a; self.height = len(a)
            def drop(self, name): return self
            def to_numpy(self): return self.a
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root/'recovery').mkdir()
            old = np.zeros((2, 36), np.float64); old[:, 0] = 10000.
            chunk = root/'recovery/DAY_0000.npz'
            np.savez_compressed(chunk, minute_chunk=old)
            pointer = {'completed_minutes': 2, 'chunks': [{'path': chunk.name, 'SHA256': audit.sha(chunk), 'rows': 2, 'columns': 36}]}
            (root/'ACCOUNT.json').write_text('{"trades": [], "funding": [], "summary": {"gross_PnL_same_quantities": 0, "gross_fill_turnover_USDT": 0, "fees_USDT": 0, "execution_cost_USDT": 0, "funding_USDT": 0}}')
            new = old.copy(); new[0, 1] = -0.0
            output = {'minute': Minute(new), 'trades': [], 'funding': [], 'protective_policy': {'events': []}}
            with self.assertRaisesRegex(ValueError, 'minute prefix bits'):
                audit.prefix_proof(output, {'calendar': [0, 120_000_000]}, root, pointer)
            output['minute'] = Minute(old.copy())
            proof = audit.prefix_proof(output, {'calendar': [0, 120_000_000]}, root, pointer)
            self.assertEqual(proof['minute_rows'], 2)
            self.assertFalse(proof['new_metadata_or_full_snapshot_identity_claimed'])

    def test_protective_signal_requires_real_own_quantity(self):
        import numpy as np
        from headroom_buffer import assess
        class Minute:
            def __init__(self, a): self.a = a
            def drop(self, name): return self
            def to_numpy(self): return self.a
        feature = dict(a_down=0., a_up=0., g_down=0., g_up=0.)
        stress = assess(1., .5, 100., **feature)
        numeric = np.zeros((2, 36), np.float64)
        numeric[1, [9, 14, 19, 24]] = [1., 100., .5, .5]
        event = {'kind': 'FULL_EXIT_SIGNAL', 'symbol': 'A', 'event_us': 120_000_000,
                 'quantity': '1', 'isolated_equity': '.5', 'isolated_balance': '.5', 'mark': '100',
                 'stress_features': feature, 'stress_assessment': {k: float(v) for k, v in stress.items() if k != 'trigger'}}
        output = {'minute': Minute(numeric), 'trades': [{'symbol': 'A', 'event_us': 60_000_001,
            'decimal_strings': {'position_delta': '1', 'entry_price_after': '100'}}],
            'protective_policy': {'events': [event], 'open_locks': {'A': {'stopped_sign': 1, 'trigger_us': 120_000_000, 'flat_us': None}}}}
        source = {'start': 0, 'symbols': ['A'], 'headroom_features': SimpleNamespace(at=lambda *a: (True, 'READY', feature))}
        self.assertEqual(audit.signal_and_lock_proof(output, source)['signals_recomputed'], 1)
        noninteger_entry = '100.00000000000000000000000000123456789'
        output['trades'][0]['decimal_strings']['entry_price_after'] = noninteger_entry
        with localcontext() as context:
            context.prec = 28
            hook_equity = D('.5')+D(1)*(D(100)-D(noninteger_entry))
        event['isolated_equity'] = str(hook_equity)
        self.assertEqual(audit.signal_and_lock_proof(output, source)['signals_recomputed'], 1)
        with localcontext() as context:
            context.prec = 40
            event['isolated_equity'] = str(D('.5')+D(1)*(D(100)-D(noninteger_entry)))
        with self.assertRaisesRegex(ValueError, 'exact own equity'):
            audit.signal_and_lock_proof(output, source)
        event['isolated_equity'] = str(hook_equity)
        event['quantity'] = '2'
        with self.assertRaisesRegex(ValueError, 'own journal quantity'):
            audit.signal_and_lock_proof(output, source)

    def test_real_shared_capacity_and_five_terminal_opens(self):
        class Points:
            def __init__(self, root): pass
            def at(self, symbol, stamp, field): return D(100) if field == 'open' else D(100000)
        original = audit.SourcePoints; audit.SourcePoints = Points
        try:
            source = {'start': 0, 'end': 600_000_000}
            signal = source['end']-6*audit.MINUTE
            identity = {'symbol': 'A', 'event_us': signal+audit.MINUTE+1, 'signal_us': signal,
                        'quote_available_us': signal+audit.MINUTE, 'execution_mid_price': '100',
                        'available_quantity': '1', 'reduce_only': True}
            receipt = {'fill_id': 'x:0:REDUCE', 'fills': [{'decimal_strings': {'quantity': '.4'}}]}
            second = deepcopy(identity); second['available_quantity'] = '.6'; second['reduce_only'] = False; second['signal_us'] = 0
            snapshot = {'account': {'fill_requests': {'a': {'identity': identity, 'receipt': receipt},
                'b': {'identity': second, 'receipt': {'fill_id': 'y:0:INCREASE', 'fills': [{'decimal_strings': {'quantity': '.5'}}]}}}}}
            output = {'protective_policy': {'events': []}}
            proof = audit.execution_proof(snapshot, output, source, Path('.'))
            self.assertEqual(proof['all_actual_fill_requests_verified'], 2)
            self.assertEqual(proof['terminal_reduce_requests_verified'], 1)
            second['signal_us'] = signal; second['reduce_only'] = True
            with self.assertRaisesRegex(ValueError, 'one terminal reduce'):
                audit.execution_proof(snapshot, output, source, Path('.'))
            second['signal_us'] = 0; second['reduce_only'] = False
            second['signal_us'] = second['event_us']-1
            with self.assertRaisesRegex(ValueError, 'earliest_execution'):
                audit.execution_proof(snapshot, output, source, Path('.'))
            second['signal_us'] = 0
            second['available_quantity'] = '1'
            with self.assertRaisesRegex(ValueError, 'shared .001'):
                audit.execution_proof(snapshot, output, source, Path('.'))
            del snapshot['account']['fill_requests']['b']
            identity['event_us'] = signal+6*audit.MINUTE+1
            identity['quote_available_us'] = identity['event_us']-1
            with self.assertRaisesRegex(ValueError, 'calendar open'):
                audit.execution_proof(snapshot, output, source, Path('.'))
        finally:
            audit.SourcePoints = original


if __name__ == '__main__':
    unittest.main()
