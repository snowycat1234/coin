"""Only generated minute quotes. Native owner receipts are the sole evidence."""
from pathlib import Path
import json
import numpy as np
from generated_fixtures import make_generated,BASE27,UNIT,START,DAY,MINUTE,S,finish
from finite_candidate import FiniteNativeCandidate

def make_candidate(bundle,cost=BASE27,*,preloaded=True):
    return FiniteNativeCandidate(bundle[0],'LONG_SHORT',cost,UNIT,source_registry=bundle[3],
        source_packets=bundle[2],target_factory=bundle[1] if preloaded else None)

def demo_bundle():
    prices={s:np.full(1440,100.) for s in S}
    prices[S[0]][20:]=94.;prices[S[0]][50:]=88.;prices[S[0]][80:]=82.
    return make_generated(weights=[.06,.08,.08,0,0],minute_prices=prices)

def run_demo(receipt_dir=None):
    bundle=demo_bundle();sim=make_candidate(bundle);finish(sim)
    result=sim.result();summary=result['summary']
    report={'scope':'ONE_GENERATED_FINITE_NATIVE_CASE_NOT_PERFORMANCE_RESEARCH',
        'new_historical_wallets':0,'live_trades':0,'historical_status':'NO_GO',
        'summary':summary,'native_trades':sim.account.trades,'native_funding':sim.funding_journal,
        'owner_fill_allocations':result['owner_fill_allocations'],
        'owner_funding_allocations':result['owner_funding_allocations'],
        'owner_events':result['owner_events'],'rejections':sim.rejections,
        'exact_account_snapshot':sim.account.snapshot()}
    if receipt_dir:
        path=Path(receipt_dir);path.mkdir(parents=False,exist_ok=False)
        (path/'DEMO.json').write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return {'scope':report['scope'],'program_completed_opening_orders':sim.program.completed_opening_orders,
        'native_trade_legs':len(sim.account.trades),'exact_final_NAV':str(sim.account.nav()),
        'completion':sim.completion,'stop_us':sim.stop,
        'owner_reconciliation':summary['owner_reconciliation'],'historical_status':'NO_GO'}
