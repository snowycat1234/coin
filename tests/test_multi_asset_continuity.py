"""One synthetic check for the new continuous funding/wallet boundary risk."""
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
import json

import numpy as np
import pytest

from scripts.investment import multi_asset_financial_audit as audit


def test_continuous_wallet_keeps_owned_boundary_funding(tmp_path):
    spec = dict(start='2024-09-01T00:00:00+00:00', end_exclusive='2024-12-01T00:00:00+00:00',
        period_days=91, account_path='CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D',
        data_role='SEEN_DEVELOPMENT_CONTINUOUS_ACCEPTED_THREE_MONTH_MANIFEST')
    scope = audit.calendar_scope(spec)
    assert scope['period_days'] == 91 and scope['required_minutes'] == 131040
    symbols = ('BTCUSDT', 'ETHUSDT')
    base, _, proof = audit.prepare_financial(symbols)
    ref = base.module(base.REFERENCE, 'd055_boundary_independent_hand', base.REFERENCE_SHA)
    start, end = scope['start_us'], scope['end_us']
    count = scope['required_minutes']
    boundaries = [int(datetime(2024, m, 1, tzinfo=UTC).timestamp()) * 1_000_000 for m in (10, 11)]
    window = dict(start=start, end=end, count=count, days=91,
        market={s:dict(open=np.full(count, 100.), mark=np.full(count, 100.),
                       quote=np.full(count, 1_000_000.)) for s in symbols},
        events=[dict(symbol='BTCUSDT', event_us=t, raw_rate=rate)
                for t, rate in zip(boundaries, (.01, .02), strict=True)])
    # Hand arithmetic: reserve100.08, fees .055044+.054956, price loss .16,
    # Oct and Nov owned coupons -1 and -2. Initial10k therefore ends9996.73.
    common = dict(symbol='BTCUSDT', quantity=1., execution_mid_price=100.,
        mark_price=100., fee_asset='USDT', execution_cost=.08)
    opening = dict(common, fill_id='entry', leg='OPEN', side='BUY', position_delta=1.,
        event_us=start+audit.MINUTE+1, signal_us=start, fill_price=100.08,
        quantity_before=0., quantity_after=1., entry_price_before=0., entry_price_after=100.08,
        fee_amount=.055044, fee_USDT_mid=.055044, realized_PnL=0., cash_delta=-.055044,
        margin_allocated=100.08, margin_released=0., isolated_balance_delta=100.08,
        free_cash_delta=-100.135044)
    closing = dict(common, fill_id='exit', leg='CLOSE', side='SELL', position_delta=-1.,
        event_us=end-audit.MINUTE+1, signal_us=end-2*audit.MINUTE, fill_price=99.92,
        quantity_before=1., quantity_after=0., entry_price_before=100.08, entry_price_after=0.,
        fee_amount=.054956, fee_USDT_mid=.054956, realized_PnL=-.16, cash_delta=-.214956,
        margin_allocated=0., margin_released=100.08, isolated_balance_delta=-100.08,
        free_cash_delta=99.865044)
    funds = [dict(row, owned=True, quantity=1., mark_price=100., mark_close_us=row['event_us']-audit.MINUTE,
                  signed_funding_USDT=-amount)
             for row, amount in zip(window['events'], (1., 2.), strict=True)]
    case = dict(mode='LONG_ONLY', cost_id='BASE27', unit_id='RAW_AS_FRACTION')
    errors = dict(cash=0., ratio=0.)
    result = base.financial_journals(window, case, [opening, closing], funds, ref, errors)
    hand = result['hand']['BTCUSDT']
    assert result['owned'] == 2 and hand.funding_cash == Decimal('-3')
    assert hand.quantity == 0 and result['margin']['BTCUSDT'] == 0
    assert result['free'] == Decimal('9996.730000') and hand.wallet == Decimal('-3.270000')
    assert result['liability'] == 0
    before_second = base.sample(result['states'], np.array([boundaries[1]]), 'left')
    assert before_second['q'][0, 0] == 1. and before_second['margin'][0, 0] == 100.08
    assert before_second['entry'][0, 0] == 100.08 and before_second['funding'][0] == -1.
    reset = deepcopy(funds)
    reset[0].update(owned=False, quantity=0., signed_funding_USDT=0.)
    with pytest.raises(ValueError, match='Funding signed owned quantity'):
        base.financial_journals(window, case, [opening, closing], reset, ref, dict(cash=0., ratio=0.))
    with pytest.raises(ValueError, match='Every original signed funding row'):
        base.financial_journals(window, case, [opening, closing], funds[1:], ref, dict(cash=0., ratio=0.))
    (tmp_path / 'continuous_boundary_evidence.json').write_text(json.dumps(dict(
        period_days=91, retained_owned_coupons=2, exact_funding='-3', exact_final_cash='9996.73',
        no_monthly_quantity_entry_margin_wallet_reset=True, cash_tolerance_USDT=base.CASH_TOL,
        ratio_tolerance=base.RATIO_TOL, unchanged_financial_AST=proof['financial_function_bytecode_unchanged'])),
        encoding='utf-8')
