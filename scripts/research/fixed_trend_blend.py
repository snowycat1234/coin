"""One fixed absolute/relative trend mixture, existing native shared wallet."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np

FAMILIES = ('SMA200_10PCT', 'FIXED_HALF_SMA_CSMOM')


def compose_targets(weights, core, symbols):
    """Map two frozen causal intents into one ordered one-way portfolio.

    The fixed half/half mix is not scaled back up after diversification.
    Opposing intents net before execution. They are not separate cash wallets.
    """
    core, symbols = list(core), list(symbols)
    if (len(set(core)) != len(core) or len(set(symbols)) != len(symbols)
            or not set(core) <= set(symbols)):
        raise ValueError('Unique explicit core and full symbol order required')
    w = np.asarray(weights, dtype=np.float64)
    if w.ndim != 3 or w.shape[1:] != (2, len(core)) or not np.isfinite(w).all():
        raise ValueError('Two finite frozen expert intents in core order required')
    if np.any(np.abs(w) > .3+1e-12) or np.any(np.abs(w).sum(axis=2) > .6+1e-12):
        raise ValueError('Expert target exceeds existing asset/gross limits')
    indices = [symbols.index(s) for s in core]
    sma = np.zeros((len(w), len(symbols)), dtype=np.float64)
    csmom = np.zeros_like(sma)
    sma[:, indices] = w[:, 0]
    csmom[:, indices] = w[:, 1]
    mix = .5*sma+.5*csmom
    sleeve_gross = .5*np.abs(sma).sum(axis=1)+.5*np.abs(csmom).sum(axis=1)
    netted_gross = np.abs(mix).sum(axis=1)
    assert np.all(netted_gross <= sleeve_gross+1e-12)
    return {FAMILIES[0]: sma, FAMILIES[1]: mix}, csmom, dict(
        mean_pre_net_sleeve_intent_gross=float(sleeve_gross.mean()),
        max_pre_net_sleeve_intent_gross=float(sleeve_gross.max()),
        mean_netted_target_gross=float(netted_gross.mean()),
        max_netted_target_gross=float(netted_gross.max()),
        mean_cancelled_absolute_intent=float((sleeve_gross-netted_gross).mean()),
        not_relevered=True, no_virtual_sleeve_PnL=True)


def main():
    from modules.transformer_v3.market_binding import verify_binding
    from modules.transformer_v3.wallet import run_tasks
    from scripts.research.joint_expert_information import verified_input_view
    from scripts.research.public_cross_section_momentum import DAY_US
    from scripts.research.run_public_momentum import ROOT, save, sha, summary_row

    ap=argparse.ArgumentParser()
    ap.add_argument('--protocol',type=Path,required=True)
    ap.add_argument('--state',type=Path,required=True)
    a=ap.parse_args();began=time.monotonic();p=json.loads(a.protocol.read_text());state=a.state.resolve()
    if p.get('mode') == 'STAGE_EXTENSION':
        run_stage_extension(a, p, began)
        return
    assert os.uname().sysname=='Linux' and state.parent==Path('/home/ubuntu/coin/execution-state')
    assert p['budget']['new_wallets']==8 and p['budget']['new_fits']==0 and p['weights']==[.5,.5]
    assert p['funding_scales']==[1,.01] and p['families']==list(FAMILIES)
    sources=[Path(__file__),a.protocol,ROOT/'scripts/research/joint_expert_information.py',ROOT/'scripts/research/run_public_momentum.py']
    sources += [ROOT/p[k] for k in ('parent_protocol','parent_results','core5_results')]
    sources += [ROOT/p['input_view'][k] for k in ('result','review','protocol')]
    for src in sources:
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+str(src.resolve().relative_to(ROOT))])).hexdigest()==sha(src),'Commit inputs and implementation before accounts'
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8_000_000_000
    assert (group/'memory.swap.max').read_text().strip()=='0'
    state.mkdir(exist_ok=True);assert not (state/'RESULTS.json').exists(),'Use completed evidence instead of replaying it'
    free_before=shutil.disk_usage(state).free;assert free_before>=p['budget']['reserve_bytes']
    def progress(completed,failed,total,detail):
        save(state/'progress.json',dict(status='running',stage='BACKTEST',phase='固定绝对/相对趋势组合',completed=completed,failed=failed,total=total,unit='账户',detail=detail,elapsed_seconds=time.monotonic()-began,pid=os.getpid(),updated_at=time.time()))
    progress(0,0,8,'DATA: verify frozen expert panel and four complete CSMOM controls')
    for k in ('parent_protocol','parent_results','core5_results'):
        assert sha(ROOT/p[k])==p[k+'_sha256']
    parent=json.loads((ROOT/p['parent_protocol']).read_text())
    assert parent['symbols']==p['symbols'] and parent['data_manifest_sha256']==p['data_manifest_sha256']
    view=verified_input_view(p['input_view'],p['core_symbols'],p['data_manifest_sha256'])
    panels=[]
    for ref in view['panel_refs']:
        with np.load(ref['path'],allow_pickle=False) as f:
            # Select only the pre-existing past-only intents and decision clock.
            # No labels/feedback/common/future outcomes enter this strategy.
            panels.append((f['decision_us'].copy(),f['weights'][:, :2].copy()))
    assert all(np.array_equal(panels[0][i],panels[1][i]) for i in (0,1))
    available,weights=panels[0]
    assert np.all(np.diff(available)==DAY_US) and available.max()<=parent['locked_start_us']
    old_public=json.loads((ROOT/p['parent_results']).read_text())
    old_core=json.loads((ROOT/p['core5_results']).read_text())
    assert old_public['protocol_sha256']==p['parent_protocol_sha256']
    tasks=[];controls=[];paired={};diags={};financial_identity=None
    for w in p['windows']:
        assert w['active_symbols']==p['core_symbols'] and w['end']<=parent['locked_start_us']
        dates=np.arange(w['start'],w['end'],DAY_US,dtype=np.int64)
        assert len(dates)==w['days']
        ix=np.searchsorted(available,dates)
        assert np.all(ix<len(available)) and np.array_equal(available[ix],dates)
        targets,csmom,diags[w['id']]=compose_targets(weights[ix],p['core_symbols'],p['symbols'])
        paths={}
        for family,target_weights in targets.items():
            path=state/'targets'/(w['id']+'-'+family+'.npz');path.parent.mkdir(exist_ok=True)
            if path.exists():
                with np.load(path,allow_pickle=False) as f:
                    assert np.array_equal(f['weights'],target_weights) and np.array_equal(f['decision_us'],dates) and f['symbol_order'].tolist()==p['symbols']
            else:np.savez_compressed(path,weights=target_weights,decision_us=dates,symbol_order=np.array(p['symbols']))
            paths[family]=path
        for scale in p['funding_scales']:
            old_rows=old_public['cases'] if w['fold']==1 else old_core['cases']
            row=next(x for x in old_rows if x['window']==w['id'] and x['funding_scale']==scale)
            old_path=Path(row['result_path']);assert sha(old_path)==row['result_sha256']
            old=json.loads(old_path.read_text());task=old['task']
            assert task['window']==w and task['funding_scale']==scale and old['summary']['symbols']==p['symbols']
            assert float(old['summary']['daily_metrics']['initial_nav'])==10000
            assert sha(task['target_path'])==task['target_sha256']
            with np.load(task['target_path'],allow_pickle=False) as f:
                assert np.array_equal(f['weights'],csmom),'Frozen CSMOM intent changed: no account may run'
                assert np.array_equal(f['decision_us'],dates) and f['symbol_order'].tolist()==p['symbols']
            checked=summary_row(old,old_path,row['kind'])
            assert all(row[k]==v for k,v in checked.items())
            for name,digest in old['binding']['frozen_wallet_sources'].items():assert sha(ROOT/name)==digest
            market=verify_binding(task['native_market_binding_path'],task['native_market_binding_sha256'])
            identity={k:old['binding'][k] for k in ('wallet_source_sha256','storage_source_sha256','financial_sources','frozen_wallet_sources')}
            if financial_identity is None:financial_identity=identity
            else:assert financial_identity==identity
            controls.append(checked);paired[(w['id'],scale)]=(old,market)
            for family,path in paths.items():
                new=dict(task,id=('raw_fraction' if scale==1 else 'raw_percent')+'/'+w['id']+'/'+family,
                         state=str(state),family=family,target_path=str(path),target_sha256=sha(path),protocol_sha256=sha(a.protocol))
                for key in ('mark_reference','native_market_binding_path','native_market_binding_sha256'):new.pop(key)
                tasks.append(new)
        print('[TARGET] '+w['id']+' two frozen expert columns, CSMOM exact golden, fixed half/half; no fit',flush=True)
    assert len(controls)==4 and len(tasks)==8
    save(state/'TARGET_DIAGNOSTICS.json',diags);save(state/'REUSED_CONTROLS.json',controls)
    cases=run_tasks(tasks,state,'FIXED_TREND_BLEND',workers=2,protocol_path=a.protocol,on_progress=progress)
    rows=[]
    for c in cases:
        old,market=paired[(c['task']['window']['id'],c['task']['funding_scale'])]
        for key in ('contract','cost_scenario','unit_scenario','symbols'):assert c['summary'][key]==old['summary'][key]
        for key in ('work','collector_root','source_run','funding_scale','profile','mapping','seed','window'):assert c['task'][key]==old['task'][key]
        for key in financial_identity:assert c['binding'][key]==financial_identity[key]
        assert verify_binding(c['task']['native_market_binding_path'],c['task']['native_market_binding_sha256'])==market
        rows.append(summary_row(c,state/'native'/c['task']['id']/'RESULT.json','NEW_FIXED_BLEND_OR_MATCHED_RISK_SMA'))
    contrasts=[]
    for w in p['windows']:
        for scale in p['funding_scales']:
            sma=next(x for x in rows if x['window']==w['id'] and x['funding_scale']==scale and x['family']==FAMILIES[0])
            mix=next(x for x in rows if x['window']==w['id'] and x['funding_scale']==scale and x['family']==FAMILIES[1])
            cs=next(x for x in controls if x['window']==w['id'] and x['funding_scale']==scale)
            contrasts.append(dict(window=w['id'],funding_scale=scale,
                mix_net_gap_SMA=mix['net_PnL']-sma['net_PnL'],mix_net_gap_CSMOM=mix['net_PnL']-cs['net_PnL'],
                mix_minute_MDD=mix['minute_MDD'],SMA_minute_MDD=sma['minute_MDD'],CSMOM_minute_MDD=cs['minute_MDD'],
                mix_vol=mix['daily_metrics']['annual_volatility'],SMA_vol=sma['daily_metrics']['annual_volatility'],CSMOM_vol=cs['daily_metrics']['annual_volatility'],
                mix_short_net=mix['contributions']['SHORT']['net_contribution']))
    mixrows=[r for r in rows if r['family']==FAMILIES[1]]
    checks=dict(all4_mix_net_positive=all(r['net_PnL']>0 for r in mixrows),
        all4_mix_vol_at_most12pct=all(r['daily_metrics']['annual_volatility']<=.12 for r in mixrows),
        all4_mix_MDD_at_most12pct=all(r['minute_MDD']<=.12 for r in mixrows),
        each_stage_has_net_or_DD_improvement_vs_both_singles=all(
            (x['mix_net_gap_SMA']>=0 or x['mix_minute_MDD']<x['SMA_minute_MDD']) and
            (x['mix_net_gap_CSMOM']>=0 or x['mix_minute_MDD']<x['CSMOM_minute_MDD']) for x in contrasts),
        both2025_mix_short_positive=all(r['contributions']['SHORT']['net_contribution']>0 for r in mixrows if r['window'].startswith('fold3')))
    owned=sum(f.stat().st_size for f in state.rglob('*') if f.is_file())
    assert owned<=p['budget']['new_owned_bytes'] and time.monotonic()-began<=p['budget']['wall_seconds']
    result=dict(status='COMPLETE_FIXED_TREND_BLEND_DEVELOPMENT_CONTRAST',protocol=p,protocol_sha256=sha(a.protocol),source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),cases=sorted(rows,key=lambda x:(x['window'],x['funding_scale'],x['family'])),reused_csmom_controls=controls,target_diagnostics=diags,contrasts=contrasts,checks=checks,
        decision='RETAIN_FIXED_BLEND_FOR_INDEPENDENT_VALIDATION' if all(checks.values()) else 'NO_ALL_STAGE_BLEND_QUALIFICATION',qualification='NONE_CASH',new_wallets=8,new_fits=0,locked_consumed=False,elapsed_seconds=time.monotonic()-began,owned_bytes=owned,free_bytes_before=free_before,free_bytes_after=shutil.disk_usage(state).free,RAM_limit=(group/'memory.max').read_text().strip(),swap_limit=(group/'memory.swap.max').read_text().strip(),GPU=0,RAM_group_peak_bytes=int((group/'memory.peak').read_text()) if (group/'memory.peak').exists() else None,limitations=p['limitations'])
    save(state/'RESULTS.json',result)
    lines=['# 固定绝对/相对趋势：同一钱包的实际互补检验','',f"决定 {result['decision']}；投资NONE/CASH。两个已见窗口/两资金情景；8新钱包、4控制复用、0fit。",'',
        '|窗口|资金解释|策略|净PnL|LONG净|SHORT净|年化vol|分钟MDD|手续费/执行/资金|换手|','|---|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in sorted(rows+controls,key=lambda x:(x['window'],x['funding_scale'],x['family'])):
        lines.append(f"|{r['window']}|{r['funding_scale']}|{r['family']}|{r['net_PnL']:.2f}|{r['contributions']['LONG']['net_contribution']:.2f}|{r['contributions']['SHORT']['net_contribution']:.2f}|{r['daily_metrics']['annual_volatility']:.2%}|{r['minute_MDD']:.2%}|{r['fees']:.2f}/{r['execution_cost']:.2f}/{r['funding']:.2f}|{r['turnover']:.2f}|")
    lines+=['','固定半权不再放大。相反意图先净成同一one-way目标，完整10k共享资本，分腿贡献只来自实际净持仓；不把平均独立钱包收益当mix。',
        '较低波动/gross本身会降低回撤，不作为新SHORT alpha证据。实际gross漂移/延迟风险按旧引擎报告，不声称瞬时caps已认证。']+p['limitations']+['',
        '复现：python -B scripts/research/fixed_trend_blend.py --protocol protocols/FIXED_TREND_BLEND_20261008.json --state /home/ubuntu/coin/execution-state/fixed-trend-blend-NEW；源码需事前commit，8GB/swap0/GPU0受限scope。']
    (state/'REPORT.md').write_text('\n'.join(lines)+'\n')
    save(state/'progress.json',dict(status='completed',stage='REPORT',phase='完成',completed=8,total=8,unit='账户',elapsed_seconds=result['elapsed_seconds'],updated_at=time.time(),detail=result['decision']))
    print(json.dumps(dict(status=result['status'],checks=checks,decision=result['decision'])),flush=True)


def run_stage_extension(a, p, began):
    """Extend the same frozen intents, never a completed wallet or label panel."""
    import polars as pl
    from modules.transformer_v3.market_binding import verify_binding
    from modules.transformer_v3.wallet import run_tasks
    from scripts.research.joint_expert_information import signed_intents
    from scripts.research.public_cross_section_momentum import DAY_US
    from scripts.research.run_public_momentum import ROOT, load_past_inputs, save, sha, summary_row

    state=a.state.resolve();families=list(FAMILIES)+['PUBLIC_CSMOM21_WEEKLY']
    assert os.uname().sysname=='Linux' and state.parent==Path('/home/ubuntu/coin/execution-state')
    assert p['families']==families and p['weights']==[.5,.5] and p['funding_scales']==[1,.01]
    assert p['budget']['new_wallets']==18 and p['budget']['new_fits']==0
    assert p['budget']['workers']==4 and p['capital']==10000 and p['max_gross']==.6 and p['max_asset_abs']==.3
    bound=[Path(__file__),a.protocol,ROOT/'scripts/research/inspect_trend_extension.py',
           ROOT/'scripts/research/joint_expert_information.py',ROOT/'scripts/research/run_public_momentum.py',
           ROOT/'scripts/research/public_cross_section_momentum.py']
    bound += [ROOT/p[k] for k in ('input_audit','parent_protocol','prior_results')]
    for src in bound:
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+str(src.resolve().relative_to(ROOT))])).hexdigest()==sha(src),'Commit all inputs before economics'
    for k in ('input_audit','parent_protocol','prior_results'):assert sha(ROOT/p[k])==p[k+'_sha256']
    audit=json.loads((ROOT/p['input_audit']).read_text());parent=json.loads((ROOT/p['parent_protocol']).read_text())
    prior=json.loads((ROOT/p['prior_results']).read_text())
    assert audit['status']=='PASS_COMPLETE_EXISTING_EXTENSION_WINDOWS_WITH_EXPLICIT_GAP'
    assert audit['source_sha256']==sha(ROOT/'scripts/research/inspect_trend_extension.py')
    assert audit['selected_windows']==p['windows'] and audit['source_manifest_sha256']==p['data_manifest_sha256']==parent['data_manifest_sha256']
    assert p['symbols']==parent['symbols']==prior['protocol']['symbols'] and p['core_symbols']==prior['protocol']['core_symbols']
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8_000_000_000
    assert (group/'memory.swap.max').read_text().strip()=='0'
    state.mkdir(exist_ok=True);assert not (state/'STARTED.json').exists(),'Inspect partial evidence before any rerun'
    free_before=shutil.disk_usage(state).free;assert free_before>=p['budget']['reserve_bytes']
    save(state/'STARTED.json',dict(protocol_sha256=sha(a.protocol),source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),started_at=time.time()))
    def progress(completed,failed,total,detail):
        save(state/'progress.json',dict(status='running',stage='BACKTEST',phase='冻结趋势跨阶段真实共享钱包',completed=completed,failed=failed,total=total,unit='账户',detail=detail,elapsed_seconds=time.monotonic()-began,pid=os.getpid(),updated_at=time.time()))
    progress(0,0,18,'DATA: past-only full calendar and original-window exact target goldens')
    full,available,input_refs=load_past_inputs(parent)
    keep=available<=max(w['end'] for w in p['windows']);available=available[keep]
    close=full[keep][:,[p['symbols'].index(s) for s in p['core_symbols']]]
    sma=[]
    for s in p['core_symbols']:
        path=Path(input_refs[p['symbols'].index(s)]['path'])
        f=pl.read_parquet(path,columns=['dt','symbol','decision_available_at','sma_signal']).sort('dt')
        f=f.filter(pl.col('decision_available_at').dt.epoch('us')<=available[-1])
        assert np.array_equal(f['decision_available_at'].dt.epoch('us').to_numpy(),available) and f['symbol'].eq(s).all()
        sma.append(f['sma_signal'].to_numpy())
    sma=np.column_stack(sma)
    weights=signed_intents(close,sma,available,p['core_symbols'])[:, :2]
    assert np.all(np.diff(available)==DAY_US) and available[-1]<parent['locked_start_us']
    gap_day=p['excluded_gap_days'][0]['day_us']
    assert gap_day in available and gap_day+DAY_US in available,'Keep valid trade features across the mark-only gap'
    boundary=int(np.searchsorted(available,gap_day+DAY_US))
    changed_close=close.copy();changed_sma=sma.copy()
    changed_close[boundary+1:]*=2;changed_sma[boundary+1:]*=-1
    perturbed=signed_intents(changed_close,changed_sma,available,p['core_symbols'])[:, :2]
    assert np.array_equal(weights[:boundary+1],perturbed[:boundary+1]),'Future suffix changed past targets'
    reverse=signed_intents(close[:,::-1],sma[:,::-1],available,list(reversed(p['core_symbols'])))[:, :2, ::-1]
    order_error=float(np.max(np.abs(weights-reverse)))
    assert order_error<=1e-12,'Asset identity/order changed frozen intent'
    save(state/'TARGET_CAUSALITY.json',dict(future_suffix_unchanged=True,mark_gap_trade_calendar_retained=True,asset_order_max_error=order_error,window_goldens_required=12))
    def targets_for(w):
        dates=np.arange(w['start'],w['end'],DAY_US,dtype=np.int64)
        ix=np.searchsorted(available,dates)
        assert len(dates)==w['days'] and np.all(ix<len(available)) and np.array_equal(available[ix],dates)
        targets,cs,diag=compose_targets(weights[ix],p['core_symbols'],p['symbols'])
        targets['PUBLIC_CSMOM21_WEEKLY']=cs
        return dates,targets,diag
    oldrows=prior['cases']+prior['reused_csmom_controls'];goldens=[];identity=None;template=None;summary_by_scale={}
    for row in oldrows:
        path=Path(row['result_path']);assert sha(path)==row['result_sha256'];old=json.loads(path.read_text())
        assert summary_row(old,path,row['kind'])==row
        task=old['task'];dates,targets,_=targets_for(task['window'])
        summary_by_scale[task['funding_scale']]=old['summary']
        assert sha(task['target_path'])==task['target_sha256']
        with np.load(task['target_path'],allow_pickle=False) as f:
            assert np.array_equal(f['weights'],targets[task['family']]),'Original-window frozen target golden changed; no wallets permitted'
            assert np.array_equal(f['decision_us'],dates) and f['symbol_order'].tolist()==p['symbols']
        for name,digest in old['binding']['frozen_wallet_sources'].items():assert sha(ROOT/name)==digest
        current={k:old['binding'][k] for k in ('wallet_source_sha256','storage_source_sha256','financial_sources','frozen_wallet_sources')}
        if identity is None:identity=current;template=task
        else:assert identity==current
        goldens.append(dict(result_path=str(path),result_sha256=sha(path),target_sha256=task['target_sha256'],exact=True))
    assert len(goldens)==12
    save(state/'ORIGINAL_TARGET_GOLDENS.json',goldens)
    tasks=[];diags={}
    for w in p['windows']:
        assert w['active_symbols']==p['core_symbols'] and w['end']<parent['locked_start_us']
        dates,targets,diags[w['id']]=targets_for(w)
        for family,target in targets.items():
            path=state/'targets'/(w['id']+'-'+family+'.npz');path.parent.mkdir(exist_ok=True)
            np.savez_compressed(path,weights=target,decision_us=dates,symbol_order=np.array(p['symbols']))
            for scale in p['funding_scales']:
                new=dict(template,id=('raw_fraction' if scale==1 else 'raw_percent')+'/'+w['id']+'/'+family,state=str(state),window=w,funding_scale=scale,family=family,target_path=str(path),target_sha256=sha(path),protocol_sha256=sha(a.protocol))
                for key in ('mark_reference','native_market_binding_path','native_market_binding_sha256'):new.pop(key,None)
                tasks.append(new)
        print('[TARGET] '+w['id']+' original frozen rules, complete past calendar; no fit',flush=True)
    assert len(tasks)==len({t['id'] for t in tasks})==18
    save(state/'TARGET_DIAGNOSTICS.json',diags)
    cases=run_tasks(tasks,state,'FIXED_TREND_EXTENSION',workers=p['budget']['workers'],protocol_path=a.protocol,on_progress=progress)
    rows=[]
    for c in cases:
        for key in ('contract','cost_scenario','unit_scenario','symbols'):assert c['summary'][key]==summary_by_scale[c['task']['funding_scale']][key]
        for key in ('work','collector_root','source_run','profile','mapping','seed'):assert c['task'][key]==template[key]
        for key in identity:assert c['binding'][key]==identity[key]
        match=next(x for x in audit['cases'] if x['window']==c['task']['window'])
        binding=verify_binding(c['task']['native_market_binding_path'],c['task']['native_market_binding_sha256'])
        assert binding['files']==match['market_files'] and binding['source_manifest_sha256']==p['data_manifest_sha256']
        rows.append(summary_row(c,state/'native'/c['task']['id']/'RESULT.json','NEW_FROZEN_STAGE_EXTENSION'))
    contrasts=[]
    for w in p['windows']:
        for scale in p['funding_scales']:
            cell={r['family']:r for r in rows if r['window']==w['id'] and r['funding_scale']==scale}
            assert set(cell)==set(families)
            mix=cell[FAMILIES[1]];sma=cell[FAMILIES[0]];cs=cell['PUBLIC_CSMOM21_WEEKLY']
            contrasts.append(dict(window=w['id'],funding_scale=scale,mix_net_gap_SMA=mix['net_PnL']-sma['net_PnL'],mix_net_gap_CSMOM=mix['net_PnL']-cs['net_PnL'],mix_minute_MDD=mix['minute_MDD'],SMA_minute_MDD=sma['minute_MDD'],CSMOM_minute_MDD=cs['minute_MDD'],mix_short_net=mix['contributions']['SHORT']['net_contribution']))
    mixrows=[r for r in rows if r['family']==FAMILIES[1]];assert len(mixrows)==6
    checks=dict(all6_mix_net_positive=all(r['net_PnL']>0 for r in mixrows),all6_mix_vol_at_most12pct=all(r['daily_metrics']['annual_volatility']<=.12 for r in mixrows),all6_mix_MDD_at_most12pct=all(r['minute_MDD']<=.12 for r in mixrows),each_stage_has_net_or_DD_improvement_vs_both_singles=all((x['mix_net_gap_SMA']>=0 or x['mix_minute_MDD']<x['SMA_minute_MDD']) and (x['mix_net_gap_CSMOM']>=0 or x['mix_minute_MDD']<x['CSMOM_minute_MDD']) for x in contrasts))
    owned=sum(f.stat().st_size for f in state.rglob('*') if f.is_file())
    assert owned<=p['budget']['new_owned_bytes'] and time.monotonic()-began<=p['budget']['wall_seconds']
    result=dict(status='COMPLETE_FROZEN_TREND_STAGE_EXTENSION',protocol=p,protocol_sha256=sha(a.protocol),source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),cases=sorted(rows,key=lambda x:(x['window'],x['funding_scale'],x['family'])),contrasts=contrasts,checks=checks,original_target_goldens=goldens,past_inputs=input_refs,target_diagnostics=diags,prior_checks=prior['checks'],decision='RETAIN_STATIC_DEVELOPMENT_CONTROL_ONLY' if all(checks.values()) else 'PAUSE_UNCONDITIONAL_FIXED_BLEND_RECIPE',prior_allstage_failure_unchanged=True,qualification='NONE_CASH',new_wallets=18,new_fits=0,locked_consumed=False,elapsed_seconds=time.monotonic()-began,owned_bytes=owned,free_bytes_before=free_before,free_bytes_after=shutil.disk_usage(state).free,RAM_limit=(group/'memory.max').read_text().strip(),swap_limit=(group/'memory.swap.max').read_text().strip(),GPU=0,RAM_group_peak_bytes=int((group/'memory.peak').read_text()) if (group/'memory.peak').exists() else None,limitations=p['limitations'])
    save(state/'RESULTS.json',result)
    save(state/'progress.json',dict(status='completed',stage='REPORT',phase='完成',completed=18,total=18,unit='账户',elapsed_seconds=result['elapsed_seconds'],updated_at=time.time(),detail=result['decision']))
    print(json.dumps(dict(status=result['status'],checks=checks,decision=result['decision'])),flush=True)


if __name__=='__main__':main()
