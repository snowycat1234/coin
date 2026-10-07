"""One published rule, four DEV wallets, reused controls; no fitting or search."""
import argparse,hashlib,json,os,resource,shutil,subprocess,time
from datetime import datetime,UTC
from pathlib import Path
import numpy as np
import polars as pl
from modules.transformer_v3.wallet import run_tasks
from modules.transformer_v3.market_binding import digest_file
from scripts.research.public_cross_section_momentum import public_targets,DAY_US

ROOT=Path(__file__).resolve().parents[2]
def sha(p):return digest_file(p)
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def verify_legacy_sources(old,current,compatibility,liquidations):
    if old.keys()!=current.keys():raise ValueError('Legacy financial source set changed')
    changed={k for k in old if old[k]!=current[k]}
    if changed and liquidations!=0:raise ValueError('Metadata compatibility limited to zero-liquidation controls')
    for k in changed:
        pair=compatibility.get(k,{})
        if pair.get('old')!=old[k] or pair.get('current')!=current[k]:raise ValueError('Unreviewed legacy financial change: '+k)
    return sorted(changed)
def summary_row(case,path,kind):
    s=case['summary'];a=case['independent_audit']
    if s['completed_minutes']!=s['required_minutes'] or not s['terminal_cash_realized']:raise ValueError('Incomplete wallet is not full-window economics')
    if not a['status'].startswith('PASS_') or not a['terminal_cash_realized']:raise ValueError('Independent financial audit failed')
    if sha(case['summary_path'])!=case['summary_sha256'] or sha(case['independent_audit_path'])!=case['independent_audit_sha256']:raise ValueError('Saved summary/audit changed')
    for item in case['artifacts'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('Saved financial artifact changed')
    return dict(kind=kind,result_path=str(path),result_sha256=sha(path),window=case['task']['window']['id'],
        funding_scale=case['task']['funding_scale'],family=case['task']['family'],net_PnL=s['net_PnL'],gross_PnL=s['gross_PnL_same_quantities'],
        fees=s['fees_USDT'],execution_cost=s['execution_cost_USDT'],funding=s['funding_USDT'],turnover=s['normalized_total_turnover'],
        daily_metrics=s['daily_metrics'],minute_MDD=s['minute_max_drawdown'],exposure=s['realized_exposure'],
        contributions=s['long_short_marked_contribution'],months=s['months'],concentration=s['daily_net_gain_concentration'],
        short_open_legs=a['actual_short_open_legs'],audit_status=a['status'],maximum_NAV_error=a['maximum_NAV_error_USDT'],
        terminal_cash_realized=True,complete_minutes=s['completed_minutes'],liquidations=s['liquidation_count'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    began=time.monotonic();p=json.loads(a.protocol.read_text());state=a.state.resolve()
    assert os.uname().sysname=='Linux' and state.is_relative_to(Path('/home/ubuntu/coin/execution-state'))
    assert p['budget']['new_wallets']==4 and p['budget']['new_fits']==0
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8000000000
    assert (group/'memory.swap.max').read_text().strip()=='0'
    state.mkdir(exist_ok=True);free_before=shutil.disk_usage(state).free;assert free_before>=p['budget']['reserve_bytes']
    source_paths=[Path(__file__),a.protocol,ROOT/'scripts/research/public_cross_section_momentum.py',ROOT/'modules/transformer_v3/wallet.py']
    for src in source_paths:
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+str(src.resolve().relative_to(ROOT))])).hexdigest()==sha(src),'Commit all sources before economics'
    def progress(completed,failed,total,detail):
        save(state/'progress.json',dict(status='running',phase='真实共享钱包回放',stage='BACKTEST',completed=completed,failed=failed,total=total,unit='账户',detail=detail,
            elapsed_seconds=time.monotonic()-began,pid=os.getpid(),updated_at=time.time()))
    progress(0,0,4,'DATA: verify past-only inputs and saved control identities')
    work=Path(p['work']);manifest=work/'reports/DATASET_MANIFEST.json';labels=work/'data/labels/raw_fraction/LABEL_MANIFEST.json'
    assert sha(manifest)==p['data_manifest_sha256'] and sha(labels)==p['label_manifest_sha256']
    refs=json.loads(labels.read_text());assert refs['scenario']=='raw_fraction' and [x['symbol'] for x in refs['files']]==p['symbols']
    frames=[];inputs=[];available=None
    for ref in refs['files']:
        fpath=Path(ref['path']).resolve();assert fpath.parent==labels.parent.resolve() and sha(fpath)==ref['sha256']
        f=pl.read_parquet(fpath,columns=['dt','symbol','close','decision_available_at']).sort('dt')
        d=f['dt'].dt.epoch('us').to_numpy();av=f['decision_available_at'].dt.epoch('us').to_numpy()
        assert np.all(np.diff(d)==DAY_US) and np.all(av==d+DAY_US) and d.max()<p['locked_start_us'] and f['symbol'].eq(ref['symbol']).all()
        if available is None:available=av
        else:assert np.array_equal(available,av)
        frames.append(f['close'].to_numpy());inputs.append(dict(path=str(fpath),sha256=ref['sha256']))
    close=np.column_stack(frames);old=Path(p['previous_state']);controls=[];tasks=[]
    # Legacy replay predates per-wallet market-input manifests. Reconstruct its
    # existing global audited dataset chain, never invent a per-case binding.
    source_binding=Path(p['source_run'])/'BINDING.json'
    sb=json.loads(source_binding.read_text());assert sb['dataset_sha256']==p['data_manifest_sha256'] and sb['symbols']==p['symbols']
    replay_protocol=old/'V2_REPLAY_PROTOCOL.json';rp=json.loads(replay_protocol.read_text())
    complete=Path(rp['complete_run']);complete_binding=json.loads((complete/'BINDING.json').read_text())
    assert complete_binding['source_binding_sha256']==sha(source_binding)
    assert complete_binding['plan_sha256']==sha(complete/'VALIDATION_PLAN.json')
    financial={str(q.relative_to(ROOT)):sha(q) for q in sorted((ROOT/'src/quant').glob('*.py'))+sorted((ROOT/'scripts/investment').glob('*.py'))}
    print('[DATA] 10/10 past-only daily inputs; no labels or locked dates loaded',flush=True)
    for w in p['windows']:
        assert w['end']<=p['locked_start_us'] and (w['end']-w['start'])//DAY_US==w['days']
        dates=np.arange(w['start'],w['end'],DAY_US,dtype=np.int64)
        weights,diagnostics=public_targets(close,available,dates,p['symbols'],w['active_symbols'],anchor_us=p['method']['anchor_us'])
        target=state/'targets'/(w['id']+'.npz');target.parent.mkdir(exist_ok=True)
        if target.exists():
            with np.load(target,allow_pickle=False) as f:
                assert np.array_equal(f['weights'],weights) and np.array_equal(f['decision_us'],dates) and f['symbol_order'].tolist()==p['symbols']
        else:np.savez_compressed(target,weights=weights,decision_us=dates,symbol_order=np.array(p['symbols']))
        save(target.with_suffix('.json'),dict(source_sha256=sha(ROOT/'scripts/research/public_cross_section_momentum.py'),target_sha256=sha(target),diagnostics=diagnostics))
        for scale in p['funding_scales']:
            scenario='raw_fraction' if scale==1 else 'raw_percent'
            for family in p['controls']:
                path=old/'native/legacy-controls'/scenario/w['id']/family/'RESULT.json';c=json.loads(path.read_text());s=c['summary']
                assert c['task']['window']==w and c['task']['funding_scale']==scale and s['symbols']==p['symbols']
                assert c['task']['work']==str(work)
                compatibility=verify_legacy_sources(c['binding']['financial_sources'],financial,p['legacy_source_compatibility'],s['liquidation_count'])
                assert c['binding']['protocol_sha256']==sha(replay_protocol)
                prior=json.loads(Path(c['task']['prior_result']).read_text())
                assert prior['binding']==complete_binding and prior['window']==w and prior['funding_scale']==scale and prior['model']==family
                assert sha(c['task']['target_path'])==c['binding']['frozen_target_sha256']
                assert float(s['daily_metrics']['initial_nav'])==10000
                row=summary_row(c,path,'REUSED_COMPLETE_CONTROL');row['reviewed_non_economic_source_differences']=compatibility;controls.append(row)
            tasks.append(dict(id=scenario+'/'+w['id']+'/PUBLIC_CSMOM21_WEEKLY',state=str(state),collector_root=p['collector_root'],work=str(work),source_run=p['source_run'],
                family='PUBLIC_CSMOM21_WEEKLY',seed=0,profile='FULL',mapping='NEUTRAL',window=w,funding_scale=scale,target_path=str(target),target_sha256=sha(target),protocol_sha256=sha(a.protocol),noncausal=False))
        print('[TARGET] '+w['id']+' frozen weekly ranking, daily signed risk sizing',flush=True)
    save(state/'REUSED_CONTROLS.json',controls)
    cases=run_tasks(tasks,state,'PUBLIC_MOMENTUM',workers=p['budget']['workers'],protocol_path=a.protocol,on_progress=progress)
    rows=[]
    for c in cases:
        path=state/'native'/c['task']['id']/'RESULT.json';row=summary_row(c,path,'NEW_FIXED_PUBLIC_ADAPTATION')
        for base in controls:
            if base['window']==row['window'] and base['funding_scale']==row['funding_scale']:
                original=json.loads(Path(base['result_path']).read_text())['summary']
                assert c['summary']['contract']==original['contract'] and c['summary']['cost_scenario']==original['cost_scenario'] and c['summary']['unit_scenario']==original['unit_scenario']
        row['net_gaps_vs_controls']={b['family']:row['net_PnL']-b['net_PnL'] for b in controls if b['window']==row['window'] and b['funding_scale']==row['funding_scale']}
        rows.append(row)
    gates=dict(all4_positive_net=all(r['net_PnL']>0 for r in rows),both_2025_short_positive=all(r['contributions']['SHORT']['net_contribution']>0 for r in rows if r['window'].startswith('fold3')),
        all4_vol_at_most12pct=all(r['daily_metrics']['annual_volatility']<=.12 for r in rows),all4_minute_MDD_at_most12pct=all(r['minute_MDD']<=.12 for r in rows))
    owned=sum(q.stat().st_size for q in state.rglob('*') if q.is_file());assert owned<=p['budget']['new_owned_bytes'] and time.monotonic()-began<p['budget']['wall_seconds']
    result=dict(status='COMPLETE_FIXED_PUBLIC_MOMENTUM_DEVELOPMENT_SCREEN',protocol=p,protocol_sha256=sha(a.protocol),source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),
        input_refs=inputs,cases=sorted(rows,key=lambda r:(r['window'],r['funding_scale'])),reused_controls=controls,checks=gates,
        reconstructed_legacy_input_chain=dict(source_binding_path=str(source_binding),source_binding_sha256=sha(source_binding),dataset_sha256=sb['dataset_sha256'],
            complete_binding_path=str(complete/'BINDING.json'),complete_binding_sha256=sha(complete/'BINDING.json'),
            validation_plan_sha256=sha(complete/'VALIDATION_PLAN.json'),replay_protocol_sha256=sha(replay_protocol),
            role='Existing audited global dataset/legacy-case/replay source chain; legacy replay has no invented per-case market manifest'),
        decision='RETAIN_FOR_MATCHED_RISK_AND_INDEPENDENT_VALIDATION' if all(gates.values()) else 'PAUSE_EXACT_RECIPE_NO_PARAMETER_SCAN',qualification='NONE_CASH',
        actual_new_wallets=4,actual_new_fits=0,locked_consumed=False,elapsed_seconds=time.monotonic()-began,owned_bytes=owned,
        RAM_group_peak_bytes=int((group/'memory.peak').read_text()),RAM_limit=(group/'memory.max').read_text().strip(),swap_limit=(group/'memory.swap.max').read_text().strip(),
        free_bytes_before=free_before,free_bytes_after=shutil.disk_usage(state).free,
        limitations=['Seen development, two selected existing contiguous windows; neither fresh OOS nor full2022bear',
          'Binance USD-M prices/funding with Bybit fee model: cross-venue proxy, two unconfirmed funding unit interpretations',
          'Equalweight K2/vol-target adaptation is not complete original paper replication; historical survivor pool remains limited',
          'Old gross60 controls have different realized risk, no causal pure-short increment or risk-matched superiority claim',
          'Separate full-capital wallets are never added or stitched; annual return is short-window descriptive, long-term APR UNKNOWN'])
    save(state/'RESULTS.json',result)
    lines=['# 固定公开横截面动量：真实共享钱包对照','',f"投资资格 NONE/CASH；决定 `{result['decision']}`。零训练、一个固定配置、四个新账户；旧控制通过身份/SHA复用。",'',
       '|窗口|资金费解释|净PnL USDT|LONG净|SHORT净|实际年化波动|分钟MDD|手续费/执行|资金费|换手/10k|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in result['cases']:
        lines.append(f"|{r['window']}|{r['funding_scale']}|{r['net_PnL']:.2f}|{r['contributions']['LONG']['net_contribution']:.2f}|{r['contributions']['SHORT']['net_contribution']:.2f}|{r['daily_metrics']['annual_volatility']:.2%}|{r['minute_MDD']:.2%}|{r['fees']:.2f}/{r['execution_cost']:.2f}|{r['funding']:.2f}|{r['turnover']:.2f}|")
    lines+=['','## 原控制：相同产品/窗口/池/资本/成本，实际风险不同','', '|窗口|资金费解释|控制|净PnL USDT|实际波动|分钟MDD|','|---|---|---|---:|---:|---:|']
    for r in controls:lines.append(f"|{r['window']}|{r['funding_scale']}|{r['family']}|{r['net_PnL']:.2f}|{r['daily_metrics']['annual_volatility']:.2%}|{r['minute_MDD']:.2%}|")
    lines+=['','参数、来源、冻结门槛、真实gross/net/保证金、逐月贡献及集中度见RESULTS.json。组合盈利不等于SHORT盈利；净敞口接近0不等于没有风险。未声称稳定APR、Bybit原生或独立投资优势。',
       '', '复现：`python -B scripts/research/run_public_momentum.py --protocol protocols/PUBLIC_CROSS_SECTION_MOMENTUM_20261008.json --state /home/ubuntu/coin/execution-state/public-csmom-20261008-NEW`，经8GB/swap0/GPU0受限scope。需全部源码事前commit。']
    (state/'REPORT.md').write_text('\n'.join(lines)+'\n')
    save(state/'progress.json',dict(status='completed',stage='REPORT',phase='完成',completed=4,total=4,unit='账户',elapsed_seconds=result['elapsed_seconds'],updated_at=time.time(),detail=result['decision']))
    print(json.dumps(dict(status=result['status'],checks=gates,decision=result['decision'])),flush=True)

if __name__=='__main__':main()
