"""Saved target intent and fill cost counts, not deletable-cost counterfactual."""
import json,hashlib,os
from pathlib import Path
from collections import defaultdict
import polars as pl
from quant.paths import ROOT,STATE
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=ROOT/'reports/fast_research/SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1.json'
v=json.loads(p.read_bytes());last=None;lookup={}
for r in v['target_meta']['risk']:
    if last is None:reason='INITIAL_TARGET'
    elif any(r['component_'+x+'_raw']!=last['component_'+x+'_raw'] for x in ('HOLD','EXIT10')):reason='SIGNAL_COMPONENT_CHANGE'
    elif r['daily_risk_close_us']!=last['daily_risk_close_us']:reason='DAILY_RISK_HOLD_REFRESH'
    elif any(r['component_'+x+'_target']!=last['component_'+x+'_target'] for x in ('HOLD','EXIT10')):reason='INTRADAY_CHANGED_COMPONENT_TARGET'
    else:reason='INTRADAY_IDENTICAL_COMPONENT_TARGET'
    lookup[r['decision_us']]=reason;last=r
cases=[]
for c in v['cases']:
    a=c['artifacts']['trades'];assert sha(a['path'])==a['sha256'];f=pl.read_parquet(a['path'])
    groups=defaultdict(lambda:dict(trades=0,notional_USDT=0.,fee_USDT=0.,execution_USDT=0.))
    for t in f.iter_rows(named=True):
        reason=lookup.get(t['signal_us'],'UNKNOWN')
        if t['signal_us']==c['config']['end_us']-6*60_000_000 and t['target_weight']==0:reason='TERMINAL_EXIT'
        x=groups[reason];x['trades']+=1;x['notional_USDT']+=t['notional'];x['fee_USDT']+=t['fee'];x['execution_USDT']+=t['execution_cost']
    assert abs(sum(x['fee_USDT'] for x in groups.values())-c['summary']['fees'])<1e-7
    assert abs(sum(x['execution_USDT'] for x in groups.values())-c['summary']['execution_costs'])<1e-7
    cases.append(dict(id=c['id'],groups=dict(groups)))
out=STATE/'d080-saved-target-turnover-20261005-v1';out.mkdir()
with (out/'RESULT.json').open('x') as f:json.dump(dict(status='PASS_SAVED_TARGET_INTENT_COST_BRIDGE',task_id=os.environ['COIN_TASK_ID'],input_sha256=sha(p),cases=cases,
 scope='Same-component intraday target is intent only, not proof fill dispensable or risk-free. No simulated deletion of fees/PnL.',new_replays=0),f,indent=2)
print(json.dumps(cases))
