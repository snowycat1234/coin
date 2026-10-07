"""One pool-only contrast, two wallets, no fits or parameter search."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path

import numpy as np

from modules.transformer_v3.market_binding import verify_binding
from modules.transformer_v3.wallet import run_tasks
from scripts.research.public_cross_section_momentum import public_targets,DAY_US
from scripts.research.run_public_momentum import ROOT,load_past_inputs,save,sha,summary_row


def verify_pool_only(old,new):
    """Allow only the pool/derived targets and their protocol/state identities."""
    a,b=old['task'],new['task']
    assert {k:v for k,v in a['window'].items() if k!='active_symbols'}=={k:v for k,v in b['window'].items() if k!='active_symbols'}
    assert set(b['window']['active_symbols'])<set(a['window']['active_symbols'])
    for key in ('work','collector_root','source_run','funding_scale','profile','mapping','family','seed'):
        assert a[key]==b[key],key
    for key in ('contract','cost_scenario','unit_scenario','symbols'):
        assert old['summary'][key]==new['summary'][key],key
    for key in ('wallet_source_sha256','storage_source_sha256','observed_mark_reference_sha256','financial_sources','frozen_wallet_sources'):
        assert old['binding'][key]==new['binding'][key],key


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    began=time.monotonic();p=json.loads(a.protocol.read_text());state=a.state.resolve()
    assert os.uname().sysname=='Linux' and state.is_relative_to(Path('/home/ubuntu/coin/execution-state'))
    assert p['budget']['new_wallets']==2 and p['budget']['new_fits']==0
    for src in [Path(__file__),a.protocol,ROOT/'scripts/research/run_public_momentum.py',ROOT/'scripts/research/public_cross_section_momentum.py']:
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+str(src.resolve().relative_to(ROOT))])).hexdigest()==sha(src)
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8000000000 and (group/'memory.swap.max').read_text().strip()=='0'
    state.mkdir(exist_ok=True);free_before=shutil.disk_usage(state).free;assert free_before>=p['budget']['reserve_bytes']
    parent_path=ROOT/p['parent_protocol'];results_path=ROOT/p['parent_results']
    assert sha(parent_path)==p['parent_protocol_sha256'] and sha(results_path)==p['parent_results_sha256']
    parent=json.loads(parent_path.read_text());old_results=json.loads(results_path.read_text())
    assert parent['data_manifest_sha256']==p['data_manifest_sha256'] and parent['method']==p['method']
    window=dict(parent['windows'][1],active_symbols=parent['windows'][0]['active_symbols'])
    assert window==p['window'] and window['end']<=parent['locked_start_us']
    assert old_results['protocol_sha256']==sha(parent_path)
    def progress(completed,failed,total,detail):
        save(state/'progress.json',dict(status='running',stage='BACKTEST',phase='固定五币共享钱包',completed=completed,failed=failed,total=total,unit='账户',detail=detail,
                                      elapsed_seconds=time.monotonic()-began,pid=os.getpid(),updated_at=time.time()))
    progress(0,0,2,'DATA: verify paired market, cost and source identities')
    close,available,inputs=load_past_inputs(parent)
    assert inputs==old_results['input_refs']
    dates=np.arange(window['start'],window['end'],DAY_US,dtype=np.int64)
    weights,diagnostics=public_targets(close,available,dates,parent['symbols'],window['active_symbols'],anchor_us=parent['method']['anchor_us'])
    original_weights,_=public_targets(close,available,dates,parent['symbols'],parent['windows'][1]['active_symbols'],anchor_us=parent['method']['anchor_us'])
    excluded=[j for j,s in enumerate(parent['symbols']) if s not in window['active_symbols']]
    assert not np.any(weights[:,excluded])
    target=state/'core5-target.npz'
    if target.exists():
        with np.load(target,allow_pickle=False) as f:assert np.array_equal(f['weights'],weights) and np.array_equal(f['decision_us'],dates) and f['symbol_order'].tolist()==parent['symbols']
    else:np.savez_compressed(target,weights=weights,decision_us=dates,symbol_order=np.array(parent['symbols']))
    save(state/'TARGET_DIAGNOSTICS.json',dict(target_sha256=sha(target),diagnostics=diagnostics,excluded_columns_zero=True))
    print('[DATA] 10/10 SHA and past-only clocks verified; [TARGET] fixed core5, 181 daily rows',flush=True)
    tasks=[];paired={};market_identity=None
    for scale in parent['funding_scales']:
        row=next(x for x in old_results['cases'] if x['window']==window['id'] and x['funding_scale']==scale)
        old_path=Path(row['result_path']);assert sha(old_path)==row['result_sha256']
        old=json.loads(old_path.read_text());assert old['task']['window']==parent['windows'][1] and sha(old['task']['target_path'])==old['task']['target_sha256']
        with np.load(old['task']['target_path'],allow_pickle=False) as f:
            assert np.array_equal(f['weights'],original_weights) and np.array_equal(f['decision_us'],dates) and f['symbol_order'].tolist()==parent['symbols']
        checked=summary_row(old,old_path,'NEW_FIXED_PUBLIC_ADAPTATION')
        assert all(row[key]==value for key,value in checked.items())
        market=verify_binding(old['task']['native_market_binding_path'],old['task']['native_market_binding_sha256'])
        for name,digest in old['binding']['frozen_wallet_sources'].items():assert sha(ROOT/name)==digest
        if market_identity is None:market_identity=market
        else:assert market==market_identity
        task=dict(old['task'],state=str(state),window=window,target_path=str(target),target_sha256=sha(target),protocol_sha256=sha(a.protocol))
        for key in ('mark_reference','native_market_binding_path','native_market_binding_sha256'):task.pop(key)
        tasks.append(task);paired[scale]=old
    cases=run_tasks(tasks,state,'CORE5_POOL',workers=2,protocol_path=a.protocol,on_progress=progress)
    rows=[]
    for case in cases:
        old=paired[case['task']['funding_scale']];verify_pool_only(old,case)
        market=verify_binding(case['task']['native_market_binding_path'],case['task']['native_market_binding_sha256'])
        assert {k:v for k,v in market.items() if k!='window'}=={k:v for k,v in market_identity.items() if k!='window'}
        row=summary_row(case,state/'native'/case['task']['id']/'RESULT.json','NEW_CORE5_POOL_ONLY_CONTRAST')
        row['paired_core6_net_PnL']=old['summary']['net_PnL'];row['net_gap_vs_core6']=row['net_PnL']-row['paired_core6_net_PnL']
        rows.append(row)
    checks=dict(both_net_positive=all(x['net_PnL']>0 for x in rows),both_short_positive=all(x['contributions']['SHORT']['net_contribution']>0 for x in rows),
                both_vol_at_most12pct=all(x['daily_metrics']['annual_volatility']<=.12 for x in rows),both_minute_MDD_at_most12pct=all(x['minute_MDD']<=.12 for x in rows))
    owned=sum(q.stat().st_size for q in state.rglob('*') if q.is_file());assert owned<=p['budget']['new_owned_bytes'] and time.monotonic()-began<=p['budget']['wall_seconds']
    result=dict(status='COMPLETE_CORE5_POOL_ONLY_DEVELOPMENT_CONTRAST',protocol=p,protocol_sha256=sha(a.protocol),source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),
                cases=sorted(rows,key=lambda x:x['funding_scale']),checks=checks,decision='RETAIN_CORE_POOL_DEVELOPMENT_CLUE' if all(checks.values()) else 'NO_CORE_POOL_GENERALIZATION',
                original_full_recipe_remains_paused=True,qualification='NONE_CASH',new_wallets=2,new_fits=0,paired_wallets_reused=2,locked_consumed=False,
                elapsed_seconds=time.monotonic()-began,owned_bytes=owned,free_bytes_before=free_before,free_bytes_after=shutil.disk_usage(state).free,
                RAM_limit=(group/'memory.max').read_text().strip(),swap_limit=(group/'memory.swap.max').read_text().strip(),GPU=0,
                RAM_group_peak_bytes=int((group/'memory.peak').read_text()) if (group/'memory.peak').exists() else None,
                RAM_group_peak_status='AVAILABLE' if (group/'memory.peak').exists() else 'UNKNOWN_KERNEL_COUNTER_ABSENT',
                limitations=p['limitations'])
    save(state/'RESULTS.json',result)
    lines=['# 固定五币池：单因素完整钱包对照','',f"决定 {result['decision']}；投资NONE/CASH。仅改变币池，两个新账户/零拟合，原配方仍暂停。",'',
           '|资金费解释|五币净PnL|原六币净PnL|差额|LONG净|SHORT净|波动|分钟MDD|费/执行/资金费|换手|',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for x in result['cases']:
        lines.append(f"|{x['funding_scale']}|{x['net_PnL']:.2f}|{x['paired_core6_net_PnL']:.2f}|{x['net_gap_vs_core6']:.2f}|{x['contributions']['LONG']['net_contribution']:.2f}|{x['contributions']['SHORT']['net_contribution']:.2f}|{x['daily_metrics']['annual_volatility']:.2%}|{x['minute_MDD']:.2%}|{x['fees']:.2f}/{x['execution_cost']:.2f}/{x['funding']:.2f}|{x['turnover']:.2f}|")
    lines+=['','同一2025已见181日、10k共享资本、相同双侧参数/成本/资金单位；池改变会改变排序、协方差和后续钱包，不是从六币结果减去PEPE利润。',
            '旧六币HOLD/SMA不能充作五币同池强控制。仅筛查原2025正收益能否在既有核心池保留，不提供独立/全年或长期APR。真实gross漂移与风险延迟仍按原引擎报告。',
            '', '复现：python -B scripts/research/check_momentum_pool.py --protocol protocols/CSMOM_CORE5_POOL_20261008.json --state /home/ubuntu/coin/execution-state/csmom-core5-20261008-NEW，须已有8GB/swap0/GPU0受限scope。']
    (state/'REPORT.md').write_text('\n'.join(lines)+'\n')
    save(state/'progress.json',dict(status='completed',stage='REPORT',phase='完成',completed=2,total=2,unit='账户',elapsed_seconds=result['elapsed_seconds'],updated_at=time.time(),detail=result['decision']))
    print(json.dumps(dict(status=result['status'],checks=checks,decision=result['decision'])),flush=True)

if __name__=='__main__':main()
