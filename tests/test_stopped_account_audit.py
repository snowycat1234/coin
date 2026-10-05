"""A stopped mark must not be replaced by the last prehalt snapshot."""
import json
import numpy as np
import polars as pl
from scripts.investment import perpetual_directional as engine
from scripts.investment import audit_shared_direction as audit

def test_stopped_mark_reference_and_unchanged_full_calendar(tmp_path):
    start=1_754_006_400_000_000;n=1440;symbols=('BTCUSDT','ETHUSDT')
    market={s:dict(open=np.full(n,100.),close=np.full(n,100.),mark=np.full(n,100.),quote_volume=np.full(n,1_000_000.)) for s in symbols}
    bars=pl.DataFrame([dict(symbol=s,close_us=start,close=100.) for s in symbols])
    def factory(b,d,m):return pl.DataFrame([dict(symbol=s,available_us=int(t),target_weight=-.1 if s=='BTCUSDT' else 0.) for t in d for s in symbols]),{}
    window=dict(symbols=symbols,start=start,end=start+n*engine.MINUTE,daily=bars,market=market,events=[])
    def check(label):
        case=engine.simulate(window,'SHORT_ONLY',engine.COSTS[0],engine.UNITS[0],target_factory=factory)
        directory=tmp_path/label;saved=engine.save_case(case,directory)
        (directory/'summary.json').write_text(json.dumps(saved['summary']))
        return case,audit.verify(directory,symbols,1.)
    full,proof=check('full')
    assert proof['status']=='PASS_INDEPENDENT_SIGNED_JOURNAL_MINUTE_MARKED_NAV_FUNDING_AND_WALLET_IDENTITY'
    market['BTCUSDT']['mark'][2:]=199.5
    stopped,proof=check('stop')
    assert stopped['summary']['account_status']=='LIQUIDATION_REQUIRED_HALT'
    assert proof['status']=='PASS_INDEPENDENT_PREFIX_AND_STOPPED_JOURNAL_WALLET_DECLARED_MARK_NOT_FULL_CALENDAR'
    assert proof['minutes']==2 and proof['terminal_cash_realized'] is False
    assert abs(sum(proof['partial_stop_direction_contribution'][k] for k in ('LONG','SHORT'))-stopped['summary']['net_PnL'])<1e-7
    assert stopped['summary']['NAV']<stopped['minute']['nav'][-1]
