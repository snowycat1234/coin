"""Post-producer metadata only for four recorded D060 financial checks."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path

ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
CHECKER='scripts/investment/audit_turtle_direction_research.py'
CHECKER_SHA='caf54215bbe3480c0a7f0f364d8645b494ae310539f60c6ad287b754f7e6f2cf'
PROTOCOL='protocols/TURTLE_NO_ADD_RESEARCH_20261004_V1.json'
PROTOCOL_SHA='4a56a62a0054a7d8351abc0d7c644b66dfb7949531ab16fedac4d05fe7fdad22'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
    assert p.is_file() and not p.is_symlink() and p.stat().st_size<2_000_000
    return json.loads(p.read_bytes())
parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=('PYRAMID4','SINGLE_LAYER'),required=True)
parser.add_argument('--actual',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();taskid=os.environ['COIN_TASK_ID']
assert args.actual.parent==ROOT/'reports/fast_research' and args.output.parent==ROOT/'protocols' and not args.output.exists()
assert sha(ROOT/PROTOCOL)==PROTOCOL_SHA and sha(ROOT/CHECKER)==CHECKER_SHA
spec=read(ROOT/PROTOCOL); actual=read(args.actual)
assert actual['status']=='COMPLETE_D060_FOUR_FIXED303D_TURTLE_VARIANT_NOT_NATIVE_OR_APR'
assert actual['variant']==args.variant and actual['allow_pyramiding']==(args.variant=='PYRAMID4')
assert actual['actual_exit_code']==0 and actual['source_bytes_unchanged'] and actual['completed_cases']==4
producerid=actual['binding']['task_id']; task=read(STATE/'task-progress'/('task-'+producerid+'.json'))
caller=read(STATE/'task-progress'/('task-'+taskid+'.json'))
assert task['status']=='completed' and task['exit_code']==0 and task['ended_at']<=caller['started_at']
owner=Path(actual['run_dir']); assert owner.parent==STATE and not owner.is_symlink()
rb=owner/'RUN_BINDING.json'; assert read(rb)==actual['binding']
assert actual['binding']['protocol_sha256']==PROTOCOL_SHA and actual['binding']['source_hashes']==spec['source_hashes']
for p,h in spec['source_hashes'].items(): assert sha(ROOT/p)==h
plan=dict(ready_to_execute=True,checker_sha256=CHECKER_SHA,source_hashes=spec['source_hashes'],
    protocol_path=PROTOCOL,protocol_sha256=PROTOCOL_SHA,actual_report=str(args.actual.relative_to(ROOT)),
    actual_report_sha256=sha(args.actual),actual_task_id=producerid,metadata_task_id=taskid,
    producer_run_binding_sha256=sha(rb),required_variant=args.variant,allow_pyramiding=actual['allow_pyramiding'],
    case_ids=[c['id'] for c in actual['cases']],period_ids=['303D'],tolerances=dict(cash_USDT=1e-7,ratio=1e-10),
    budgets=dict(new_owned_bytes=100000,wall_seconds=1800,peak_RSS_bytes=1500000000),
    metadata_only=True,market_arrays_read=False,accounts_replayed=0,created_utc=datetime.now(UTC).isoformat())
with args.output.open('x') as f:json.dump(plan,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(plan=str(args.output),sha256=sha(args.output),variant=args.variant,market_arrays_read=False)),flush=True)
