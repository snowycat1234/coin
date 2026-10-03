"""One UNRUN conditional closing-filter regression; no native-filter claim.

Only new closing exemptions are exercised. The frozen independent HandLedger
checks actual signed fills, fees and wallet/NAV; no old suite or market replay.
All generated evidence stays in the caller's new STATE pytest directory.
"""
from copy import deepcopy
from decimal import Decimal as D, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATE = Path('/home/xflops/coin-state')
ACCOUNT = 'scripts/investment/perpetual_closing_exempt_account.py'
ACCOUNT_SHA = 'd4c1636be51b067be6b86437cd69f158320f47c258f0d78f0a47f21806c617ac'
ORIGINAL_SHA = 'cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261'
HAND = 'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
HAND_SHA = '3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'
PROFILE = 'CLOSING_MIN_NOTIONAL_EXEMPT_WITH_UNCERTIFIED_1E8_QUANTITY_V1'
MINUTE = 60_000_000
TOL = D('1e-24')


def test_closing_exemption_partial_restore_and_independent_wallet(tmp_path):
    assert tmp_path.resolve().is_relative_to(STATE)
    assert hashlib.sha256((ROOT / ACCOUNT).read_bytes()).hexdigest() == ACCOUNT_SHA
    assert hashlib.sha256((ROOT / 'src/quant/perpetual_account.py').read_bytes()).hexdigest() == ORIGINAL_SHA
    assert hashlib.sha256((ROOT / HAND).read_bytes()).hexdigest() == HAND_SHA

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, ROOT / path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    new = load('d048_closing_exempt_case', ACCOUNT)
    reference = load('d048_frozen_hand_ledger', HAND)
    from quant.perpetual_account import USDTLinearPerpetualAccount as Original
    Account = new.USDTLinearPerpetualAccount
    assert new.FILTER_PROFILE_ID == PROFILE and new.VERSION != Original().snapshot()['version']
    assert Account().config == Original().config  # No fee, step, capital or risk change.
    derivation = new.derivation_receipt()
    assert derivation['original_source_sha256'] == ORIGINAL_SHA
    assert derivation['financial_leg_body_unchanged'] and derivation['config_unchanged']
    assert sum(len(row['changes']) for row in derivation['methods']) == 1
    assert all(row['original_body_AST_sha256'] == row['derived_body_AST_sha256']
               for row in derivation['methods'] if row['name'] != 'execute_fill')

    def marks(account, t, price='100'):
        account.update_marks(t, {s: dict(price=price, close_us=t, available_us=t)
                                 for s in ('BTCUSDT', 'ETHUSDT')})

    def fill(account, side, q, minute, identity, *, mid='90', capacity=None, reduce_only=True):
        return account.execute_fill('BTCUSDT', side, q, minute * MINUTE + 1,
            (minute - 1) * MINUTE, identity, execution_mid_price=mid,
            quote_available_us=minute * MINUTE, available_quantity=capacity, reduce_only=reduce_only)

    def near(actual, expected):
        assert abs(actual - expected) <= TOL

    evidence = []

    def checked_fill(account, hand, side, q, minute, identity, expected_q, **options):
        with localcontext() as context:
            context.prec = 50
            mid = D(options.get('mid', '90'))
            direction = D(1) if side == 'BUY' else D(-1)
            expected_fill = mid * (1 + direction * D('.0008'))
            receipt = fill(account, side, q, minute, identity, **options)
            assert D(receipt['decimal_strings']['executed_quantity']) == D(expected_q)
            assert len(receipt['fills']) == 1
            row = receipt['fills'][0]
            near(D(row['decimal_strings']['fill_price']), expected_fill)
            near(D(row['decimal_strings']['fee_amount']), D(expected_q) * expected_fill * D('.00055'))
            hand.fill(direction * D(expected_q), expected_fill, '.00055')
            near(account.positions['BTCUSDT'].quantity, hand.quantity)
            near(account.positions['BTCUSDT'].entry_price, hand.entry_fill)
            near(account.free_cash + sum(p.isolated_balance for p in account.positions.values()), hand.wallet)
            near(account.fees, hand.fees)
            near(account.nav(), hand.equity(account.marks['BTCUSDT'][-1]['price']))
            assert account.unpaid_liability == 0 and account.status == 'ACTIVE'
            evidence.append(receipt)
            return receipt

    # Sub10 opening stays rejected on both sides; future quotes do not mutate state.
    empty = Account(); marks(empty, 0)
    before = deepcopy(empty.snapshot())
    with pytest.raises(ValueError, match='availability'):
        empty.execute_fill('BTCUSDT', 'BUY', '1', MINUTE + 1, 0, 'future',
            execution_mid_price='100', quote_available_us=MINUTE + 2)
    assert empty.snapshot() == before
    for side in ('BUY', 'SELL'):
        rejected = fill(empty, side, '.05', 1, 'small-open-' + side, mid='100', reduce_only=False)
        assert rejected['status'] == 'REJECTED' and rejected['fills'] == []
    assert empty.nav() == 10000 and empty.fees == 0 and empty.positions['BTCUSDT'].quantity == 0

    # Open at trade-mid100; reduce0.9 at90 leaves an actual9USDT short position.
    # Same-quantity mid gross is10; spread/slippage and actual quote fees reduce it.
    account = Account(); marks(account, 0)
    hand = reference.HandLedger(D(10000))
    checked_fill(account, hand, 'SELL', '1', 1, 'short', '1', mid='100', reduce_only=False)
    marks(account, 2 * MINUTE, '90')
    checked_fill(account, hand, 'BUY', '.9', 2, 'reduce-to-sub10', '.9')
    assert account.positions['BTCUSDT'].quantity == D('-.1')
    residual = deepcopy(account.snapshot())

    # A small non-reduce-only closing order is still a pure reduction; a flip
    # closes existing inventory but cannot use that exemption to open below10.
    pure = Account.from_snapshot(residual); pure_hand = deepcopy(hand)
    checked_fill(pure, pure_hand, 'BUY', '.02', 3, 'pure-small-close', '.02', reduce_only=False)
    assert pure.positions['BTCUSDT'].quantity == D('-.08')
    flip = Account.from_snapshot(residual); flip_hand = deepcopy(hand)
    reversed_receipt = checked_fill(flip, flip_hand, 'BUY', '.15', 3, 'small-flip', '.1', reduce_only=False)
    assert reversed_receipt['reason'] == 'OPENING_LEG_BELOW_MIN_NOTIONAL'
    assert reversed_receipt['status'] == 'PARTIAL' and flip.positions['BTCUSDT'].quantity == 0
    assert all(row['leg'] == 'CLOSE' for row in reversed_receipt['fills'])

    # Actual capacity limits an under10 partial close. Restore must retain the
    # exact request journal so repetition charges no second fee or close leg.
    first = checked_fill(account, hand, 'BUY', '.08', 3, 'small-capacity', '.03', capacity='.03')
    assert first['status'] == 'PARTIAL' and account.positions['BTCUSDT'].quantity == D('-.07')
    restored = Account.from_snapshot(account.snapshot())
    snapshot = deepcopy(restored.snapshot())
    assert fill(restored, 'BUY', '.08', 3, 'small-capacity', capacity='.03') == first
    assert restored.snapshot() == snapshot
    with pytest.raises(ValueError, match='conflicting'):
        fill(restored, 'BUY', '.09', 3, 'small-capacity', capacity='.03')
    assert restored.snapshot() == snapshot
    with pytest.raises(ValueError, match='product|version|profile'):
        Account.from_snapshot(Original().snapshot())
    with pytest.raises(ValueError, match='product|version|profile'):
        Original.from_snapshot(restored.snapshot())
    wrong_profile = deepcopy(restored.snapshot())
    wrong_profile['contract']['filter_profile_id'] = 'INCOMPATIBLE_FILTER_PROFILE'
    with pytest.raises(ValueError, match='product|version|profile'):
        Account.from_snapshot(wrong_profile)

    # Oversized reduce-only respects available quantity and the held remainder.
    second = checked_fill(restored, hand, 'BUY', '.2', 4, 'oversized-capacity', '.04', capacity='.04')
    assert second['status'] == 'PARTIAL' and restored.positions['BTCUSDT'].quantity == D('-.03')
    last = checked_fill(restored, hand, 'BUY', '1', 5, 'full-sub10', '.03')
    assert last['status'] == 'PARTIAL' and restored.positions['BTCUSDT'].quantity == 0
    assert restored.positions['BTCUSDT'].isolated_balance == 0
    fees_before = restored.fees
    rejected = fill(restored, 'BUY', '.05', 6, 'over-reduce-flat')
    assert rejected['fills'] == [] and restored.fees == fees_before
    below_step = fill(restored, 'SELL', '.000000003', 6, 'below-proxy-step', reduce_only=False)
    assert below_step['fills'] == [] and restored.positions['BTCUSDT'].quantity == 0
    summary = restored.summary()
    near(D(summary['decimal_strings']['gross_PnL_same_quantities']), D(10))
    near(restored.execution_cost, D('.152'))
    near(restored.fees, D('.1044956'))
    near(restored.nav(), D('10009.7435044'))
    near(hand.bridge(10000, '90'), D(0))
    assert restored.contract_metadata()['native_filters_certified'] is False
    assert hashlib.sha256((ROOT / 'src/quant/perpetual_account.py').read_bytes()).hexdigest() == ORIGINAL_SHA
    (tmp_path / 'closing_exemption_evidence.json').write_text(json.dumps(dict(
        scope='SYNTHETIC_CLOSING_PROFILE_PROXY_NOT_NATIVE_BYBIT_FILTERS',
        filter_profile=PROFILE, original_source_sha256=ORIGINAL_SHA, hand_source_sha256=HAND_SHA,
        new_source_sha256=ACCOUNT_SHA, derivation=derivation, receipts=evidence, final_summary=summary,
        quantity_step_certified=False, historical_filter_certified=False,
        market_inputs_read=False, orders_sent=0), indent=2, sort_keys=True), encoding='utf-8')
