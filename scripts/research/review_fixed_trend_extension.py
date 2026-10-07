"""Independent saved-JSON arithmetic; no fitting, replay or market/locked reads."""
import hashlib
import json
import math
from pathlib import Path
import time

ROOT=Path('/mnt/d/codex/coin')
DAY=86400000000
began=time.monotonic()
def load(name): return json.loads((ROOT/name).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def near(a,b):
    assert math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7),(a,b)
def valid_sha(value): return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)

result_name='reports/FIXED_TREND_EXTENSION_20261008.json'
protocol_name='protocols/FIXED_TREND_EXTENSION_20261008.json'
r=load(result_name); p=load(protocol_name)
assert r['status']=='COMPLETE_FROZEN_TREND_STAGE_EXTENSION' and r['protocol']==p
assert r['protocol_sha256']==sha(ROOT/protocol_name) and p['mode']=='STAGE_EXTENSION'
assert r['new_wallets']==p['budget']['new_wallets']==18 and r['new_fits']==p['budget']['new_fits']==0
assert r['qualification']==p['qualification']=='NONE_CASH' and r['locked_consumed'] is False
assert p['data_role'].startswith('SEEN_DEVELOPMENT_ONLY') and p['weights']==[.5,.5] and p['funding_scales']==[1,.01]
assert p['capital']==10000 and p['max_asset_abs']==.3 and p['max_gross']==.6 and p['leverage']==1 and not p['automatic_margin_topup']
families=['SMA200_10PCT','FIXED_HALF_SMA_CSMOM','PUBLIC_CSMOM21_WEEKLY']; assert p['families']==families
for name in ('input_audit','prior_results','parent_protocol'): assert sha(ROOT/p[name])==p[name+'_sha256']
audit=load(p['input_audit']); prior=load(p['prior_results']); parent=load(p['parent_protocol'])
assert audit['status']=='PASS_COMPLETE_EXISTING_EXTENSION_WINDOWS_WITH_EXPLICIT_GAP' and audit['selected_windows']==p['windows']
assert audit['source_manifest_sha256']==p['data_manifest_sha256']==parent['data_manifest_sha256']
assert audit['plan_sha256']==p['validation_plan_sha256'] and audit['excluded_gap_days']==p['excluded_gap_days']
assert p['symbols']==parent['symbols']==prior['protocol']['symbols'] and p['core_symbols']==prior['protocol']['core_symbols']
assert r['prior_allstage_failure_unchanged'] is True and r['prior_checks']==prior['checks'] and not all(prior['checks'].values())
assert prior['decision']=='NO_ALL_STAGE_BLEND_QUALIFICATION'
windows={w['id']:w for w in p['windows']}; assert len(windows)==len(p['windows'])==3
assert [(w['fold'],w['days']) for w in p['windows']]==[(2,41),(2,142),(4,184)]
for w in windows.values():
    assert w['end']-w['start']==w['days']*DAY and w['end']<1772323200000000 and w['active_symbols']==p['core_symbols']
    source=next(x for x in audit['cases'] if x['window']==w)
    assert source['complete_trade_mark'] and source['required_minutes']==w['days']*1440
    assert all(source['observed_minutes'][s]==w['days']*1440 and not source['missing_minutes'][s] and source['invalid_observed_minutes'][s]==0 for s in p['core_symbols'])
original={(x['result_path'],x['result_sha256']) for x in prior['cases']+prior['reused_csmom_controls']}
goldens=r['original_target_goldens']; assert len(goldens)==12 and {(x['result_path'],x['result_sha256']) for x in goldens}==original
assert all(x['exact'] is True and valid_sha(x['target_sha256']) for x in goldens)
key=lambda x:(x['window'],x['funding_scale'],x['family'])
rows={key(x):x for x in r['cases']}
expected={(w,s,f) for w in windows for s in p['funding_scales'] for f in families}
assert set(rows)==expected and len(r['cases'])==len(rows)==18
bridges=[]; summary=[]
for cell,x in sorted(rows.items()):
    w=windows[x['window']]; m=x['daily_metrics']; legs=x['contributions']; months=x['months']
    unit='raw_fraction' if x['funding_scale']==1 else 'raw_percent'
    assert x['result_path'].endswith('/'+unit+'/'+x['window']+'/'+x['family']+'/RESULT.json') and valid_sha(x['result_sha256'])
    assert x['complete_minutes']==w['days']*1440 and m['days']==w['days'] and x['terminal_cash_realized'] is True
    assert x['audit_status'].startswith('PASS_') and x['maximum_NAV_error']<=1e-7 and x['liquidations']>=0
    assert m['initial_nav']==10000 and set(months[-1]['ending_signed_quantities'])==set(p['symbols'])
    assert all(v==0 for v in months[-1]['ending_signed_quantities'].values())
    bridge=x['gross_PnL']-x['fees']-x['execution_cost']+x['funding']; near(bridge,x['net_PnL']); bridges.append(abs(bridge-x['net_PnL']))
    near(m['final_nav']-10000,x['net_PnL']); near(m['total_return'],x['net_PnL']/10000)
    near(m['annual_return'],(m['final_nav']/10000)**(365/m['days'])-1)
    near(m['fees'],x['fees']); near(m['execution_costs'],x['execution_cost']); near(m['turnover']/10000,x['turnover'])
    assert set(legs)=={'LONG','SHORT'}
    for leg in legs.values(): near(leg['gross']-leg['fees']-leg['execution_cost']+leg['funding'],leg['net_contribution'])
    for field,total in (('gross','gross_PnL'),('fees','fees'),('execution_cost','execution_cost'),('funding','funding'),('net_contribution','net_PnL')):
        near(sum(leg[field] for leg in legs.values()),x[total])
    assert sum(z['days'] for z in months)==w['days'] and len({z['month'] for z in months})==len(months)
    for z in months: near(z['gross_PnL']-z['fees']-z['spread_cost']-z['slippage_cost']+z['funding_USDT'],z['net_PnL'])
    for field,total in (('net_PnL','net_PnL'),('gross_PnL','gross_PnL'),('fees','fees'),('funding_USDT','funding')): near(sum(z[field] for z in months),x[total])
    near(sum(z['spread_cost']+z['slippage_cost'] for z in months),x['execution_cost'])
    summary.append(dict(window=cell[0],funding_scale=cell[1],family=cell[2],net_PnL=x['net_PnL'],LONG_net=legs['LONG']['net_contribution'],SHORT_net=legs['SHORT']['net_contribution'],vol=m['annual_volatility'],minute_MDD=x['minute_MDD'],gross_peak=x['exposure']['minute_max_gross_weight'],liquidations=x['liquidations']))
