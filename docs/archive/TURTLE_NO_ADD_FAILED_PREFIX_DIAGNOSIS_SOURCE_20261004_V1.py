"""Independent recorded-prefix finance and five failed capacity attempts only."""
from datetime import UTC,datetime
from decimal import Decimal as D,ROUND_DOWN,localcontext
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
    assert p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    return json.loads(p.read_bytes())
def load(name,h,id):
    p=ROOT/name;assert sha(p)==h
    spec=importlib.util.spec_from_file_location(id,p);v=importlib.util.module_from_spec(spec);sys.modules[id]=v;spec.loader.exec_module(v);return v
started=time.monotonic();id=os.environ['COIN_TASK_ID'];owner=STATE/'d060-turtle-failed-prefix-financial-20261004-v1';owner.mkdir()
spec=read(ROOT/'protocols/TURTLE_NO_ADD_RESEARCH_20261004_V1.json')
for p,h in spec['source_hashes'].items():assert sha(ROOT/p)==h
actualpath=ROOT/'reports/fast_research/TURTLE_NO_ADD_SINGLE_LAYER_303D_20261004_V1.json'
a=read(actualpath);t=read(STATE/'task-progress'/('task-'+a['binding']['task_id']+'.json'))
assert a['status']=='FAILED_D060_TURTLE_VARIANT' and a['completed_cases']==1 and t['status']=='failed' and t['exit_code']==1
case=a['cases'][0]; assert case['summary']['completion']=='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION'
assert case['summary']['completed_minutes']==83285 and case['summary']['required_minutes']==436320
binding=dict(task_id=id,actual_report_sha256=sha(actualpath),source_hashes=spec['source_hashes'],
    source_sha256=sha(Path(__file__)),command=[sys.executable,*sys.argv],failed_producer_task_id=t['id'])
(owner/'RUN_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
event=dict.fromkeys(FIELDS);event.update(experiment_id=owner.name,event_id=owner.name+':START',event_type='OPERATIONAL_RESEARCH_START',
    protocol_hash=sha(ROOT/'protocols/TURTLE_NO_ADD_RESEARCH_20261004_V1.json'),source_hashes={str(actualpath.relative_to(ROOT)):sha(actualpath)},
    success_failure='START_BEFORE_FAILED_PREFIX_FINANCIAL',reason_for_next_experiment='Explain actual risk exit failure without promoting a prefix',
    result_influenced_later_choice=False)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
mature=load('scripts/investment/multi_asset_financial_audit.py','4568a8c6f1c7c8c0ff04e6631420210575a791f4d17e482f88a885b14d0e4666','d060_prefix_finance')
base,financial,derivation=mature.prepare_financial(('BTCUSDT','ETHUSDT'))
date=load('docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py','356086d2534539dba0aecf04b1e716d39ec1f5bb5e1c5817b80affdb38d36b31','d060_prefix_reader')
_,reader,readerproof=date.prepare_financial_adapter()
manifest=read(ROOT/spec['input_manifest']['path']);assert sha(ROOT/spec['input_manifest']['path'])==spec['input_manifest']['sha256']
w=reader(manifest,manifest['windows'][0]);g=base.module(base.GUARD,'d060_prefix_guards',base.GUARD_SHA)
hand=base.module(base.REFERENCE,'d060_prefix_hand',base.REFERENCE_SHA);errors=dict(cash=0.,ratio=0.)
verified=financial(w,case,g,hand,Path(a['run_dir']),None,[],errors)
assert verified['complete_calendar_verified'] is False
rejections=read(Path(case['artifacts']['rejections.json']['path']));assert sha(Path(case['artifacts']['rejections.json']['path']))==case['artifacts']['rejections.json']['sha256']
attempts=[r for r in rejections if r.get('order_id')=='BTCUSDT:RISK_REDUCTION:175'];assert len(attempts)==5
rows=[]
with localcontext() as ctx:
    ctx.prec=40
    for row in attempts:
        i=(row['event_us']-1-w['start'])//60000000
        quote=D(str(w['market']['BTCUSDT']['quote'][i-1]));mid=D(str(w['market']['BTCUSDT']['open'][i]))
        available=quote*D('.001')/mid;rounded=(available/D('1e-8')).to_integral_value(rounding=ROUND_DOWN)*D('1e-8')
        rows.append(dict(event_us=row['event_us'],event_utc=datetime.fromtimestamp(row['event_us']/1e6,UTC).isoformat(),
            previous_completed_minute_quote_USDT=str(quote),execution_trade_open=str(mid),capacity_base=str(available),
            step_floored_capacity=str(rounded),actual_requested_quantity=row['decimal_strings']['requested_quantity'],
            actual_executed_quantity=row['decimal_strings']['executed_quantity'],actual_reason=row['reason']))
result=dict(status='PASS_D060_FAILED_PREFIX_RECORDED_FINANCE_AND_CAPACITY_DIAGNOSIS_NOT_FULL_PERIOD_COMPARE',
 binding=binding,run_dir=str(owner),recorded_financial_result=verified,maximum_errors=errors,
 financial_calls=1,complete_calendar=False,completed_minutes=83285,required_minutes=436320,
 full_period_net_delta='NOT_EVALUABLE',long_term_APR='NOT_EVALUABLE',candidate='NONE',investment='CASH',
 market_QA_or_new_account_calls=0,failed_capacity_attempts=rows,financial_derivation=derivation,reader_derivation=readerproof,
 pending_positions=case['summary']['positions'],marked_prefix_summary=case['summary'],
 elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
 shared_resources=resources.status(),resource_budget=dict(wall_seconds=1800,peak_RSS_bytes=1500000000))
assert result['elapsed_seconds']<1800 and result['peak_RSS_bytes']<1500000000
out=ROOT/'reports/fast_research/TURTLE_NO_ADD_FAILED_PREFIX_DIAGNOSIS_20261004_V1.json'
with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=owner.name+':RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',
    success_failure=result['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
print(json.dumps(dict(status=result['status'],maximum_errors=errors,failed_capacity_attempts=rows)),flush=True)
