import copy
from .report import compare,BASELINES

def test_rank_uses_worst_funding_and_retains_all_seed_evidence():
    rows=[];protocol=dict(models=['A','B'],seeds=[1,2,3])
    for scale in (1.,.01):
      for i in range(6):
        window=f'w{i}'
        for baseline in (*BASELINES,'OLD_FROZEN_TRANSFORMER_SHARED'):
            rows.append(dict(family=baseline,seed='FROZEN_LEGACY',mapping='DIRECTIONAL',funding_scale=scale,window=window,net_return_percent=0,full_calendar_and_paid_cash=True))
        for family in protocol['models']:
          for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):
            value=(10 if scale==1 else -1) if family=='A' else 1+i*.01
            for seed in (1,2,3,'ENSEMBLE'):
                rows.append(dict(family=family,seed=seed,mapping=mapping,funding_scale=scale,window=window,net_return_percent=value,full_calendar_and_paid_cash=True))
    before=copy.deepcopy(rows);summaries,paired,chosen=compare(rows,protocol)
    assert chosen['family']=='B' and chosen['development_gate_pass']
    assert rows==before and len(paired)==72