contrasts=[]
for w in windows:
    for s in p['funding_scales']:
        a,m,b=(rows[w,s,f] for f in families)
        x=dict(window=w,funding_scale=s,mix_net_gap_SMA=m['net_PnL']-a['net_PnL'],mix_net_gap_CSMOM=m['net_PnL']-b['net_PnL'],mix_minute_MDD=m['minute_MDD'],SMA_minute_MDD=a['minute_MDD'],CSMOM_minute_MDD=b['minute_MDD'],mix_short_net=m['contributions']['SHORT']['net_contribution'])
        saved=next(z for z in r['contrasts'] if z['window']==w and z['funding_scale']==s); assert set(saved)==set(x)
        for field,value in x.items():
            if isinstance(value,str): assert saved[field]==value
            else: near(saved[field],value)
        contrasts.append(x)
assert len(contrasts)==len(r['contrasts'])==6
mix=[x for x in rows.values() if x['family']=='FIXED_HALF_SMA_CSMOM']; assert len(mix)==6
gates=dict(all6_mix_net_positive=all(x['net_PnL']>0 for x in mix),all6_mix_vol_at_most12pct=all(x['daily_metrics']['annual_volatility']<=.12 for x in mix),all6_mix_MDD_at_most12pct=all(x['minute_MDD']<=.12 for x in mix),each_stage_has_net_or_DD_improvement_vs_both_singles=all((x['mix_net_gap_SMA']>=0 or x['mix_minute_MDD']<x['SMA_minute_MDD']) and (x['mix_net_gap_CSMOM']>=0 or x['mix_minute_MDD']<x['CSMOM_minute_MDD']) for x in contrasts))
assert gates==r['checks']
decision='RETAIN_STATIC_DEVELOPMENT_CONTROL_ONLY' if all(gates.values()) else 'PAUSE_UNCONDITIONAL_FIXED_BLEND_RECIPE'
assert decision==r['decision']
worst=[dict(family=f,funding_scale=s,worst_separate_window_net=min(x['net_PnL'] for x in summary if x['family']==f and x['funding_scale']==s),worst_separate_window_MDD=max(x['minute_MDD'] for x in summary if x['family']==f and x['funding_scale']==s),max_separate_window_vol=max(x['vol'] for x in summary if x['family']==f and x['funding_scale']==s)) for f in families for s in p['funding_scales']]
review=dict(status='PASS_WITH_LIMITATIONS',review_source_sha256=sha(__file__),result_sha256=sha(ROOT/result_name),protocol_sha256=sha(ROOT/protocol_name),elapsed_seconds=time.monotonic()-began,accounts_checked=18,original_target_goldens_bound=12,new_review_wallets=0,new_review_fits=0,max_abs_cash_bridge_error=max(bridges),cells=summary,contrasts=contrasts,gates=gates,decision=decision,prior_allstage_failure_unchanged=True,worst_separate_window_metrics=worst,qualification='NONE_CASH',limits=['Pure-stdlib JSON arithmetic only; full server ledger/source/target bytes not reread. Minute audit/source/target-causality identities rely on bound preflight and existing account audits.','All three stages are seen development; 41days is a short diagnostic, annualization is not stable APR. Two funding scales are conditional, not independent samples.','Aug12 CORE5 mark gap remains explicit; independent complete-capital windows are never stitched into a continuous track record.','Static netting/lower gross or volatility does not establish selector/regime or isolated SHORT alpha.','Funding units/native historical risk and instantaneous caps remain uncertified; NONE/CASH unchanged.'])
out=ROOT/'reports/FIXED_TREND_EXTENSION_REVIEW_20261008.json'
with out.open('x') as f: json.dump(review,f,indent=2,allow_nan=False); f.write('\n')
print(json.dumps(dict(status=review['status'],accounts=18,gates=gates,decision=decision,max_bridge_error=max(bridges),elapsed_seconds=review['elapsed_seconds'])))
