"""Read saved panels/predictions only. No labels/features/fits/accounts rerun."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json
import numpy as np

state=Path('/home/ubuntu/coin/execution-state/joint-information-20261008-v1')
r=json.loads((state/'RESULTS.json').read_text())
pred=json.loads((state/'PREDICTIONS.json').read_text())
def date(us): return datetime.fromtimestamp(int(us)/1e6,timezone.utc).strftime('%Y-%m-%d')
def spans(values):
    out=[]
    for v in values:
        if not out or v-out[-1][-1]!=86400000000:out.append([v])
        else:out[-1].append(v)
    return [dict(start=date(v[0]),end=date(v[-1]),daily_rows=len(v)) for v in out]
with np.load(state/'PAST_INTENTS.npz',allow_pickle=False) as a:
    market_good=np.isfinite(a['market']).all(1)
out=dict(source='existing saved panels and predictions only',new_fits=0,new_wallets=0,coverage=[],actions=[])
for scale in (1,0.01):
    with np.load(state/f'REFERENCE_PANEL_{scale}.npz',allow_pickle=False) as a:
        d=a['decision_us'];av=a['label_available_us'];y=a['labels'];feedback_good=np.isfinite(a['feedback']).all(1);complete=a['common']&np.isfinite(y).all(1)
        for w in r['protocol']['windows']:
            eligible=(d<w['start'])&(av<w['start']-7*86400000000)
            train=eligible&complete
            out['coverage'].append(dict(scale=scale,window=w['id'],calendar_eligible=int(eligible.sum()),market_eligible=int((eligible&market_good).sum()),feedback_eligible=int((eligible&feedback_good).sum()),complete_train=int(train.sum()),train_spans=spans(d[train]),missing_market_spans=spans(d[eligible&~market_good]),missing_feedback_spans=spans(d[eligible&market_good&~feedback_good]),missing_labels_spans=spans(d[eligible&a['common']&~np.isfinite(y).all(1)])))
for p,c in zip(pred,r['cases']):
    assert (p['window'],p['funding_scale'],p['input'])==(c['window'],c['funding_scale'],c['input'])
    y=np.array(p['actual_reference_utility']);z=np.array(p['predicted_reference_utility']);choice=z.argmax(1);winner=y.argmax(1)
    regret=y.max(1)-y[np.arange(len(y)),choice]
    worst=np.argsort(-regret)[:3]
    names=r['protocol']['experts']
    pairs=Counter((names[c],names[w]) for c,w in zip(choice,winner))
    chosen=y[np.arange(len(y)),choice]
    out['actions'].append(dict(window=p['window'],scale=p['funding_scale'],input=p['input'],choice_counts={names[k]:int((choice==k).sum()) for k in range(4)},oracle_winner_counts={names[k]:int((winner==k).sum()) for k in range(4)},chosen_by_expert_sum_bp={names[k]:float(chosen[choice==k].sum()*1e4) for k in range(4)},choice_winner_pairs={a+' -> '+b:n for (a,b),n in pairs.items()},largest_regrets=[dict(decision=date(p['decision_us'][i]),choice=names[choice[i]],winner=names[winner[i]],regret_bp=float(regret[i]*1e4),chosen_bp=float(chosen[i]*1e4),oracle_bp=float(y[i].max()*1e4)) for i in worst]))
out['market_combined_same_choices']=all(a['metrics']['choices']==next(b for b in r['cases'] if b['window']==a['window'] and b['funding_scale']==a['funding_scale'] and b['input']=='COMBINED')['metrics']['choices'] for a in r['cases'] if a['input']=='MARKET_INTENT' and '2024' in a['window'])
path=state/'READ_ONLY_DIAGNOSIS.json';path.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
