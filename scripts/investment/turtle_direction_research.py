"""Fixed Turtle LONG_ONLY proactive-ADD ablation with one shared account.

Two explicit policies use the same normal event strategy, financial engine,
accepted303D market, full capital, costs and mandatory reductions. No search.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import gc
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from quant import disk,resources
from quant.paths import ROOT,STATE
from scripts.investment import perpetual_directional as engine
from scripts.investment import turtle_perpetual_research as turtle
from scripts.research_v8.registry import FIELDS,append_event

CONTRACT='D060_FIXED303D_TURTLE_NO_ADD_CONDITIONAL_V1'
STATUS='COMPLETE_D060_FOUR_FIXED303D_TURTLE_VARIANT_NOT_NATIVE_OR_APR'
VARIANTS={'PYRAMID4':True,'SINGLE_LAYER':False}


def main():
    from scripts.research_v7.oracle_flow_ceiling import Progress
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--variant',choices=tuple(VARIANTS),required=True)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();spec=engine.small(args.protocol)
    engine.need(spec['contract_id']==CONTRACT and spec['direction_mode']=='LONG_ONLY'
        and spec['variants']==VARIANTS and spec['cost_scenarios']==engine.COSTS
        and spec['unit_scenarios']==engine.UNITS and spec['initial_capital_USDT']==10000,
        'Exactly one predeclared factor, four cost/unit conditions per shared-account policy')
    engine.need(os.environ.get('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2'),
                'Accepted bounded WSL runtime')
    run=args.run_dir.resolve();output=args.output.resolve()
    engine.need(run.is_relative_to(STATE) and not run.exists()
        and output.is_relative_to(ROOT/'reports') and not output.exists(),'Exclusive actual outputs')
    for name,value in spec['source_hashes'].items():
        engine.need(name!='state/dataset_lock.json' and engine.sha(ROOT/name)==value,'Current source '+name)
    engine.need(engine.sha(ROOT/'state/dataset_lock.json')==
        '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d','Private SHA-only guard')
    accepted=engine.relative_proof(spec['input_manifest'])
    warmup=engine.relative_proof(spec['warmup_acceptance'])
    engine.need(accepted['status']=='PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'
        and len(accepted['windows'])==1 and warmup['status']=='PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY',
        'Prior accepted complete303D and official4h source, not native qualification')
    window_spec=accepted['windows'][0]
    engine.need(int(datetime.fromisoformat(window_spec['start']).timestamp()*1000000)==1725148800000000
        and int(datetime.fromisoformat(window_spec['end_exclusive']).timestamp()*1000000)==1751328000000000
        and tuple(window_spec['symbols'])==('BTCUSDT','ETHUSDT'),'Original fixed two-asset303D control')
    receipt=engine.relative_proof(spec['required_test'])
    engine.need(receipt['status']=='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT'
        and receipt['test_exit_code']==0 and receipt['source_bytes_unchanged'] is True,
        'New direct event path and noADD necessary case before accounts')
    run.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],command=[sys.executable,*sys.argv],
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=engine.sha(args.protocol),source_hashes=spec['source_hashes'],
        input_manifest_sha256=spec['input_manifest']['sha256'],warmup_sha256=spec['warmup_acceptance']['sha256'],
        environment_lock_sha256=engine.sha(ROOT/'environments/v8/uv.lock'))
    engine.write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS)
    event.update(event_id=spec['experiment_id']+':'+args.variant+':START',event_type='OPERATIONAL_RESEARCH_START',
        experiment_id=spec['experiment_id']+':'+args.variant,git_commit=binding['git_commit'],
        protocol_hash=binding['protocol_sha256'],data_manifest_hash=binding['input_manifest_sha256'],
        source_hashes={str(args.protocol):binding['protocol_sha256']},feature_set='ORIGINAL_COMPLETED4H_TURTLE',
        labels='NONE',model_family='FIXED_RULE_NO_TRAINING',hyperparameters=dict(variant=args.variant,
        allow_pyramiding=VARIANTS[args.variant]),seed=None,thresholds='FIXED_NO_SEARCH',
        cost_assumptions=dict(costs=engine.COSTS,units=engine.UNITS),all_folds='SEEN_DEVELOPMENT_COMPLETE303D',
        fits=0,success_failure='START_BEFORE_NEW_ACCOUNTS',reason_for_next_experiment=spec['question'],
        result_influenced_later_choice='NONE_BEFORE_RESULTS')
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    result=dict(status='FAILED_D060_TURTLE_VARIANT',binding=binding,run_dir=str(run),variant=args.variant,
        allow_pyramiding=VARIANTS[args.variant],direction_mode='LONG_ONLY',strategy_id=turtle.STRATEGY_ID,
        cases=[],required_cases=4,completed_cases=0,actual_calendar_days=303,initial_capital_USDT=10000,
        one_shared_full_capital_wallet_per_scenario=True,target_exchange='Bybit_VIP0',
        price_funding_source='Binance_USDM_CROSS_VENUE_PROXY',funding_unit_certified=False,
        native_filters_certified=False,candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE',
        model_fits=0,HPO=0,new_downloads=0,source_QA_calls=0,orders_sent=0,locked_consumed=False,
        resources_before=resources.status())
    progress=Progress();began=time.monotonic();peak=result['resources_before']['ram_current_bytes'];code=1

    def guard():
        nonlocal peak
        r=resources.status();peak=max(peak,r['ram_current_bytes'])
        owned=sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
        engine.need(owned<=spec['budget']['owned_bytes'] and time.monotonic()-began<=spec['budget']['wall_seconds'],
                    'Finite output/wall budget reached')
        engine.need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=spec['budget']['peak_RSS_bytes'],
                    'Actual process RSS budget')

    try:
        progress.update('既有磁盘守卫；总扫描量未知',None,None,'扫描')
        result['disk_before']=disk.check(spec['budget']['owned_bytes'])
        progress.update('读取原已接受303日与4h预热；不重源QA',0,4,'账户')
        window=turtle.load_window(accepted,window_spec,warmup)
        result['accepted_input_files_read']=len(window['input_proofs'])
        result['input_proofs']=window['input_proofs']
        for cost in engine.COSTS:
            for unit in engine.UNITS:
                guard();case_id=args.variant+'-'+cost['id']+'-'+unit['id']
                actual=turtle.simulate(window,'LONG_ONLY',cost,unit,progress,guard,
                    allow_pyramiding=VARIANTS[args.variant])
                saved=engine.save_case(actual,run/case_id)
                result['cases'].append(dict(id=case_id,period='303D',mode='LONG_ONLY',variant=args.variant,
                    allow_pyramiding=VARIANTS[args.variant],strategy_id=turtle.STRATEGY_ID,
                    cost_id=cost['id'],unit_id=unit['id'],**saved))
                result['completed_cases']=len(result['cases'])
                engine.need(saved['summary']['completed_minutes']==436320
                    and saved['summary']['required_minutes']==436320
                    and saved['summary']['daily_metrics']['days']==303,'No prefix or deleted dates promoted')
                del actual;gc.collect();guard()
        result['status']=STATUS;code=0
    except Exception as error:
        result.update(error_type=type(error).__name__,reason=str(error))
    finally:
        result.update(actual_exit_code=code,elapsed_seconds=time.monotonic()-began,
            owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            shared_RAM_sampled_peak_bytes=peak,shared_peak_scope='SAMPLED_THIS_TASK_NOT_KERNEL_LIFETIME',
            resources_after=resources.status(),source_bytes_unchanged=all(
                engine.sha(ROOT/p)==h for p,h in spec['source_hashes'].items()))
        engine.write(output,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,
            event_id=spec['experiment_id']+':'+args.variant+':RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',
            success_failure=result['status'],actual_exit_code=code,report_path=str(output),report_sha256=engine.sha(output),
            reason_for_next_experiment=result.get('reason','Independent recorded finance and same-loop policy contrast')))
        progress.update('Turtle变体实际退出',len(result['cases']),4,'账户',actual_exit_code=code);progress.stop.set()
    return code


if __name__=='__main__':
    raise SystemExit(main())
