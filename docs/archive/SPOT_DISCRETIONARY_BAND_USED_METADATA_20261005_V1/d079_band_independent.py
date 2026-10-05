"""Independently verify saved band intentions and no-cost skipped actual goals."""
import argparse,hashlib,json,os,time
from pathlib import Path
from collections import Counter
import numpy as np
import polars as pl
R=Path('/mnt/d/codex/coin');S=Path('/home/xflops/coin-state')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def frame(a):
    assert sha(a['path'])==a['sha256'];return pl.read_parquet(a['path'])
p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();began=time.monotonic()
v=json.loads(a.input.read_bytes());ctrl=json.loads(Path(v['spot_control']['path']).read_bytes())
assert sha(v['spot_control']['path'])==v['spot_control']['sha256']
assert a.output.resolve().is_relative_to(S) and not a.output.exists()
targets=frame(v['target_artifact']);original=frame(ctrl['target_artifact'])
assert targets.select(original.columns).equals(original)
symbols=v['cases'][0]['symbols'];contexts=v['target_meta']['risk']
previous=None;checks=0;reasons=Counter()
for i,r in enumerate(contexts):
    for j,s in enumerate(symbols):
        row=targets.row(i*len(symbols)+j,named=True)
        reason='DISCRETIONARY_REBALANCE'
        if previous is None:reason='INITIAL_TARGET'
        elif row['eligibility_reason']!='ELIGIBLE' or row['eligibility_reason']!=previous['eligibility'][s]:reason='DATA_EXIT'
        else:
            rawchanged=any(any(x!=y for x,y in zip(r['component_'+c+'_raw'],previous['component_'+c+'_raw'],strict=True)) for c in ('HOLD','EXIT10'))
            decrease=any(r['component_'+c+'_target'][j]<previous['component_'+c+'_target'][j] for c in ('HOLD','EXIT10'))
            if rawchanged:reason='SIGNAL_COMPONENT_CHANGE'
            elif decrease:reason='VOLATILITY_RISK_REDUCTION'
        assert row['target_reason']==reason and row['discretionary_rebalance']==(reason=='DISCRETIONARY_REBALANCE')
        reasons[reason]+=1;checks+=1
    previous=r
minutes=frame(v['market_minutes']);cases=[]
for case in v['cases']:
    orders=frame(case['artifacts']['orders.parquet']);trades=frame(case['artifacts']['trades'])
    clocks=orders['open_us'].unique().to_list()
    prices={(r['open_us'],r['symbol']):r['open'] for r in minutes.filter(pl.col('open_us').is_in(clocks)).iter_rows(named=True)}
    fills={(r['execution_us']-1,r['symbol']):r for r in trades.iter_rows(named=True)}
    q=dict.fromkeys(symbols,0.);cash=10000.;skipped=0;protected=0;started=set();seenfills=0
    for o in orders.iter_rows(named=True):
        stamp,s=o['open_us'],o['symbol'];key=(o['signal_us'],s);f=fills.get((stamp,s))
        nav=cash+sum(q[x]*prices[(stamp,x)] for x in symbols)
        breached=any(q[x]*prices[(stamp,x)]>case['config']['max_weight']*nav+1e-7 for x in symbols) or sum(q[x]*prices[(stamp,x)] for x in symbols)>case['config']['max_gross']*nav+1e-7
        if o['status']=='rebalance_band':
            assert o['discretionary_rebalance'] and o['target_reason']=='DISCRETIONARY_REBALANCE'
            assert not o['rebalance_band_exempt'] and o['rebalance_band_skipped']
            assert 0<o['requested_notional']<50 and o['filled_notional']==o['quantity']==0
            assert q[s]>0 and not breached and key not in started and f is None
            assert stamp+1>o['signal_us'] and o['capacity_open_us']<stamp
            skipped+=1
        elif f is not None:
            assert not f['rebalance_band_skipped'] and f['target_reason']==o['target_reason']
            if o['target_reason']!='DISCRETIONARY_REBALANCE':assert o['rebalance_band_exempt']
            if key in started or breached or q[s]<=0:assert o['rebalance_band_exempt']
            if o['rebalance_band_exempt']:protected+=1
            q[s]+=f['position_delta'];cash+=f['cash_delta'];started.add(key);seenfills+=1
    assert seenfills==trades.height and skipped>0
    final=cash+sum(q[x]*case['terminal_marks'][x]['price'] for x in symbols)
    assert abs(final-case['summary']['final_nav'])<1e-7
    cases.append(dict(id=case['id'],orders=orders.height,actual_fills=seenfills,actual_skipped_goals=skipped,
        protected_or_started_fills=protected,terminal_NAV_error=abs(final-case['summary']['final_nav'])))
out=dict(status='PASS_UNCHANGED_TARGETS_EXPLICIT_PROTECTION_AND_NO_FILL_BAND_ORDERS',input_sha256=sha(a.input),
    task_id=os.environ['COIN_TASK_ID'],target_rows_checked=checks,reason_counts=dict(reasons),cases=cases,
    elapsed_seconds=time.monotonic()-began,source_sha256=sha(__file__),scope='Uses saved orders and pinned source open prices, sequential saved fills after independent monetary audit. No new account replay or counterfactual alpha proof.')
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out))
