"""Bind completed CASH/HOLD controls to exactly the same research economics."""
import hashlib,json
from pathlib import Path
from quant.paths import ROOT,STATE

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def load(spec,source_hashes,*,root=ROOT,state=STATE):
    ref=spec['reused_cycle_controls'];path=(root/ref['path']).resolve()
    assert path.is_relative_to(root/'reports/fast_research') and sha(path)==ref['sha256']
    prior=json.loads(path.read_bytes());task=json.loads((state/'task-progress'/('task-'+prior['binding']['task_id']+'.json')).read_bytes())
    assert task['status']=='completed' and task['exit_code']==0
    assert prior['status']=='COMPLETE_FROZEN_CTA_10_ACTUAL_ACCOUNTS_OR_EXPLICIT_HALTS' and len(prior['cases'])==10
    keys=('symbols','data_manifest','locked_sha256','preparation_start','economics_start','economics_end_exclusive',
          'cost','cost_ids','resources','input_adapter','source_acceptance','cycle_regression')
    for key in keys:assert spec[key]==prior['protocol'][key],'Reused control economics changed: '+key
    for p,h in prior['binding']['source_hashes'].items():
        if p=='scripts/investment/run_cta_leaderboard.py':continue
        changes=spec.get('recipe_source_changes',{})
        if p in changes:
            assert p in {'scripts/investment/cta_classics.py','scripts/investment/audit_cta_classics.py','tests/test_cta_classics.py'}
            assert changes[p]==dict(previous=h,current=source_hashes[p]) and sha(root/p)==source_hashes[p]
            assert 'legacy_signal_golden' in spec and spec['families'] in (
                ['SMA200_SHORT50'],['PUBLIC_SMA50_200'],['DONCHIAN20_10','DC_TWO_SPEED'],
                ['ORACLE60D'],['EQUAL_EXPERTS','STATIC_DIRECTION3'])
        else:assert source_hashes[p]==h==sha(root/p),'Reused control source changed: '+p
    controls=[c for c in prior['cases'] if c['strategy'] in ('CASH','HOLD')]
    assert {(c['strategy'],c['mode'],c['cost'],c['unit']) for c in controls}=={
        (family,mode,'BASE27',unit) for family,mode in [('CASH','CASH'),('HOLD','LONG_ONLY')]
        for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT')}
    assert len(controls)==4
    for c in controls:
        s=c['summary'];assert s['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and s['completed_minutes']==s['required_minutes']==1051200
        assert s['terminal_cash_realized'] and s['symbols']==spec['symbols']
        fee=s['contract']['cost_provenance'];fee_path=root/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json'
        assert Path(fee['fee_source_ref'])==fee_path and sha(fee_path)==fee['fee_source_sha256']
        assert c['independent']['maximum_NAV_error_USDT']<1e-7 and c['independent']['maximum_wallet_error_USDT']<1e-7
        for v in c['artifacts'].values():
            p=Path(v['path']).resolve();assert p.is_relative_to(state) and sha(p)==v['sha256'] and p.stat().st_size==v['bytes']
    return controls,dict(**ref,producer_task_id=prior['binding']['task_id'],scope='FOUR_WHOLE_COMPLETE_COUNTERFACTUAL_CONTROLS; NO_WALLET_JOIN; SAME_CAPITAL_INPUT_COST_AND_FINANCIAL_CORE')
