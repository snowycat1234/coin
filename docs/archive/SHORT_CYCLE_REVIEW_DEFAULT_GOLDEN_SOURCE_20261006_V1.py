import json,os
from datetime import UTC,datetime
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
old=ROOT/'reports/SHORT_FIXED_CYCLE_REVIEW_20261006_V1.json'
new=ROOT/'reports/SHORT_CYCLE_REVIEW_COMPATIBILITY_20261006_V1.json'
a=json.loads(old.read_bytes());b=json.loads(new.read_bytes())
assert a['rows']==b['rows'] and a['decision']==b['decision']
for x,y in zip(a['decisions'],b['decisions']):
    assert x=={k:y[k] for k in x}
out=dict(status='PASS_OLD_REVIEW_ROWS_AND_PREDECLARED_DECISION_UNCHANGED',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    old_report_sha256=sha(old),new_report_sha256=sha(new),created_utc=datetime.now(UTC).isoformat(),new_accounts=0,fits=0,
    scope='EXACT_SAVED_ECONOMIC_RISK_CALENDAR_OWN_TREND_ROWS; SAME_DEFAULT_GATES; NOT_NEW_ACCOUNT_REGRESSION')
with (ROOT/'reports/SHORT_CYCLE_REVIEW_DEFAULT_GOLDEN_20261006_V1.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(dict(status=out['status'])))
