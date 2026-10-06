"""Read-only actual-process and source-clock samples; no continuity promotion."""
import argparse,hashlib,json,os
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from quant import collector_public_v3 as public,resources
from quant.microstructure import read_microstructure_status
ap=argparse.ArgumentParser();ap.add_argument('--preservation',required=True);ap.add_argument('--output',required=True);ap.add_argument('--prior-sample');a=ap.parse_args()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=(ROOT/a.output).resolve();assert out.is_relative_to(ROOT/'reports') and not out.exists()
pres=json.loads((ROOT/a.preservation).read_bytes());backup=Path(pres['backup_directory']);before=json.loads((backup/'AUDIT_BEFORE_RESTART.json').read_bytes())
processes=[]
for p in Path('/proc').iterdir():
    if not p.name.isdecimal():continue
    try:
        argv=[v.decode() for v in (p/'cmdline').read_bytes().split(b'\0') if v]
        if argv and argv[0]==str(ROOT/'.venv/bin/python') and '-m' in argv and argv[argv.index('-m')+1] in ('quant.collector_public_v3','quant.microstructure'):
            processes.append(dict(pid=int(p.name),argv=argv,start_ticks=int((p/'stat').read_text().split(') ',1)[1].split()[19]),cgroup=(p/'cgroup').read_text().strip()))
    except (OSError,UnicodeError,IndexError):pass
assert len(processes)==2 and all('coin-quant.slice' in v['cgroup'] for v in processes)
pub=public.read_public_v3_status(STATE/'collector_public_v3_20261006.sqlite3');micro=read_microstructure_status()
assert pub['stored_source_matches_current'] and pub['contract']==before['public_contract'] and micro['binding']==before['microstructure']['binding']
assert micro['checkpoint']['session']!=before['microstructure']['checkpoint']['session']
r=dict(status='SAMPLED_RESTORED_ORIGINAL_COLLECTORS_NO_CONTINUITY_CLAIM',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),processes=processes,public=pub,microstructure=micro,resources=resources.status(),created_utc=datetime.now(UTC).isoformat(),exit_cause='UNKNOWN',healthy_gap_splicing=False,qualification=False)
if a.prior_sample:
    prior=json.loads((ROOT/a.prior_sample).read_bytes());assert [(v['pid'],v['start_ticks']) for v in processes]==[(v['pid'],v['start_ticks']) for v in prior['processes']]
    delta=dict(public_heartbeat_ms=pub['session']['heartbeat_ms']-prior['public']['session']['heartbeat_ms'],micro_events=micro['checkpoint']['accepted_events']-prior['microstructure']['checkpoint']['accepted_events'],micro_asof_us=micro['checkpoint']['asof_us']-prior['microstructure']['checkpoint']['asof_us'])
    assert pub['state']=='RUNNING' and micro['state']=='CONNECTED' and all(v>0 for v in delta.values());r['sample_delta']=delta
with out.open('x') as f:json.dump(r,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(dict(status=r['status'],public=pub['state'],micro=micro['state'],delta=r.get('sample_delta'))))
