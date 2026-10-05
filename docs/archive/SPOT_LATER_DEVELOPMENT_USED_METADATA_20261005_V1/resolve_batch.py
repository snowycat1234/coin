import hashlib,json,subprocess
from pathlib import Path
from quant.paths import ROOT,STATE
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
p=ROOT/'protocols/SPOT_LATER_DEVELOPMENT_20261005_V1.json';old=json.loads(p.read_bytes())
for n in old['common']['source_hashes']:old['common']['source_hashes'][n]=sha(ROOT/n)
old['superseded_unrun_template']=dict(path=str(p),sha256=sha(p),reason='Source-metadata V1 stopped before accounts; missing old size field adapted using current accepted-byte SHA')
source=ROOT/old['source_output'];assert json.loads(source.read_bytes())['status']=='PASS_ACCEPTED_SPOT_SOURCE_WINDOW_REUSED_QA_CURRENT_BYTES'
base=old['common'];base['spot_source']=dict(path=str(source),sha256=sha(source))
save(ROOT/'protocols/SPOT_LATER_DEVELOPMENT_20261005_V2.json',old)
base['module']='D082_HOLD8';base['experiment_id']='D082_LATER_HOLD8'
save(ROOT/'protocols/SPOT_LATER_HOLD8_20261005_V1.json',base)
py='/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python';prefix=[py,'-B'];run=STATE/'d082-later-spot-20261005-v1'
run.mkdir()
names=dict(HOLD8='SPOT_LATER_HOLD8_20261005_V1',BLEND='SPOT_LATER_BLEND_20261005_V1')
steps=[dict(title='HOLD8两个完整后段账户',argv=prefix+['scripts/investment/spot_perpetual_product_comparison.py','--protocol','protocols/'+names['HOLD8']+'.json','--run-dir',str(run/'hold'),'--output','reports/fast_research/'+names['HOLD8']+'.json']),
 dict(title='仅解析事前固定挑战者来源引用',argv=prefix+['.cache/d082_resolve_challenger.py']),
 dict(title='日线防御组合两个完整后段账户',argv=prefix+['scripts/investment/spot_perpetual_product_comparison.py','--protocol','protocols/'+names['BLEND']+'.json','--run-dir',str(run/'blend'),'--output','reports/fast_research/'+names['BLEND']+'.json'])]
for label,name in names.items():
    inp='reports/fast_research/'+name+'.json'
    steps.extend([dict(title=label+'独立金额与完整分钟风险',argv=prefix+['docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py','--input',inp,'--output',str(run/(label+'_FINANCIAL.json'))]),
      dict(title=label+'独立日信号和协方差核验',argv=prefix+['scripts/investment/audit_daily_spot_targets.py','--input',inp,'--output',str(run/(label+'_TARGETS.json'))])])
steps.append(dict(title='真实账本资产月份连续资金桥',argv=prefix+['scripts/investment/spot_saved_economic_diagnostics.py','--input','reports/fast_research/'+names['BLEND']+'.json','--output',str(run/'DIAGNOSTIC.json')]))
save(ROOT/'.cache/d082_batch.json',dict(steps=steps))
print('FIXED_4_WALLETS_AND_REQUIRED_REFERENCES_BATCH_READY')
