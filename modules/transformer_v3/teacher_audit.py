"""Audit only past-development teacher eligibility; never train or open locked labels."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from modules.transformer_v2.data import chronological_inner
from modules.transformer_v2.train import atomic,sha
from .teachers import load_teacher_development,training_teacher_view,ACTIONS

def audit(d):
    rows=[]
    for fi,fold in enumerate(d['folds'],1):
        active=np.array([s in fold['active'] for s in d['symbols']]);outer=np.array(sorted({i for _,_,i in fold['train']}))
        inner,valid=chronological_inner(outer,d['dates'],d['label_end'])
        inner_cutoff=d['dates'][valid[0]]-pd.Timedelta(days=60)
        for name,indices,cutoff in (('INNER_TRAIN',inner,inner_cutoff),('INNER_VALIDATION',valid,fold['cutoff']),('OUTER_REFIT',outer,fold['cutoff'])):
            view=training_teacher_view(d,indices,cutoff,active)
            for scenario,tag in enumerate(('raw_fraction','raw_percent')):
                u=view['expert_utilities'][scenario];mask=view['expert_valid'][scenario];best=np.argmax(np.where(mask[...,None],u,0.),-1)
                rows.append(dict(fold=fi,role=name,scenario=tag,samples=len(indices),active_symbols=fold['active'],expert_valid_asset_samples=int(mask.sum()),
                    action_counts={action:int(((best==a)&mask).sum()) for a,action in enumerate(ACTIONS)},
                    direction_valid_asset_samples=int(view['direction_valid'].sum()),relative_valid_asset_samples=[int(view['relative_valid'][...,h].sum()) for h in range(3)],
                    min_decision_row=d['dates'][indices[0]].isoformat(),max_decision_row=d['dates'][indices[-1]].isoformat(),
                    latest_label_end=d['label_end'][indices].max().isoformat(),purge_cutoff=cutoff.isoformat(),
                    gap_scale_descriptive=view['gap_scales'][scenario],gap_scale_role='USED_ONLY_IF_TRAIN_ROLE; VALIDATION_USES_INNER_TRAIN_SCALE',
                    full_future_maturity_verified=True,no_gap_bridge=True,no_locked_labels=True,embargo_days=60))
    return dict(status='PASS_TRAINING_TEACHER_CHRONOLOGY_AUDIT',teachers=['DIRECTION_TEACHER_30D','RELATIVE_RANK_TEACHER_30D','EXPERT_TEACHER_60D'],
                actions=list(ACTIONS),rows=rows,source_receipts=d['teacher_receipts'],data_max_date=d['dates'].max().isoformat(),
                expert_scope='REUSED_CONTINUOUS_DAILY_COST_AND_FUNDING_AWARE_EXPERT_PROXY; NOT_MINUTE_WALLET_EQUIVALENT',
                inference_has_no_teacher_inputs=True,new_fits=0,protocol_frozen=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);a=p.parse_args()
    d=load_teacher_development(a.collector_root,a.work,a.source_run);result=audit(d)
    result['audit_source_sha256']=sha(__file__);path=Path(a.state)/'TEACHER_AUDIT_PRELIMINARY.json'
    if path.exists():raise RuntimeError('Preserve previous teacher audit receipt')
    atomic(path,result);print(result['status'],len(result['rows']),'chronology rows; no fitting',flush=True)

if __name__=='__main__':main()
