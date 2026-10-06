import json,subprocess,sys,os
from datetime import UTC,datetime
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
name='reports/SMA200_REVIEW_COMPATIBILITY_SHORT50_20261006_V1.json'
subprocess.run([sys.executable,'-B','scripts/investment/review_short_cycle.py',
    '--producer','reports/fast_research/SMA200_FIXED_CYCLE_DIRECTIONS_20261006_V1.json',
    '--producer','reports/fast_research/SMA200_FIXED_CYCLE_LONG_SHORT_20261006_V1.json',
    '--strategy','SMA200_SIGNED','--output',name],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
old=ROOT/'reports/SMA200_FIXED_CYCLE_REVIEW_20261006_V1.json';new=ROOT/name
a=json.loads(old.read_bytes());b=json.loads(new.read_bytes())
assert a['rows']==b['rows'] and a['decisions']==b['decisions'] and a['decision']==b['decision']
result=dict(status='PASS_SMA200_OLD_ROWS_AND_PREDECLARED_DECISION_UNCHANGED',task_id=os.environ['COIN_TASK_ID'],
    source_sha256=sha(__file__),old_report_sha256=sha(old),new_report_sha256=sha(new),
    created_utc=datetime.now(UTC).isoformat(),new_accounts=0,fits=0)
with (ROOT/'reports/SMA200_REVIEW_DEFAULT_GOLDEN_SHORT50_20261006_V1.json').open('x') as f:
    json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(status=result['status'])))
