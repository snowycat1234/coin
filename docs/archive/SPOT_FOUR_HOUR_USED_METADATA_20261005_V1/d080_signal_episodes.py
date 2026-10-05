import json,os,hashlib
from pathlib import Path
import numpy as np
from quant.paths import ROOT,STATE
p=ROOT/'reports/fast_research/SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1.json'
v=json.loads(p.read_bytes());out=[]
for j,s in enumerate(v['target_meta']['symbols']):
    entered=None;episodes=[]
    for r in v['target_meta']['risk']:
        held=r['component_EXIT10_raw'][j]>0
        if held and entered is None:entered=r['decision_us']
        elif not held and entered is not None:
            episodes.append(dict(entry_us=entered,exit_us=r['decision_us'],held_hours=(r['decision_us']-entered)/3.6e9));entered=None
    hours=[x['held_hours'] for x in episodes]
    out.append(dict(symbol=s,closed_episodes=episodes,right_censored_entry_us=entered,
        completed_count=len(hours),median_hours=float(np.median(hours)) if hours else None,
        completed_under_24h=sum(h<24 for h in hours),completed_under_48h=sum(h<48 for h in hours)))
d=STATE/'d080-saved-signal-episodes-20261005-v1';d.mkdir()
with (d/'RESULT.json').open('x') as f:json.dump(dict(status='DESCRIPTIVE_COMPONENT_SIGNAL_EPISODES_NOT_ACCOUNT_PNL',input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),task_id=os.environ['COIN_TASK_ID'],assets=out,
 scope='COIN EXIT10 component intent, not executed separate wallet or causal profit attribution. No horizon/parameter selection.'),f,indent=2)
print(json.dumps([{k:x for k,x in r.items() if k!='closed_episodes'} for r in out]))
