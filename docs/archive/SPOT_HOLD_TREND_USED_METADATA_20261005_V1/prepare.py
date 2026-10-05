import hashlib,json,subprocess
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.research_v8.registry import FIELDS,append_event

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head=='f328dcbef054b53dbf31cae87af082c0f8305dcb'
run=STATE/'d084-hold-trend-gate-20261005-v1';run.mkdir()
py='/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python';prefix=[py,'-B'];steps=[];refs={}
for window,pn,rn in [('ORIGINAL','protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json','reports/fast_research/SPOT_DEFENSIVE_BLEND_20261005_V1.json'),('LATER','protocols/SPOT_LATER_BLEND_20261005_V1.json','reports/fast_research/SPOT_LATER_BLEND_20261005_V1.json')]:
    c=read(ROOT/pn)
    for name in ('perpetual_report','economic_reference'):c.pop(name,None)
    c.update(parent_commit=head,module='D084_'+window,experiment_id='D084_HOLD_TREND_'+window,
        recipe='HALF_HOLD10_EXIT10_HOLD_TREND',annual_vol_target=.10,
        question='Does gating only the HOLD leg by the completed daily close above SMA200 reduce downside without eliminating the original net opportunity?',
        hypothesis='D083 later loss is HOLD price exposure, not Donchian or fee. A past-known trend gate may lower downside but miss rebounds and incur gate transactions.',
        spot_control=dict(path=str(ROOT/rn),sha256=sha(ROOT/rn)),
        success_decision='Account acceptance independent of economic result. Adopt development challenger only if BASE/STRESS both show positive net delta with no greater realized daily vol and minute MDD in BOTH seen windows; otherwise retain old research reference, identify tradeoff and pause fixed gate. No investment promotion.',
        change='Only HOLD component multiplied by daily close>SMA200 mask AFTER original full HOLD covariance sizing. Equality flat, no redistribution; .5HOLD+.5EXIT10, EXIT10 and budgets unchanged.',
        budget=dict(actual_spot_wallets=2,wall_seconds=1200,owned_bytes=100000000,fits=0,HPO=0,downloads=0,API=0),
        stop_rule='Exactly four wallets at declared windows/costs, no SMA/period/threshold grid. Stop on source/target/cash/cap mismatch; preserve terminal residual and original five exits. No retrospective date/asset selection.')
    c['source_hashes']={n:sha(ROOT/n) for n in c['source_hashes']}
    for n in ('scripts/investment/hold_donchian_blend_target.py','scripts/investment/audit_daily_spot_targets.py'):c['source_hashes'][n]=sha(ROOT/n)
    proto='protocols/SPOT_HOLD_TREND_'+window+'_20261005_V1.json';out='reports/fast_research/SPOT_HOLD_TREND_'+window+'_20261005_V1.json'
    save(ROOT/proto,c);refs[window]=dict(path=proto,sha256=sha(ROOT/proto))
    steps.extend([dict(title=window+'HOLD趋势门控两成本真实钱包',argv=prefix+['scripts/investment/spot_perpetual_product_comparison.py','--protocol',proto,'--run-dir',str(run/window),'--output',out]),
       dict(title=window+'独立资金库存费用与分钟risk',argv=prefix+['docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py','--input',out,'--output',str(run/(window+'_FINANCIAL.json'))]),
       dict(title=window+'独立趋势目标未来扰动与旧默认golden',argv=prefix+['scripts/investment/audit_daily_spot_targets.py','--input',out,'--output',str(run/(window+'_TARGETS.json'))]),
       dict(title=window+'资产月份与成本配对诊断',argv=prefix+['scripts/investment/spot_saved_economic_diagnostics.py','--input',out,'--output',str(run/(window+'_DIAGNOSTIC.json'))])])
save(ROOT/'protocols/SPOT_HOLD_TREND_20261005_V1.json',dict(parent_commit=head,protocols=refs,question='Single HOLD timing intervention after D083 component isolation',data_role='TWO_SEEN_DEVELOPMENT_WINDOWS_NEVER_CONCATENATED',wallets=4,fits=0,HPO=0,API_calls=0,downloads=0,full_capital=10000,abs_cap=.3,gross_cap=.6,adopt='ALL_FOUR_NET_POSITIVE_DELTA_VOL_MDD_NO_GREATER',strategy_before_results=True))
save(ROOT/'.cache/d084_batch.json',dict(steps=steps))
event=dict.fromkeys(FIELDS);event.update(event_id='D084:FIXED_GATE_BEFORE_RESULTS',event_type='OPERATIONAL_RESEARCH_START',experiment_id='D084_HOLD_TREND',git_commit=head,model_family='PAST_DAILY_HOLD_SMA200_GATE',fits=0,artifact_path='protocols/SPOT_HOLD_TREND_20261005_V1.json',artifact_sha256=sha(ROOT/'protocols/SPOT_HOLD_TREND_20261005_V1.json'),success_failure='FIXED_FOUR_WALLETS_NO_SEARCH',reason_for_next_experiment='D083 later loss from HOLD exposure; one past-trend gate tests downside vs missed upside, same costs/capital/caps')
append_event(ROOT/'reports/experiment_registry.jsonl',event)
print('FIXED_HOLD_GATE_FOUR_WALLETS_REGISTERED')