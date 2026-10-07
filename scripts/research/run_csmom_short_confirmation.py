"""One frozen absolute-SHORT confirmation, existing shared wallet and controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import numpy as np

from scripts.research.public_cross_section_momentum import public_targets, DAY_US
from scripts.research.run_public_momentum import ROOT, load_past_inputs, save, sha, summary_row
from modules.transformer_v3.wallet import run_tasks


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--state',type=Path,required=True)
    a=ap.parse_args();began=time.monotonic();p=json.loads(a.protocol.read_text());state=a.state.resolve()
    assert os.uname().sysname=='Linux' and state.parent==Path('/home/ubuntu/coin/execution-state')
    assert p['budget']['new_wallets']==10 and p['budget']['new_fits']==0 and p['funding_scales']==[1,.01]
    assert p['capital']==10000 and p['max_asset_abs']==.3 and p['max_gross']==.6 and p['leverage']==1
    for name in p['input_reports']:assert sha(ROOT/name)==p['input_report_hashes'][name]
    assert sha(ROOT/p['parent_protocol'])==p['parent_protocol_sha256']
    bound=[Path(__file__),a.protocol,ROOT/'scripts/research/public_cross_section_momentum.py',ROOT/'scripts/research/run_public_momentum.py']
    bound += [ROOT/x for x in p['input_reports']]
    for path in bound:
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+str(path.resolve().relative_to(ROOT))])).hexdigest()==sha(path), 'Commit protocol, targets and input evidence before wallets'
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8_000_000_000
    assert (group/'memory.swap.max').read_text().strip()=='0'
    state.mkdir(exist_ok=False);free_before=shutil.disk_usage(state).free;assert free_before>=p['budget']['reserve_bytes']
    from types import SimpleNamespace
    from modules.collector_research.validation import runtime
    base=json.loads((ROOT/p['parent_protocol']).read_text())
    runtime.configure(SimpleNamespace(collector_root=base['collector_root'],collector_work=base['work'],source_run=base['source_run'],
        run_dir=state/'control',resource_policy='server',workers=p['budget']['workers'],minimum_days=30,publish_source_report=False,audit_device='cpu'))
    from modules.collector_research.validation.data import saved_case_valid
    def progress(done,failed,total,detail):
        save(state/'progress.json',dict(status='running',phase='绝对SHORT确认 · 真实共享钱包',completed=done,failed=failed,total=total,
            unit='账户',detail=detail,elapsed_seconds=time.monotonic()-began,pid=os.getpid(),updated_at=time.time()))
    progress(0,0,10,'Verify unchanged baseline targets and source identity before new wallets')
    close,available,refs=load_past_inputs(base)
    indices=[base['symbols'].index(s) for s in p['core_symbols']];close=close[:,indices]
    source_reports=[json.loads((ROOT/name).read_text()) for name in p['input_reports'][:2]]
    baselines=source_reports[0]['reused_csmom_controls']+[x for x in source_reports[1]['cases'] if x['family']=='PUBLIC_CSMOM21_WEEKLY']
    assert len(baselines)==10
    tasks=[];controls=[];target_proofs=[];paired={}
    for w in p['windows']:
        dates=np.arange(w['start'],w['end'],DAY_US,dtype=np.int64)
        old,_=public_targets(close,available,dates,p['core_symbols'],p['core_symbols'])
        confirmed,diag=public_targets(close,available,dates,p['core_symbols'],p['core_symbols'],short_absolute_confirmation=True)
        assert np.all(np.abs(confirmed)<=np.abs(old)+1e-14) and not np.any(confirmed*old < -1e-14)
        full=np.zeros((len(dates),len(p['symbols'])));full[:,indices]=confirmed
        original=np.zeros_like(full);original[:,indices]=old
        path=state/(w['id']+'_targets.npz');np.savez_compressed(path,weights=full,decision_us=dates,symbol_order=np.array(p['symbols']))
        cut=len(dates)//2;changed=close.copy();changed[available>dates[cut]]*=np.arange(2,7)
        perturbed,_=public_targets(changed,available,dates,p['core_symbols'],p['core_symbols'],short_absolute_confirmation=True)
        assert np.array_equal(confirmed[:cut+1],perturbed[:cut+1])
        perm=np.arange(4,-1,-1);reordered,_=public_targets(close[:,perm],available,dates,[p['core_symbols'][i] for i in perm],p['core_symbols'],short_absolute_confirmation=True)
        order_error=float(np.abs(reordered-confirmed[:,perm]).max());assert order_error<=1e-14
        suppressed=np.asarray(diag['short_confirmation_blocked'])
        target_proofs.append(dict(window=w['id'],target_sha256=sha(path),future_suffix_unchanged=True,asset_order_max_error=order_error,
            no_target_leg_increased=True,short_intents_suppressed=int(suppressed.sum()),days_any_suppressed=int(suppressed.any(axis=1).sum()),
            mean_original_gross=float(np.abs(old).sum(1).mean()),mean_confirmed_gross=float(np.abs(confirmed).sum(1).mean()),
            available_us_never_after_decision=all(x is None or x<=t for t,row in zip(dates,diag['feature_available_us']) for x in row)))
        for scale in p['funding_scales']:
            row=next(x for x in baselines if x['window']==w['id'] and x['funding_scale']==scale)
            assert sha(row['result_path'])==row['result_sha256'];case=json.loads(Path(row['result_path']).read_text())
            saved_case_valid(case,case['binding']);task=case['task']
            assert task['window']==w and case['summary']['symbols']==p['symbols'] and task['profile']=='FULL'
            with np.load(task['target_path'],allow_pickle=False) as f:
                assert sha(task['target_path'])==task['target_sha256'] and np.array_equal(f['decision_us'],dates)
                assert f['symbol_order'].tolist()==p['symbols'] and np.array_equal(f['weights'],original), 'Original CSMOM default target changed'
            for name,digest in case['binding']['frozen_wallet_sources'].items():assert sha(ROOT/name)==digest
            controls.append(summary_row(case,Path(row['result_path']),'REUSED_IDENTICAL_FULL_CAPITAL_BASELINE'))
            task=dict(task,id=('raw_fraction' if scale==1 else 'raw_percent')+'/'+w['id']+'/CSMOM21_ABSOLUTE_SHORT',family='CSMOM21_ABSOLUTE_SHORT',
                state=str(state),target_path=str(path),target_sha256=sha(path),protocol_sha256=sha(a.protocol))
            for key in ('mark_reference','native_market_binding_path','native_market_binding_sha256'):task.pop(key)
            tasks.append(task);paired[(w['id'],scale)]=case
        print('[TARGET] '+w['id']+' exact default golden; one fixed confirmation; no fit',flush=True)
    assert len(tasks)==10
    save(state/'TARGET_PROOFS.json',target_proofs)
    cases=run_tasks(tasks,state,'CSMOM_SHORT_CONFIRMATION',workers=p['budget']['workers'],protocol_path=a.protocol,on_progress=progress)
    rows=[];contrasts=[]
    for case in cases:
        key=(case['task']['window']['id'],case['task']['funding_scale']);old=paired[key]
        for field in ('contract','cost_scenario','unit_scenario','symbols'):assert case['summary'][field]==old['summary'][field]
        for field in ('financial_sources','frozen_wallet_sources','wallet_source_sha256','storage_source_sha256'):assert case['binding'][field]==old['binding'][field]
        new=summary_row(case,state/'native'/case['task']['id']/'RESULT.json','NEW_ABSOLUTE_SHORT_CONFIRMATION');rows.append(new)
        baseline=next(x for x in controls if (x['window'],x['funding_scale'])==key)
        contrasts.append(dict(window=key[0],funding_scale=key[1],net_increment=new['net_PnL']-baseline['net_PnL'],
            SHORT_increment=new['contributions']['SHORT']['net_contribution']-baseline['contributions']['SHORT']['net_contribution'],
            LONG_increment=new['contributions']['LONG']['net_contribution']-baseline['contributions']['LONG']['net_contribution'],
            MDD_change=new['minute_MDD']-baseline['minute_MDD'],vol_change=new['daily_metrics']['annual_volatility']-baseline['daily_metrics']['annual_volatility'],
            turnover_change=new['turnover']-baseline['turnover'],cost_change=new['fees']+new['execution_cost']-baseline['fees']-baseline['execution_cost']))
    checks=dict(no_liquidation=all(x['liquidations']==0 for x in rows),all_vol_at_most12pct=all(x['daily_metrics']['annual_volatility']<=.12 for x in rows),
        all_MDD_at_most12pct=all(x['minute_MDD']<=.12 for x in rows),each_pair_net_or_DD_improves=all(x['net_increment']>=0 or x['MDD_change']<0 for x in contrasts),
        at_least8_of10_net_positive=sum(x['net_PnL']>0 for x in rows)>=8,
        both2025_stages_SHORT_positive=all(x['contributions']['SHORT']['net_contribution']>0 for x in rows if x['window'].startswith(('fold3','fold4'))))
    seconds=time.monotonic()-began;owned=sum(x.stat().st_size for x in state.rglob('*') if x.is_file())
    assert seconds<=p['budget']['wall_seconds'] and owned<=p['budget']['new_owned_bytes']
    result=dict(status='COMPLETE_ONE_ABSOLUTE_SHORT_CONFIRMATION',protocol=p,protocol_sha256=sha(a.protocol),source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),
        cases=sorted(rows,key=lambda x:(x['window'],x['funding_scale'])),reused_controls=controls,contrasts=sorted(contrasts,key=lambda x:(x['window'],x['funding_scale'])),
        target_proofs=target_proofs,input_refs=refs,checks=checks,decision='RETAIN_FOR_INDEPENDENT_VALIDATION' if all(checks.values()) else 'PAUSE_EXACT_CONFIRMATION_RECIPE',
        qualification='NONE_CASH',new_wallets=10,new_fits=0,elapsed_seconds=seconds,owned_bytes=owned,free_bytes_before=free_before,free_bytes_after=shutil.disk_usage(state).free,
        RAM_limit_bytes=int((group/'memory.max').read_text()),RAM_true_peak_bytes=int((group/'memory.peak').read_text()) if (group/'memory.peak').exists() else None,swap=0,GPU=0,locked_consumed=False)
    save(state/'RESULTS.json',result)
    save(state/'progress.json',dict(status='completed',phase='完成',completed=10,total=10,unit='账户',detail=result['decision'],elapsed_seconds=seconds,updated_at=time.time()))
    print(json.dumps(dict(status=result['status'],checks=checks,decision=result['decision'],elapsed_seconds=seconds)),flush=True)


if __name__=='__main__':main()
