"""Metadata refusal tests only; real control accounts retain their own audits."""
import copy,json
from pathlib import Path
import pytest
from scripts.investment.reuse_cycle_controls import load,sha

def fixture(tmp_path):
    root=tmp_path/'root';state=tmp_path/'state'
    (root/'reports/fast_research').mkdir(parents=True);(state/'task-progress').mkdir(parents=True)
    (root/'docs/input_evidence').mkdir(parents=True)
    fee=root/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json';fee.write_text('fixture only')
    core=root/'core.py';core.write_text('fixture core')
    spec={k:k for k in ('data_manifest','locked_sha256','preparation_start','economics_start','economics_end_exclusive',
        'cost','cost_ids','resources','input_adapter','source_acceptance','cycle_regression')}
    spec['symbols']=['BTCUSDT'];cases=[]
    for family,mode in [('CASH','CASH'),('HOLD','LONG_ONLY')]:
        for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
            p=state/(family+unit);p.write_text('fixture bytes, not an actual account')
            cases.append(dict(strategy=family,mode=mode,cost='BASE27',unit=unit,
                summary=dict(completion='COMPLETE_CONDITIONAL_ACCOUNT',completed_minutes=1051200,required_minutes=1051200,
                    terminal_cash_realized=True,symbols=['BTCUSDT'],contract=dict(cost_provenance=dict(fee_source_ref=str(fee),fee_source_sha256=sha(fee)))),
                independent=dict(maximum_NAV_error_USDT=0.,maximum_wallet_error_USDT=0.),
                artifacts={'fixture':dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)}))
    cases += [dict(strategy='OTHER') for _ in range(6)]
    source=root/'reports/fast_research/source.json'
    source.write_text(json.dumps(dict(status='COMPLETE_FROZEN_CTA_10_ACTUAL_ACCOUNTS_OR_EXPLICIT_HALTS',
        binding=dict(task_id='fixture',source_hashes={'core.py':sha(core)}),protocol=spec,cases=cases)))
    (state/'task-progress/task-fixture.json').write_text(json.dumps(dict(status='completed',exit_code=0)))
    spec=copy.deepcopy(spec);spec['reused_cycle_controls']=dict(path='reports/fast_research/source.json',sha256=sha(source))
    return spec,{'core.py':sha(core)},root,state,fee,cases

def test_control_identity_refuses_changed_window_cost_risk_and_bytes(tmp_path):
    spec,hashes,root,state,fee,cases=fixture(tmp_path)
    controls,proof=load(spec,hashes,root=root,state=state)
    assert len(controls)==4 and proof['producer_task_id']=='fixture'
    for key in ('symbols','economics_start','cost','resources'):
        bad=copy.deepcopy(spec);bad[key]=['ETHUSDT'] if key=='symbols' else 'changed'
        with pytest.raises(AssertionError):load(bad,hashes,root=root,state=state)
    artifact=Path(cases[0]['artifacts']['fixture']['path']);artifact.write_text('changed account bytes')
    with pytest.raises(AssertionError):load(spec,hashes,root=root,state=state)

def test_control_identity_refuses_changed_fee_and_nonterminal_producer(tmp_path):
    spec,hashes,root,state,fee,_=fixture(tmp_path)
    task=state/'task-progress/task-fixture.json';task.write_text(json.dumps(dict(status='running',exit_code=0)))
    with pytest.raises(AssertionError):load(spec,hashes,root=root,state=state)
    task.write_text(json.dumps(dict(status='completed',exit_code=0)));fee.write_text('changed fee snapshot')
    with pytest.raises(AssertionError):load(spec,hashes,root=root,state=state)


def test_recipe_change_cannot_exempt_a_financial_source(tmp_path):
    spec,hashes,root,state,fee,_=fixture(tmp_path)
    (root/'core.py').write_text('new financial semantics')
    new_hash=sha(root/'core.py')
    spec.update(families=['SMA200_SHORT50'],legacy_signal_golden={'fixture':'not actual proof'},
        recipe_source_changes={'core.py':dict(previous=hashes['core.py'],current=new_hash)})
    with pytest.raises(AssertionError):load(spec,{'core.py':new_hash},root=root,state=state)
