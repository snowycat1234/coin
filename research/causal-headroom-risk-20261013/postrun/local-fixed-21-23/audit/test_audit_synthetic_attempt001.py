"""Synthetic observer tests only. No historical account or source is opened."""
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import cold_audit as audit


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
            old = np.zeros((2, 36), np.float64)
            chunk = root/'recovery/DAY_0000.npz'
            np.savez_compressed(chunk, minute_chunk=old)
            pointer = {'completed_minutes': 2, 'chunks': [{'path': chunk.name, 'SHA256': audit.sha(chunk), 'rows': 2, 'columns': 36}]}
            (root/'ACCOUNT.json').write_text('{"trades": [], "funding": []}')
            new = old.copy(); new[0, 0] = -0.0
            output = {'minute': Minute(new), 'trades': [], 'funding': [], 'protective_policy': {'events': []}}
            with self.assertRaisesRegex(ValueError, 'minute prefix bits'):
                audit.prefix_proof(output, {'calendar': [0, 120_000_000]}, root, pointer)
            output['minute'] = Minute(old.copy())
            proof = audit.prefix_proof(output, {'calendar': [0, 120_000_000]}, root, pointer)
            self.assertEqual(proof['minute_rows'], 2)
            self.assertFalse(proof['new_metadata_or_full_snapshot_identity_claimed'])


if __name__ == '__main__':
    unittest.main()
