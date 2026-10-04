"""Saved Turtle semantic migration check and one-factor economic contrast.

No account or market replay. The old default is checked at trajectory/leg
scope; investment comparison uses two new accounts in the same normal loop.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
import gc
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment import perpetual_directional as engine
from scripts.investment import turtle_turnover_diagnostic as diagnostic
from scripts.research_v8.registry import FIELDS,append_event

CASH_TOL=1e-7
RATIO_TOL=1e-10


def closed(id):
    value=engine.small(STATE/'task-progress'/('task-'+id+'.json'))
    engine.need(value['id']==id and value['status']=='completed' and value['exit_code']==0,
                'Real producer completed0')
    return value


def payload(case,name):
    ref=case['artifacts'][name];p=Path(ref['path']).resolve()
    engine.need(p.is_relative_to(STATE) and p.name==name and p.parent.name==case['id']
        and not p.is_symlink() and engine.sha(p)==ref['sha256'],'Exact saved artifact')
    return pl.read_parquet(p) if name.endswith('.parquet') else json.loads(p.read_bytes())


def semantic_json(old,new,maximum,path='row'):
    """Every original financial field remains present and numerically equivalent."""
    if isinstance(old,dict):
        engine.need(isinstance(new,dict) and set(old)<=set(new),'Semantic fields '+path)
        for key,value in old.items():semantic_json(value,new[key],maximum,path+'.'+key)
    elif isinstance(old,list):
        engine.need(isinstance(new,list) and len(old)==len(new),'Semantic list length '+path)
        for i,(a,b) in enumerate(zip(old,new,strict=True)):semantic_json(a,b,maximum,path+f'[{i}]')
    elif isinstance(old,(int,float)) and not isinstance(old,bool):
        engine.need(isinstance(new,(int,float)) and math.isfinite(old) and math.isfinite(new),'Finite ledger '+path)
        tolerance=RATIO_TOL if any(k in path for k in ('rate_fraction','conditional_rate_scale','weight')) else CASH_TOL
        delta=abs(old-new);maximum['ratio' if tolerance==RATIO_TOL else 'cash']=max(
            maximum['ratio' if tolerance==RATIO_TOL else 'cash'],delta)
        engine.need(delta<=tolerance,'Semantic numeric mismatch '+path)
    elif isinstance(old,str) and '.decimal_strings.' in path:
        a,b=Decimal(old),Decimal(new)
        engine.need(a.is_finite() and b.is_finite() and abs(a-b)<=Decimal(str(CASH_TOL)),
                    'Exact-decimal finance tolerance '+path)
    else:engine.need(old==new,'Semantic identity mismatch '+path)


def migration_pair(old,new):
    errors=dict(cash=0.,ratio=0.)
    a,b=payload(old,'minute_nav_inventory.parquet'),payload(new,'minute_nav_inventory.parquet')
    engine.need(a.height==b.height==436320 and set(a.columns)<=set(b.columns),'Full303D minute columns')
    for col in a.columns:
        if col=='close_us':engine.need(a[col].equals(b[col]),'Same exact minute clock');continue
        av,bv=a[col].to_numpy(),b[col].to_numpy()
        engine.need(np.isfinite(av).all() and np.isfinite(bv).all(),'Finite saved minute ledger')
        delta=float(np.max(np.abs(av-bv)));ratio='weight' in col
        errors['ratio' if ratio else 'cash']=max(errors['ratio' if ratio else 'cash'],delta)
        engine.need(delta<=(RATIO_TOL if ratio else CASH_TOL),'Minute ledger semantic mismatch '+col)
    del a,b;gc.collect()
    a,b=payload(old,'targets.parquet'),payload(new,'targets.parquet')
    engine.need(a.height==b.height==3636 and set(a.columns)<=set(b.columns),'Every ordered4h target')
    for col in a.columns:
        av,bv=a[col],b[col]
        engine.need(av.is_null().equals(bv.is_null()),'Same target nullable identity')
        if av.dtype.is_numeric() and col!='available_us':
            usable=~av.is_null();aa,bb=av.filter(usable).to_numpy(),bv.filter(usable).to_numpy()
            engine.need(np.isfinite(aa).all() and np.isfinite(bb).all(),'Finite target values')
            delta=float(np.max(np.abs(aa-bb))) if len(aa) else 0.
            ratio='target' in col and 'quantity' not in col
            errors['ratio' if ratio else 'cash']=max(errors['ratio' if ratio else 'cash'],delta)
            engine.need(delta<=(RATIO_TOL if ratio else CASH_TOL),'Target semantic mismatch '+col)
        else:engine.need(av.equals(bv),'Target clock/product/direction mapping')
    for name in ('trades.json','funding.json'):
        semantic_json(payload(old,name),payload(new,name),errors,name)
    for key in ('NAV','free_cash','isolated_balance','net_PnL','gross_PnL_same_quantities',
                'realized_PnL','unrealized_PnL','fees_USDT','execution_cost_USDT','funding_USDT','positions'):
        semantic_json(old['summary'][key],new['summary'][key],errors,'summary.'+key)
    return dict(cost_id=new['cost_id'],unit_id=new['unit_id'],maximum_errors=errors,
        full_minutes_verified=436320,ordered_target_rows_verified=3636,
        old_account_replayed=False,account_version_bytes_equal_claim=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('protocol','control','treatment','output','run-dir'):parser.add_argument('--'+arg,type=Path,required=True)
    parser.add_argument('--kind',choices=('migration','pyramiding'),required=True)
    args=parser.parse_args();began=time.monotonic();spec=engine.small(args.protocol)
    engine.need(os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2'),
                'Bounded accepted comparison runtime')
    for p,h in spec['source_hashes'].items():engine.need(engine.sha(ROOT/p)==h,'Current comparison source '+p)
    run=args.run_dir.resolve();out=args.output.resolve()
    engine.need(run.is_relative_to(STATE) and not run.exists() and out.is_relative_to(ROOT/'reports')
        and not out.exists(),'Exclusive small comparison artifacts')
    controls,treatments=engine.small(args.control),engine.small(args.treatment)
    closed(controls['binding']['task_id']);closed(treatments['binding']['task_id'])
    engine.need(treatments['status']=='COMPLETE_D060_FOUR_FIXED303D_TURTLE_VARIANT_NOT_NATIVE_OR_APR'
        and treatments['completed_cases']==4,'New complete variant')
    if args.kind=='migration':
        engine.need(engine.sha(args.control)==spec['saved_original']['sha256']
            and treatments['variant']=='PYRAMID4','Saved original vs new default, never noADD before compatibility')
        old_cases=[c for c in controls['cases'] if c['mode']=='LONG_ONLY']
    else:
        engine.need(controls['status']==treatments['status'] and controls['variant']=='PYRAMID4'
            and treatments['variant']=='SINGLE_LAYER'
            and controls['binding']['protocol_sha256']==treatments['binding']['protocol_sha256']==engine.sha(args.protocol)
            and controls['binding']['source_hashes']==treatments['binding']['source_hashes'],
            'Only ADD policy changes in the same new normal financial loop')
        old_cases=controls['cases']
    indexed={(c['cost_id'],c['unit_id']):c for c in old_cases}
    engine.need(len(indexed)==4 and len(treatments['cases'])==4,'Four complete cost/unit pairs')
    run.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],command=[sys.executable,*sys.argv],
        protocol_sha256=engine.sha(args.protocol),control_sha256=engine.sha(args.control),
        treatment_sha256=engine.sha(args.treatment),source_sha256=engine.sha(__file__))
    engine.write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS)
    event.update(event_id=spec['experiment_id']+':'+args.kind+':START',event_type='OPERATIONAL_RESEARCH_START',
        experiment_id=spec['experiment_id']+':'+args.kind,git_commit=spec['parent_commit'],
        protocol_hash=binding['protocol_sha256'],data_manifest_hash=spec['input_manifest']['sha256'],
        source_hashes={str(args.protocol):binding['protocol_sha256']},feature_set='SAVED_TURTLE_SEMANTIC_OR_COST_PATH',
        labels='NONE',model_family='NONE',hyperparameters=dict(kind=args.kind),seed=None,
        thresholds=dict(cash_USDT=CASH_TOL,ratio=RATIO_TOL),cost_assumptions=spec['cost_scenarios'],
        all_folds='SEEN_DEVELOPMENT_FIXED303D',fits=0,success_failure='START_BEFORE_SAVED_PAYLOAD_COMPARE',
        reason_for_next_experiment=spec['question'],result_influenced_later_choice='NONE_BEFORE_RESULTS')
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    pairs=[]
    for new in treatments['cases']:
        old=indexed[(new['cost_id'],new['unit_id'])]
        if args.kind=='migration':pairs.append(migration_pair(old,new));continue
        old_diag=diagnostic.diagnose_case(payload(old,'trades.json'),payload(old,'target_meta.json'),
            old['summary'],payload(old,'funding.json'))
        new_diag=diagnostic.diagnose_case(payload(new,'trades.json'),payload(new,'target_meta.json'),
            new['summary'],payload(new,'funding.json'))
        engine.need(new_diag['mapping']['UNKNOWN_legs']==0,'No guessed treatment order-reason contribution')
        engine.need(all(r['reason']!='ADD' or r['legs']==0 for r in new_diag['reason_totals']),
                    'No proactive ADD execution in the single-layer account')
        keys=('net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT',
            'gross_fill_turnover_USDT','minute_max_drawdown','normalized_total_turnover')
        pairs.append(dict(cost_id=new['cost_id'],unit_id=new['unit_id'],
            delta={k:new['summary'][k]-old['summary'][k] for k in keys},
            control_summary=old['summary'],treatment_summary=new['summary'],
            control_order_diagnostic=old_diag,treatment_order_diagnostic=new_diag,
            realized_risk_matched=False,change_is_full_strategy_path_not_deleted_fees=True))
    result=dict(status=('PASS_D060_DEFAULT_SEMANTIC_MIGRATION_NOT_NEW_ALPHA' if args.kind=='migration'
        else 'COMPLETE_D060_SAME_LOOP_NO_ADD_ECONOMIC_COMPARISON_NOT_APR'),
        task_id=os.environ['COIN_TASK_ID'],binding=binding,kind=args.kind,pairs=pairs,actual_days=303,
        initial_capital_USDT=10000,CASH_net_PnL_USDT=0,old_accounts_replayed=False,models_fit=0,HPO=0,
        funding_unit_certified=False,native_certified=False,candidate='NONE',investment='CASH',
        long_term_APR='NOT_EVALUABLE',elapsed_seconds=time.monotonic()-began,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        tolerances=dict(cash_USDT=CASH_TOL,ratio=RATIO_TOL))
    engine.write(out,result)
    append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,
        event_id=spec['experiment_id']+':'+args.kind+':RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',
        success_failure=result['status'],actual_exit_code=0,report_path=str(out),report_sha256=engine.sha(out)))
    print(json.dumps(dict(status=result['status'],pairs=len(pairs),elapsed_seconds=result['elapsed_seconds'])),flush=True)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        # Preserve a real mismatch before any treatment run; never amend the control.
        output=Path(sys.argv[sys.argv.index('--output')+1]).resolve()
        failure=dict(status='FAIL_D060_SAVED_TURTLE_COMPARE',task_id=os.environ.get('COIN_TASK_ID'),
            actual_exit_code=1,error_type=type(error).__name__,reason=str(error),market_accounts=0,
            old_accounts_replayed=False,command=[sys.executable,*sys.argv],candidate='NONE')
        if output.is_relative_to(ROOT/'reports') and not output.exists():engine.write(output,failure)
        print(json.dumps(failure),flush=True)
        raise SystemExit(1)
