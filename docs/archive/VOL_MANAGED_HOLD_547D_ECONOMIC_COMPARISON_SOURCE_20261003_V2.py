"""Unrun D034 metadata-only comparison V2; no ledger/price arrays or replay.

Frozen --binding JSON: comparator_sha256; protocol/actual/audit each
{path,sha256}, with actual/audit also task_id. Only the ROOT small reports below
are permitted. Binding is frozen after actual+audit closed0; strict descriptive
Pareto criteria below are fixed before results. Ordinary wrapper supplies task.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, shlex, sys
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
from quant.paths import ROOT, STATE

VM='VOL_MANAGED_BUY_AND_HOLD'
PUBLIC=('COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER','COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER')
ACTUAL='reports/fast_research/VOL_MANAGED_HOLD_547D_ACTUAL_20261003_V1.json'
AUDIT='reports/fast_research/VOL_MANAGED_HOLD_547D_INDEPENDENT_AUDIT_20261003_V1.json'
AUDIT_STATUS='PASS_D034_SINGLE_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
OLD='reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json'
OLD_SHA='c70e3011f74ddbbbf250316bb2cad9a02d2bd6945b266a1a96a1083b9fcbc6e8'
OLD_AUDIT='reports/fast_research/PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json'
OLD_AUDIT_SHA='c7033ef299071f1d3149381fc19d923487bbbdd1040c4b20c75481058203441d'
OLD_ROOT='reports/fast_research/PUBLIC_LONG_547D_ROOT_ACCEPTANCE_20261003_V1.json'
OLD_ROOT_SHA='3c34b9b01b84d2febc6692e8d0d310ce2f416ade0b1a7006b434c176ef03f76c'
OUT=ROOT/'reports/fast_research/VOL_MANAGED_HOLD_547D_ECONOMIC_COMPARISON_20261003_V1.json'
STATUS='COMPLETE_D034_SAVED_SUMMARY_RISK_COST_COMPARISON_NOT_LONG_TERM_APR'
MONTHS=[f'2024-{m:02d}' for m in range(1,13)]+[f'2025-{m:02d}' for m in range(1,7)]
METRICS=('net_cash_PnL','gross_cash_PnL_same_quantities','fees','spread_cost','slippage_cost','turnover',
 'period_net_return','period_descriptive_net_CAGR','annual_volatility','max_observed_minute_MDD',
 'max_drawdown','sharpe','terminal_marked_notional','trade_count','max_minute_marked_gross_weight',
 'max_minute_BTC_weight','max_minute_ETH_weight','terminal_positions_flat','open_positions')
PARETO_RULE=dict(net_PnL='NEW_GE_REFERENCE',actual_annual_vol='NEW_LE_REFERENCE',minute_MDD='NEW_LE_REFERENCE',
 at_least_one_strict=True,numerical_tolerance_or_significance_band=None,cash_excluded_from_dominance_claim=True)

def require(ok,reason):
    if not ok:raise ValueError(reason)

def small(path,digest=None):
    original=Path(path);path=original.resolve()
    require(not original.is_symlink() and path.is_file() and path.stat().st_size<2_000_000
        and (path.is_relative_to(ROOT) or path.is_relative_to(STATE)) and path.suffix in ('.json','.py'),'Ordinary small JSON/source only')
    data=path.read_bytes();actual=hashlib.sha256(data).hexdigest();require(digest is None or actual==digest,'Frozen small proof changed')
    return (json.loads(data) if path.suffix=='.json' else None),actual

def closed(report,expected_id):
    identity=report['binding']['task_id'];require(identity==expected_id and len(identity)==32 and all(x in '0123456789abcdef' for x in identity),'Exact task identity')
    path=STATE/'task-progress'/('task-'+identity+'.json');task,digest=small(path)
    require(task['id']==identity and task['status']=='completed' and task['exit_code']==0,'Real completed0 before comparison')
    for key in ('started_at','ended_at'):require(type(task[key]) in (int,float) and math.isfinite(task[key]),'Real Unix task times')
    return dict(path=str(path),sha256=digest,task=task)

def near(left,right,tolerance):
    left,right=float(left),float(right);require(math.isfinite(left) and math.isfinite(right) and abs(left-right)<=tolerance,'Saved summary differs from independent audit')

def exact_actual_report_map(mapping,digest):
    require(isinstance(mapping,dict) and len(mapping)==1,'Exactly one independently bound new actual report')
    key,value=next(iter(mapping.items()));require(isinstance(key,str),'Ordinary report path key')
    path=Path(key);path=path if path.is_absolute() else ROOT/path
    require(path.resolve()==(ROOT/ACTUAL).resolve() and value==digest,'Canonical key must be the exact fixed ROOT actual report and SHA')

def dominates(new,old):
    return (new['net_cash_PnL']>=old['net_cash_PnL'] and new['annual_volatility']<=old['annual_volatility']
        and new['max_observed_minute_MDD']<=old['max_observed_minute_MDD'] and
        (new['net_cash_PnL']>old['net_cash_PnL'] or new['annual_volatility']<old['annual_volatility']
            or new['max_observed_minute_MDD']<old['max_observed_minute_MDD']))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binding',type=Path,required=True)
    parser.add_argument('--run-dir',type=Path,required=True);parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args()
    work,out=args.run_dir.resolve(),args.output.resolve();task_id=os.environ.get('COIN_TASK_ID')
    require(task_id and work.is_relative_to(STATE) and not work.exists() and out==OUT.resolve() and not out.exists(),'Exclusive bounded/progress STATE task and report')
    runtime=resources.status();require(runtime['ram_limit_bytes']<=5_000_000_000 and runtime['swap_bytes']==0 and not runtime['gpu_used'],'Shared5GB/swap0/noGPU')
    binding_path=args.binding.resolve();require(binding_path.is_relative_to(ROOT/'protocols'),'Root-frozen comparison binding')
    binding,binding_sha=small(binding_path);_,own_sha=small(__file__,binding['comparator_sha256'])
    proto_path=binding['protocol']['path'];version=re.fullmatch(r'protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V([1-9][0-9]*)\.json',proto_path)
    require(version is not None and int(version.group(1))>=2,'Root-frozen corrected protocol version; failed V1 remains excluded')
    reports={}
    for role,path in [('protocol',proto_path),('actual',ACTUAL),('audit',AUDIT)]:
        require(binding[role]['path']==path,'Only fixed D034 input role');reports[role]=small(ROOT/path,binding[role]['sha256'])[0]
    spec,new,audit=reports['protocol'],reports['actual'],reports['audit']
    require(new['binding']['protocol_sha256']==binding['protocol']['sha256']
        and new['binding']['source_hashes'][proto_path]==binding['protocol']['sha256']
        and all(new['binding']['source_hashes'][name]==digest for name,digest in spec['frozen_sources'].items())
        and Path(sys.prefix).resolve()==Path(spec['environment']['sys_prefix']).resolve(),'Exact executed new protocol/source/environment binding')
    old,_=small(ROOT/OLD,OLD_SHA);old_audit,_=small(ROOT/OLD_AUDIT,OLD_AUDIT_SHA);old_root,_=small(ROOT/OLD_ROOT,OLD_ROOT_SHA)
    require(new['status']==old['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and new['completed_ledgers']==new['planned_ledgers']==1
        and new['all_planned_ledgers_complete'] and old['all_planned_ledgers_complete'] and old['completed_ledgers']==3,'Only one complete new account plus three saved references')
    exact_actual_report_map(audit['binding']['actual_reports'],binding['actual']['sha256'])
    require(audit['status']==AUDIT_STATUS and audit['completed_ledgers_verified']==1 and audit['actual_report_sha256']==binding['actual']['sha256']
        and audit['verified_source_hashes']==new['binding']['source_hashes'],'New independently accepted exact actual inputs')
    require(old_root['status']=='PASS_ROOT_D033_547D_THREE_ACCOUNT_SAVED_SUMMARY_METADATA_NOT_NATIVE_OR_LONG_TERM_APR'
        and old_root['small_reports'][OLD]==OLD_SHA and old_root['small_reports'][OLD_AUDIT]==OLD_AUDIT_SHA
        and old_audit['completed_ledgers_verified']==3,'Saved D033 acceptance, no old financial validation replay')
    require(spec['strategy_ids']==new['binding']['strategies']==[VM] and spec['planned_ledgers']==1 and spec['costs']==new['registration_start']['cost_assumptions']==old['registration_start']['cost_assumptions']
        and spec['common_config']==new['registration_start']['hyperparameters']==old['registration_start']['hyperparameters'],'Same preset one-cost/risk/capital contract')
    for key in ('source_receipt_sha256','source_days_per_symbol','source_scope','source_calendar','source_month_files','fee_settlement','fee_profile_sha256'):
        require(new[key]==old[key],'Same accepted source/fee scope: '+key)
    require(spec['folds']==new['binding']['all_folds']==old['binding']['all_folds'] and len(new['folds'])==len(old['folds'])==1
        and new['minute_source']['rows']==old['minute_source']['rows']==1664640 and new['minute_source']['invalid_minutes']==0,'Same uninterrupted scoring and warmup input continuity')
    require(all(new['folds'][0][key]==old['folds'][0][key] for key in ('fold','start_us','end_us','days')),'Actual full scoring boundaries also match, not protocol labels alone')
    require(spec['reused_minute_input']==dict(report_path=OLD,report_sha256=OLD_SHA,path=old['minute_source']['path'],sha256=old['minute_source']['sha256'])
        and new['reused_minute_input']==spec['reused_minute_input'] and new['raw_normalized_market_files_read'] is False,'Reuse exact accepted parent Parquet, no 38-source reload')
    tasks={role:closed(reports[role],binding[role]['task_id']) for role in ('actual','audit')}
    require(tasks['actual']['task']['id']!=tasks['audit']['task']['id'] and tasks['audit']['task']['started_at']>=tasks['actual']['task']['ended_at'],'Distinct closed0 audit after actual')
    require(Path(new['run_dir']).resolve()!=Path(old['run_dir']).resolve(),'Independent accounts, no stitched account or old directory reuse')
    cases=[];summaries={}
    for actual,proof,report_path,report_sha,audit_path,audit_sha,expected in [(new,audit,ACTUAL,binding['actual']['sha256'],AUDIT,binding['audit']['sha256'],{VM}),
        (old,old_audit,OLD,OLD_SHA,OLD_AUDIT,OLD_AUDIT_SHA,{'CASH',*PUBLIC})]:
        fold=actual['folds'][0];require(fold['status']=='COMPLETE_PROXY_COMPARISON' and fold['days']==547 and len(fold['results'])==len(expected),'Full uninterrupted accounts')
        rows={r['strategy']:r for r in fold['results']};ledgers={r['strategy']:r for r in proof['ledgers']};require(set(rows)==set(ledgers)==expected,'Fixed exact account set')
        for strategy in sorted(expected):
            row,verified=rows[strategy],ledgers[strategy];summary=row['summary']
            require(row['spread_bps']==8 and row['nominal_roundtrip_bps']==36 and summary['initial_nav']==10000 and summary['period_days']==547
                and [m['month'] for m in verified['months']]==MONTHS and summary['annualized_return_is_descriptive_only']
                and not summary['candidate_qualification_allowed'] and not summary['native_Bybit_market_or_filters_proven'],'Saved complete same-cost accounting scope')
            if strategy==VM:
                for key,field,tol in [('net_cash_PnL','net_PnL',1e-7),('gross_cash_PnL_same_quantities','gross_PnL_same_quantities',1e-7),('fees','fees',1e-7),
                    ('max_observed_minute_MDD','minute_MDD',1e-10),('max_drawdown','daily_MDD',1e-10)]:near(summary[key],verified[field],tol)
            metrics={key:summary[key] for key in METRICS};summaries[strategy]=metrics
            cases.append(dict(strategy=strategy,period=fold['fold'],period_days=547,actual_report_path=report_path,actual_report_sha256=report_sha,
                audit_report_path=audit_path,audit_report_sha256=audit_sha,summary=metrics,months=verified['months']))
    pairs=[]
    for strategy in PUBLIC:
        vm,reference=summaries[VM],summaries[strategy];forward,reverse=dominates(vm,reference),dominates(reference,vm)
        pairs.append(dict(new_strategy=VM,reference_strategy=strategy,new_Pareto_dominates_reference=forward,reference_Pareto_dominates_new=reverse,
            net_PnL_delta_USDT=vm['net_cash_PnL']-reference['net_cash_PnL'],annual_volatility_delta=vm['annual_volatility']-reference['annual_volatility'],
            minute_MDD_delta=vm['max_observed_minute_MDD']-reference['max_observed_minute_MDD'],
            conclusion='NEW_DESCRIPTIVE_PARETO_DOMINANCE' if forward else 'REFERENCE_DESCRIPTIVE_PARETO_DOMINANCE' if reverse else 'NO_STRICT_PARETO_DOMINANCE_NO_SCALAR_WINNER'))
    require(new['market_models_fit']==new['orders_sent']==0 and not new['locked_consumed'] and new['source_bytes_unchanged'],'No model/order/locked or changed source')
    work.mkdir();own_binding=dict(task_id=task_id,source_sha256=own_sha,comparison_binding_path=str(binding_path),comparison_binding_sha256=binding_sha,
        protocol_sha256=binding['protocol']['sha256'],exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]))
    (work/'RUN_BINDING.json').write_text(json.dumps(own_binding,indent=2)+'\n')
    value=dict(status=STATUS,created_utc=datetime.now(UTC).isoformat(),binding=own_binding,actual_task_copies=tasks,
        source_hashes=new['binding']['source_hashes'],small_report_hashes={proto_path:binding['protocol']['sha256'],ACTUAL:binding['actual']['sha256'],AUDIT:binding['audit']['sha256'],OLD:OLD_SHA,OLD_AUDIT:OLD_AUDIT_SHA,OLD_ROOT:OLD_ROOT_SHA},
        cases=cases,pairs=pairs,predeclared_Pareto_rule=PARETO_RULE,both_public_descriptively_dominated=all(r['new_Pareto_dominates_reference'] for r in pairs),
        economic_action='SAVED_DEVELOPMENT_RISK_RETURN_COMPARISON_NO_INVESTMENT_ADOPTION',cash_dominance_claimed=False,
        same_caps_not_equal_realized_risk=True,annualization_and_ratios_descriptive_only=True,statistical_significance_established=False,all_event_drawdown_verified=False,
        old_financial_validation_replayed=False,source_QA_or_ledger_or_price_arrays_read=False,monthly_winners_or_accounts_concatenated=False,
        long_term_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE',native_account_certified=False,unseen_qualification=False,
        models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources=runtime)
    with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=STATUS,output=str(out),sha256=small(out)[1])))

if __name__=='__main__':main()
