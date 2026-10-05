import hashlib,json
from pathlib import Path
from quant.paths import ROOT
p=ROOT/'protocols/SPOT_LATER_DEVELOPMENT_20261005_V2.json';v=json.loads(p.read_bytes());base=v['common']
h=ROOT/'reports/fast_research/SPOT_LATER_HOLD8_20261005_V1.json';control=json.loads(h.read_bytes())
assert control['actual_calendar_days']==90 and len(control['cases'])==2
base.update(module='D082_BLEND',experiment_id='D082_LATER_BLEND',annual_vol_target=.10,recipe='HALF_HOLD10_EXIT10',
 spot_source=control['spot_source'],spot_control=dict(path=str(h),sha256=hashlib.sha256(h.read_bytes()).hexdigest()))
with (ROOT/'protocols/SPOT_LATER_BLEND_20261005_V1.json').open('x') as f:json.dump(base,f,indent=2);f.write('\n')
print('PREDECLARED_BLEND_RESOLVED_WITH_ACTUAL_CONTROL_SHA')
