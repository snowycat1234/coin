"""One frozen tail protection; existing targets, wallet, controls and audits."""
import argparse,gzip,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scripts.research.run_public_momentum import ROOT,sha,save,summary_row
from modules.transformer_v3.wallet import run_tasks


def verify_control_sources(old,current,p):
    assert set(current)-set(old)==set(p['added_sources']) and not set(old)-set(current)
    changed={k for k in old if old[k]!=current[k]}
    assert changed<=set(p['source_updates'])
    for k in changed:assert p['source_updates'][k]==dict(old=old[k],current=current[k])
    for k,v in p['added_sources'].items():assert current[k]==v
    return sorted(changed)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--state',type=Path,required=True)
    a=ap.parse_args();began=time.monotonic();p=json.loads(a.protocol.read_text());state=a.state.resolve()
    assert os.uname().sysname=='Linux' and state.parent==Path('/home/ubuntu/coin/execution-state')
    assert p['budget']['new_wallets']==10 and p['budget']['new_fits']==0 and p['funding_scales']==[1,.01]
    assert (p['capital'],p['max_asset_abs'],p['max_gross'],p['leverage'])==(10000,.3,.6,1)
    for k,v in p['input_reports'].items():assert sha(ROOT/k)==v
    paths=list(p['activity_sources'])+[str(a.protocol.resolve().relative_to(ROOT))]
    for name in paths:
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+name])).hexdigest()==sha(ROOT/name)
    cg=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (cg/'memory.max').read_text().strip()!='max' and int((cg/'memory.max').read_text())<=8_000_000_000
    assert (cg/'memory.swap.max').read_text().strip()=='0'
    state.mkdir(exist_ok=False);free_before=shutil.disk_usage(state).free;assert free_before>=p['budget']['reserve_bytes']
    base=json.loads((ROOT/p['parent_protocol']).read_text())
    from modules.collector_research.validation import runtime
    runtime.configure(SimpleNamespace(collector_root=base['collector_root'],collector_work=base['work'],source_run=base['source_run'],
        run_dir=state/'control',resource_policy='server',workers=p['budget']['workers'],minimum_days=30,publish_source_report=False,audit_device='cpu'))
    from modules.collector_research.validation.data import saved_case_valid
    def progress(done,failed,total,detail):
        save(state/'progress.json',dict(status='running',phase='SHORT逐仓保护 · 原信号共享钱包',completed=done,failed=failed,total=total,
            unit='账户',detail=detail,elapsed_seconds=time.monotonic()-began,pid=os.getpid(),updated_at=time.time()))
    progress(0,0,10,'Verify frozen old targets and precise source compatibility')
    evidence=json.loads((ROOT/'reports/CSMOM_ABSOLUTE_SHORT_20261008.json').read_text());original=evidence['reused_controls']
    assert len(original)==10;controls=[];tasks=[];paired={};compat=[]
    current_fin={str(x.relative_to(ROOT)):sha(x) for x in sorted((ROOT/'src/quant').glob('*.py'))+sorted((ROOT/'scripts/investment').glob('*.py'))}
    current_frozen=dict(current_fin,**{x:sha(ROOT/x) for x in ['modules/transformer_v3/wallet.py','modules/transformer_v3/storage.py','modules/transformer_v3/market_reference.py','modules/transformer_v3/market_binding.py','modules/transformer_v3/isolated_audit.py']})
    for row in original:
        assert sha(row['result_path'])==row['result_sha256'];case=json.loads(Path(row['result_path']).read_text())
        saved_case_valid(case,case['binding']);task=case['task'];w=task['window'];scale=task['funding_scale']
        assert w==next(x for x in p['windows'] if x['id']==w['id']) and case['summary']['symbols']==p['symbols'] and task['profile']=='FULL'
        assert sha(task['target_path'])==task['target_sha256']
        with np.load(task['target_path'],allow_pickle=False) as f:
            assert f['symbol_order'].tolist()==p['symbols'] and np.array_equal(f['decision_us'],np.arange(w['start'],w['end'],86_400_000_000))
        financial=verify_control_sources(case['binding']['financial_sources'],current_fin,p)
        frozen=verify_control_sources(case['binding']['frozen_wallet_sources'],current_frozen,p)
        compat.append(dict(window=w['id'],funding_scale=scale,financial_updates=financial,frozen_updates=frozen,liquidations_preserved=row['liquidations']))
        controls.append(summary_row(case,Path(row['result_path']),'REUSED_FROZEN_OLD_DEFAULT_WITH_GOLDEN_CHECKED_OPTIONAL_EXTENSION'))
        t=dict(task,id=('raw_fraction' if scale==1 else 'raw_percent')+'/'+w['id']+'/CSMOM_SHORT_COLLATERAL_HALF',
            family='CSMOM_SHORT_COLLATERAL_HALF',state=str(state),protocol_sha256=sha(a.protocol),position_protection=p['recipe']['id'])
        for field in ('mark_reference','native_market_binding_path','native_market_binding_sha256'):t.pop(field)
        tasks.append(t);paired[(w['id'],scale)]=case
    cases=run_tasks(tasks,state,'SHORT_COLLATERAL',workers=p['budget']['workers'],protocol_path=a.protocol,on_progress=progress)
    rows=[];contrasts=[]
    for case in cases:
        t=case['task'];key=(t['window']['id'],t['funding_scale']);old=paired[key]
        for field in ('contract','cost_scenario','unit_scenario','symbols'):assert case['summary'][field]==old['summary'][field]
        assert case['binding']['position_protection']['id']==p['recipe']['id']
        entry=case['artifacts']['protection_journal.json'];assert sha(entry['path'])==entry['sha256']
        raw=gzip.decompress(Path(entry['path']).read_bytes());assert hashlib.sha256(raw).hexdigest()==entry['uncompressed_sha256']
        journal=json.loads(raw)
        new=summary_row(case,state/'native'/t['id']/'RESULT.json','NEW_FIXED_SHORT_COLLATERAL_PROTECTION')
        new['protection_events']={kind:sum(x['kind']==kind for x in journal) for kind in ('OBSERVED_SHORT_COLLATERAL_FLOOR','PROTECTIVE_FILL','ORIGINAL_SHORT_SIGNAL_RESET')}
        rows.append(new);b=next(x for x in controls if (x['window'],x['funding_scale'])==key)
        contrasts.append(dict(window=key[0],funding_scale=key[1],net_increment=new['net_PnL']-b['net_PnL'],
            SHORT_increment=new['contributions']['SHORT']['net_contribution']-b['contributions']['SHORT']['net_contribution'],
            LONG_increment=new['contributions']['LONG']['net_contribution']-b['contributions']['LONG']['net_contribution'],
            MDD_change=new['minute_MDD']-b['minute_MDD'],vol_change=new['daily_metrics']['annual_volatility']-b['daily_metrics']['annual_volatility'],
            cost_change=new['fees']+new['execution_cost']-b['fees']-b['execution_cost'],turnover_change=new['turnover']-b['turnover']))
    checks=dict(no_liquidation=all(x['liquidations']==0 for x in rows),all_vol_at_most12pct=all(x['daily_metrics']['annual_volatility']<=.12 for x in rows),
        all_MDD_at_most12pct=all(x['minute_MDD']<=.12 for x in rows),each_pair_net_or_DD_improves=all(x['net_increment']>=-1e-7 or x['MDD_change']<=-.0001 for x in contrasts),
        any_material_net_or_DD_improvement=any(x['net_increment']>=10 or x['MDD_change']<=-.001 for x in contrasts),
        both2025_stages_SHORT_positive=all(x['contributions']['SHORT']['net_contribution']>0 for x in rows if x['window'].startswith(('fold3','fold4'))))
    seconds=time.monotonic()-began;owned=sum(x.stat().st_size for x in state.rglob('*') if x.is_file())
    assert seconds<=p['budget']['wall_seconds'] and owned<=p['budget']['new_owned_bytes']
    out=dict(status='COMPLETE_ONE_SHORT_COLLATERAL_PROTECTION',protocol=p,protocol_sha256=sha(a.protocol),source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),
        cases=sorted(rows,key=lambda x:(x['window'],x['funding_scale'])),reused_controls=controls,contrasts=sorted(contrasts,key=lambda x:(x['window'],x['funding_scale'])),
        source_compatibility=compat,checks=checks,decision='RETAIN_TAIL_PROTECTION_FOR_INDEPENDENT_VALIDATION' if all(checks.values()) else 'PAUSE_EXACT_TAIL_PROTECTION_RECIPE',
        qualification='NONE_CASH',new_wallets=10,new_fits=0,elapsed_seconds=seconds,owned_bytes=owned,free_bytes_before=free_before,free_bytes_after=shutil.disk_usage(state).free,
        RAM_limit_bytes=int((cg/'memory.max').read_text()),RAM_true_peak_bytes=int((cg/'memory.peak').read_text()) if (cg/'memory.peak').exists() else None,swap=0,GPU=0,locked_consumed=False)
    save(state/'RESULTS.json',out);save(state/'progress.json',dict(status='completed',phase='完成',completed=10,total=10,unit='账户',detail=out['decision'],elapsed_seconds=seconds,updated_at=time.time()))
    print(json.dumps(dict(status=out['status'],checks=checks,decision=out['decision'],seconds=seconds)),flush=True)


if __name__=='__main__':main()
