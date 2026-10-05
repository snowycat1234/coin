"""Finite Spot research acceptance; economic non-adoption is a valid result.

References remain separate bound artifacts. Live collection is operational
status, not a prerequisite for an immutable historical wallet audit.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, time
from pathlib import Path
from quant.paths import ROOT, STATE
from quant import resources

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def bound(path):
    p=Path(path);resolved=p.resolve()
    assert not p.is_symlink() and (resolved.is_relative_to(ROOT) or resolved.is_relative_to(STATE))
    return dict(path=str(resolved),sha256=sha(p),bytes=p.stat().st_size)

def read(path):
    bound(path)
    return json.loads(Path(path).read_bytes())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--result',required=True);ap.add_argument('--protocol',required=True)
    ap.add_argument('--financial',required=True);ap.add_argument('--targets',required=True);ap.add_argument('--diagnostic',required=True)
    ap.add_argument('--paired-acceptance',help='Accepted second window for a predeclared joint economic decision')
    ap.add_argument('--output',required=True);a=ap.parse_args();began=time.monotonic()
    v=read(a.result);c=read(a.protocol);f=read(a.financial);t=read(a.targets);d=read(a.diagnostic)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert head==v['git_commit']==c['parent_commit'] and sha(a.protocol)==v['protocol_sha256']
    assert v['status'].startswith('COMPLETE_SPOT_') and v['candidate']=='NONE' and v['investment']=='CASH'
    assert not v['locked_consumed'] and v['orders_sent']==0 and v['new_model_fits']==v['API_calls']==0
    for n,h in c['source_hashes'].items():assert sha(ROOT/n)==h,n
    private=sha(ROOT/'state/dataset_lock.json')
    assert private=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
    assert f['status']=='PASS_INDEPENDENT_SAVED_SPOT_WALLETS_NOT_NATIVE_OR_ALPHA_CERTIFICATION'
    assert t['status'].startswith('PASS_') and d['status']=='PASS_SAVED_SPOT_ASSET_MONTH_NET_AND_COST_BRIDGES'
    target=t.get('actual_reference',t.get('actual_target_reference',t))
    assert target is not None and all(x['input_sha256']==sha(a.result) for x in (f,d,target))
    assert target['target_rows']==v['target_artifact']['rows'] and target['target_max_error']<=1e-12
    if 'current_sources' in t:
        assert t['current_sources']['shared']==sha(ROOT/'scripts/investment/public_sma_perpetual.py')
        assert t['current_sources']['donchian']==sha(ROOT/'scripts/investment/donchian_daily_pool_target.py')
    else:assert t['current_source_sha256']==sha(ROOT/'scripts/investment/public_sma_perpetual.py')
    for case,audit in zip(v['cases'],f['cases'],strict=True):
        assert case['id']==audit['id'] and case['symbols']==c['symbols']
        assert case['config']['initial_cash']==10000 and case['risk']['observed_caps_ok']
        assert audit['full_saved_minute_risk']['rows']==v['actual_calendar_days']*1440
        assert audit['full_saved_minute_risk']['gross_above_cap_rows']==audit['full_saved_minute_risk']['any_asset_above_cap_rows']==0
        for receipt in case['artifacts'].values():assert bound(receipt['path'])['sha256']==receipt['sha256']
    assert v['owned_bytes']<=c['budget']['owned_bytes'] and v['elapsed_seconds']<=c['budget']['wall_seconds']
    # This policy is predeclared in this research family's protocol. It does
    # not restrict evidence acceptance to either profitable or losing cases.
    adopt=all(x['net_delta_USDT']>0 and x['challenger_daily_vol']<=x['control_daily_vol']
              and x['challenger_minute_MDD']<=x['control_minute_MDD'] for x in v['comparisons'])
    per_window_policy_pass=adopt
    if a.paired_acceptance:
        peer=read(a.paired_acceptance)
        assert peer['status']=='ACTUAL_SPOT_RESEARCH_ACCEPTED' and peer['parent_commit']==head
        for r in peer['references'].values():assert sha(r['path'])==r['sha256']
        other=read(peer['references']['result']['path'])
        assert other['recipe']==v['recipe'] and other['git_commit']==head
        assert other['cases'][0]['symbols']==v['cases'][0]['symbols']
        assert other['cases'][0]['fee_snapshot']==v['cases'][0]['fee_snapshot']
        for name in ('src/quant/backtest.py','scripts/investment/hold_donchian_blend_target.py',
                     'scripts/investment/spot_perpetual_product_comparison.py',
                     'scripts/investment/public_sma_perpetual.py'):
            assert other['source_hashes'][name]==v['source_hashes'][name]
        lhs,rhs=v['cases'][0]['config'],other['cases'][0]['config']
        assert lhs['end_us']<=rhs['start_us'] or rhs['end_us']<=lhs['start_us']
        assert [x['id'] for x in other['cases']]==[x['id'] for x in v['cases']]
        adopt=adopt and peer['development_recipe_adopted']
    live=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x]
            if len(argv)==5 and argv[0]==str(ROOT/'.venv/bin/python') and argv[1:3]==['-u','-m'] and argv[3] in ('quant.microstructure','quant.collector_public_v3'):
                live.append(dict(pid=int(p.name),argv=argv,cgroup=(p/'cgroup').read_text().strip()))
        except (OSError,UnicodeError):pass
    out=Path(a.output);assert out.resolve().is_relative_to(ROOT/'reports') and not out.exists()
    value=dict(status='ACTUAL_SPOT_RESEARCH_ACCEPTED',experiment_id=c['experiment_id'],parent_commit=head,
        task_id=os.environ['COIN_TASK_ID'],references={k:bound(p) for k,p in dict(result=a.result,protocol=a.protocol,
            financial=a.financial,targets=a.targets,diagnostic=a.diagnostic).items()},
        source_hashes=c['source_hashes'],development_recipe_adopted=adopt,candidate='NONE',investment='CASH',
        per_window_policy_pass=per_window_policy_pass,
        economic_decision_scope='PAIRED_WINDOWS' if a.paired_acceptance else 'THIS_WINDOW_ONLY',
        long_term_APR='NOT_EVALUABLE',collector_operational_snapshot=live,
        collector_scope='POINT_IN_TIME_NOT_OFFLINE_ACCEPTANCE_GATE_OR_FORWARD_QUALIFICATION',
        private_SHA_only=private,private_body_read=False,resources=resources.status(),
        elapsed_seconds=time.monotonic()-began,validator_source_sha256=sha(__file__))
    if a.paired_acceptance:value['references']['paired_acceptance']=bound(a.paired_acceptance)
    with out.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(status=value['status'],adopted=adopt,collector_count=len(live),elapsed_seconds=value['elapsed_seconds'])))

if __name__=='__main__':main()
