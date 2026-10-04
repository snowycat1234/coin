"""The active multi-asset account specialization forwards cost identity/recovery."""
from decimal import Decimal as D
from quant.paths import ROOT
from scripts.investment.bybit_cost_inputs import snapshot_cost, account_for_cost
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Closing


def test_active_closing_account_cost_forwarding_recovery_and_legacy_default():
    symbols = ('BTCUSDT','ETHUSDT')
    cost = snapshot_cost(ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json',
        symbols=symbols, fee_zone_by_symbol=dict.fromkeys(symbols,'DERIVATIVES_CRYPTO_STANDARD'),
        scenario_id='SYNTHETIC_CLOSING_PROFILE', half_spread_bps=2, slippage_bps=1,
        execution_source_ref='SYNTHETIC_HAND_NOT_CALIBRATED', execution_status='SYNTHETIC_ONLY')
    account = account_for_cost(cost, symbols, Closing)
    account.update_marks(0,{s:dict(price=100,close_us=0,available_us=0) for s in symbols})
    account.execute_fill('BTCUSDT','SELL',10,60_000_001,0,'short',execution_mid_price=100,quote_available_us=0)
    original = account.snapshot()
    restored = Closing.from_snapshot(original,expected_cost_context=cost['provenance'])
    assert restored.snapshot() == original
    assert restored.closing_min_notional_exempt is True
    assert restored.positions['BTCUSDT'].quantity == -10
    restored.update_marks(120_000_000,{s:dict(price=100,close_us=120_000_000,available_us=120_000_000) for s in symbols})
    restored.execute_fill('BTCUSDT','BUY',100,180_000_001,120_000_000,'close',execution_mid_price=100,
        quote_available_us=120_000_000,reduce_only=True)
    assert restored.positions['BTCUSDT'].quantity == 0
    assert restored.fees == D('1.10') and restored.execution_cost == D('.60')
    assert restored.nav() == D('9998.30')
    assert Closing.from_snapshot(restored.snapshot()).snapshot() == restored.snapshot()
    legacy = Closing().snapshot(); del legacy['cost_context']
    assert Closing.from_snapshot(legacy).contract_metadata()['nominal_roundtrip_bps'] == 27
