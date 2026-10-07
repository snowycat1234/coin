from decimal import Decimal as D
import numpy as np
import polars as pl
import pytest
from modules.expert_aggregation.funding import factor,AdverseFundingAccount,independent
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment import perpetual_directional as engine

@pytest.mark.parametrize('q,r,f',[('1','.01','2'),('-1','.01','.5'),('1','-.01','.5'),('-1','-.01','2'),('0','.01','1')])
def test_adverse_signed_payment_and_receipt(q,r,f):assert factor(q,r)==D(f)

@pytest.mark.parametrize('signed',[.1,-.1])
def test_full_wallet_pressure_cash_and_original_rate_audit(tmp_path,signed):
    start=1754006400000000;n=2880;price=np.full(n,100.)
    window=dict(start=start,end=start+n*engine.MINUTE,symbols=('BTCUSDT',),
        daily=pl.DataFrame([dict(symbol='BTCUSDT',close_us=start+i*engine.DAY,close=100.) for i in range(3)]),
        market={'BTCUSDT':dict(open=price,close=price,mark=price,quote_volume=np.full(n,1e8))},
        events=[dict(symbol='BTCUSDT',event_us=start+8*60*engine.MINUTE,raw_rate=.01,reported_interval_hours=8.)])
    def targets(bars,decisions,mode):return pl.DataFrame([dict(symbol='BTCUSDT',available_us=int(t),target_weight=signed if i==0 else 0.) for i,t in enumerate(decisions)]),{}
    normal=engine.simulate(window,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,account_factory=BybitIsolatedAccount,persist_cash_close=True)
    adverse=engine.simulate(window,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,account_factory=AdverseFundingAccount,persist_cash_close=True)
    assert adverse['summary']['NAV']<normal['summary']['NAV']
    assert adverse['funding'][0]['raw_rate']==normal['funding'][0]['raw_rate']==.01
    dest=tmp_path/'wallet';saved=engine.save_case(adverse,dest)
    from modules.expert_aggregation.common import atomic
    atomic(dest/'summary.json',saved['summary'])
    proof=independent(dest,1.,True,tmp_path/'audit')
    assert proof['maximum_NAV_error_USDT']<1e-7
    assert adverse['summary']['terminal_cash_realized'] and adverse['summary']['fees_USDT']>0
