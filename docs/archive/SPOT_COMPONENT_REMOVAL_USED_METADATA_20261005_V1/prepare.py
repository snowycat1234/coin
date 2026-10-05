import hashlib,json,subprocess
from pathlib import Path
from quant.paths import ROOT,STATE
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head=='8c93cc6b874757194e3931a82c0788829fad0bd7'
specs=[('ORIGINAL','protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json','reports/fast_research/SPOT_DEFENSIVE_BLEND_20261005_V1.json'),
 ('LATER','protocols/SPOT_LATER_BLEND_20261005_V1.json','reports/fast_research/SPOT_LATER_BLEND_20261005_V1.json')]
py='/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python';prefix=[py,'-B'];run=STATE/'d083-half-hold-component-20261005-v1';run.mkdir()
steps=[];protocol_refs={};results={}
for window,pn,rn in specs:
    c=read(ROOT/pn)
    for name in ('perpetual_report','economic_reference'):c.pop(name,None)
    c.update(parent_commit=head,module='D083_'+window,experiment_id='D083_HALF_HOLD10_'+window,recipe='HALF_HOLD10',
        question='What economic contribution does the fixed EXIT10 component add to its exact half-HOLD10 component wallet?',
        spot_control=dict(path=str(ROOT/rn),sha256=sha(ROOT/rn)),annual_vol_target=.10,
        comparison='One complete10k wallet with half past-risk HOLD10, versus existing same-date .5HOLD10+.5EXIT10. Removes signal component, not matched realized risk; independent windows never concatenated.',
        hypothesis='The later90-day zero EXIT10 component should produce no actual incremental economics; the original303-day active component may add net opportunity and risk. No prior assumption of positive signal contribution.',
        success_decision='Diagnostic control only. Explain full net/gross/cost and actual risk contribution in both windows/costs; no investment promotion, no threshold/period/risk grid.',
        budget=dict(actual_spot_wallets=2,wall_seconds=1200,owned_bytes=100000000,fits=0,HPO=0,downloads=0,API=0),
        stop_rule='Exactly four new wallets across two declared windows. Any source/target/cash/cap mismatch stops acceptance; preserve residual, no liquidation extension or old-NAV scaling.')
    c['source_hashes']={n:sha(ROOT/n) for n in c['source_hashes']}
    for n in ('scripts/investment/hold_donchian_blend_target.py','scripts/investment/audit_daily_spot_targets.py'):c['source_hashes'][n]=sha(ROOT/n)
    proto='protocols/SPOT_HALF_HOLD10_'+window+'_20261005_V1.json';out='reports/fast_research/SPOT_HALF_HOLD10_'+window+'_20261005_V1.json'
    save(ROOT/proto,c);protocol_refs[window]=dict(path=proto,sha256=sha(ROOT/proto));results[window]=out
    steps.extend([dict(title=window+'半份HOLD10完整两成本钱包',argv=prefix+['scripts/investment/spot_perpetual_product_comparison.py','--protocol',proto,'--run-dir',str(run/window),'--output',out]),
       dict(title=window+'独立资金费用和完整分钟风险',argv=prefix+['docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py','--input',out,'--output',str(run/(window+'_FINANCIAL.json'))]),
       dict(title=window+'独立半份目标/未来扰动',argv=prefix+['scripts/investment/audit_daily_spot_targets.py','--input',out,'--output',str(run/(window+'_TARGETS.json'))]),
       dict(title=window+'资产月份及连续资本诊断',argv=prefix+['scripts/investment/spot_saved_economic_diagnostics.py','--input',out,'--output',str(run/(window+'_DIAGNOSTIC.json'))])])
save(ROOT/'protocols/SPOT_COMPONENT_REMOVAL_20261005_V1.json',dict(parent_commit=head,
    question='Is defensive performance genuine incremental signal economics or just half-risk market exposure?',
    data_role='TWO_ALREADY_SEEN_DEVELOPMENT_WINDOWS_NOT_INDEPENDENT',protocols=protocol_refs,results=results,
    wallets=4,fits=0,HPO=0,API_calls=0,downloads=0,shared_full_capital=10000,abs_cap=.3,gross_cap=.6,
    scope='Full new wallets at each window, no concatenation, no fee removal or posthoc NAV scaling',
    funding_check='D076 already passed raw-chain sign/units-scaling accounting. Physical unit remains unconfirmed; existing403/451 not retried. No new archive-unit evidence from official README/API docs.',
    funding_source_reference=dict(path='docs/FUNDING_CHAIN_20261005.md',sha256=sha(ROOT/'docs/FUNDING_CHAIN_20261005.md'))))
save(ROOT/'.cache/d083_batch.json',dict(steps=steps))
print('FIXED_COMPONENT_REMOVAL_TWO_WINDOWS_FOUR_WALLETS_READY')
