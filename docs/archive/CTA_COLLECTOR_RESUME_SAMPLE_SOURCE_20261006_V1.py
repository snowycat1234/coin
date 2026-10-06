import hashlib,json,os,sys
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from quant import collector_public_v3 as public,resources
from quant.microstructure import read_microstructure_status

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
n=sys.argv[1];assert n in ('1','2')
procs=[]
for p in Path('/proc').iterdir():
    if not p.name.isdecimal():continue
    try:
        argv=(p/'cmdline').read_bytes().split(b'\0')
        if argv[0]==str(ROOT/'.venv/bin/python').encode() and b'-m' in argv and argv[argv.index(b'-m')+1] in (b'quant.collector_public_v3',b'quant.microstructure'):
            procs.append(dict(pid=int(p.name),argv=[v.decode() for v in argv if v],cgroup=(p/'cgroup').read_text().strip(),
                start_ticks=int((p/'stat').read_text().split(') ',1)[1].split()[19])))
    except OSError:pass
assert len(procs)==2 and all('coin-quant.slice' in p['cgroup'] for p in procs)
pub=public.read_public_v3_status(STATE/'collector_public_v3_20261006.sqlite3');micro=read_microstructure_status()
before=json.loads((STATE/'d099-interruption-preserved-20261006-v1/AUDIT_BEFORE_RESTART.json').read_bytes())
assert pub['stored_source_matches_current'] and micro['binding']==before['microstructure']['binding']
assert micro['checkpoint']['session']!=before['microstructure']['checkpoint']['session']
report=dict(status='SAMPLED_ORIGINAL_COLLECTORS_NEW_SESSIONS_NOT_CONTINUOUS_HEALTH',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    processes=procs,public=pub,microstructure=micro,resources=resources.status(),created_utc=datetime.now(UTC).isoformat(),
    exit_cause='UNKNOWN',qualification=False,healthy_gap_splicing=False)
if n=='2':
    prev=json.loads((ROOT/'reports/CTA_COLLECTOR_RESUME_SAMPLE_20261006_V1.json').read_bytes())
    assert [(p['pid'],p['start_ticks']) for p in procs]==[(p['pid'],p['start_ticks']) for p in prev['processes']]
    report['sample_delta']=dict(public_heartbeat_ms=pub['session']['heartbeat_ms']-prev['public']['session']['heartbeat_ms'],
        micro_events=micro['checkpoint']['accepted_events']-prev['microstructure']['checkpoint']['accepted_events'])
out=ROOT/('reports/CTA_COLLECTOR_RESUME_SAMPLE_20261006_V'+n+'.json')
with out.open('x') as f:json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
print(json.dumps(dict(status=report['status'],public=pub['state'],micro=micro['state'],delta=report.get('sample_delta'))))
