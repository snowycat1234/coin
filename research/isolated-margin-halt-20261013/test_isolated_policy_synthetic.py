"""Pure synthetic tests of the generic frozen account's isolation semantics.

No historical replay, source market tape, or wallet state is opened or written.
"""
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve()
REPO = next((p for p in HERE.parents if (p / 'src/quant/perpetual_account.py').exists()), None)
if REPO is None:  # Local research artifact before copying into the public repository.
    REPO = HERE.parents[1] / 'coin_native_half_mix_20261013' / 'repo'
sys.path[:0] = [str(REPO), str(REPO / 'src')]
from quant.perpetual_account import InstrumentProfile, USDTLinearPerpetualAccount

ENTRY_MARK = D('0.53197408')
PRE_MARK = D('1.05526648')
HALT_MARK = D('1.06181663')
MMR = D('0.005')


def seed_short():
    account = USDTLinearPerpetualAccount(
        symbols=('XRPUSDT',),
        instrument_profiles={'XRPUSDT': InstrumentProfile(quantity_step=D(100))},
    )
    account.update_marks(0, {'XRPUSDT': dict(price=ENTRY_MARK, close_us=0, available_us=0)})
    receipt = account.execute_fill('XRPUSDT', 'SELL', 300, 60_000_001, 0, 'synthetic-open',
        execution_mid_price=ENTRY_MARK, quote_available_us=60_000_000,
        available_quantity=300)
    assert receipt['status'] == 'FILLED'
    account.update_marks(120_000_000, {'XRPUSDT': dict(price=PRE_MARK, close_us=120_000_000,
                                                      available_us=120_000_000)})
    assert account.status == 'ACTIVE'
    return account


def ratio(account, mark):
    p = account.positions['XRPUSDT']
    equity = p.isolated_balance + p.quantity * (mark - p.entry_price)
    maintenance = abs(p.quantity) * mark * MMR
    return equity / maintenance


def close(account, quantity):
    receipt = account.execute_fill('XRPUSDT', 'BUY', quantity, 180_000_001, 120_000_000,
        f'synthetic-close-{quantity}', execution_mid_price=PRE_MARK,
        quote_available_us=180_000_000, available_quantity=quantity, reduce_only=True)
    assert receipt['status'] == 'FILLED'


class IsolatedPolicyTests(unittest.TestCase):
    def test_free_cash_does_not_rescue_isolated_short(self):
        account = seed_short()
        account.update_marks(240_000_000, {'XRPUSDT': dict(price=HALT_MARK,
            close_us=240_000_000, available_us=240_000_000)})
        self.assertEqual(account.status, 'LIQUIDATION_REQUIRED_HALT')
        self.assertGreater(account.free_cash, D('9000'))
        self.assertGreater(account.nav(), 0)
        self.assertLess(ratio(account, HALT_MARK), 1)

    def test_substep_reduction_floors_to_zero(self):
        account = seed_short()
        self.assertEqual(account._floor('XRPUSDT', D('62.11890914338037')), 0)
        self.assertEqual(account._floor('XRPUSDT', D('100')), 100)

    def test_partial_close_preserves_margin_ratio_at_fixed_mark(self):
        account = seed_short()
        pre_ratio = ratio(account, PRE_MARK)
        close(account, 100)
        self.assertEqual(account.positions['XRPUSDT'].quantity, -200)
        self.assertEqual(ratio(account, PRE_MARK), pre_ratio)
        account.update_marks(240_000_000, {'XRPUSDT': dict(price=HALT_MARK,
            close_us=240_000_000, available_us=240_000_000)})
        self.assertEqual(account.status, 'LIQUIDATION_REQUIRED_HALT')

    def test_full_close_before_observed_breach_removes_exposure(self):
        account = seed_short()
        close(account, 300)
        self.assertEqual(account.positions['XRPUSDT'].quantity, 0)
        self.assertEqual(account.status, 'ACTIVE')
        account.update_marks(240_000_000, {'XRPUSDT': dict(price=HALT_MARK,
            close_us=240_000_000, available_us=240_000_000)})
        self.assertEqual(account.status, 'ACTIVE')
        self.assertGreater(account.nav(), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
