"""Saved repaired-policy readback; independent Decimal costs and net bootstrap."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch

from .run import sha, write_json
from .cost_training import ARMS, SEEDS, model_outputs, arm_inputs
from .sharpe import PositionLSTM, scored_sharpe, InvalidScore
from .audit_cost_training import decimal_path, direct_bootstrap, verify_source_rows, verify_decision
from .repaired_cost import load, preservation
from .repaired_data import evaluation_blocks


def audit(state, config_sha):
    config, artifacts, ep, identity=load(config_sha)
    result=json.loads((state/'RESULT.json').read_text())
    if result['config_sha256']!=config_sha or result['training_identity']!=identity:
        raise ValueError('Result/data identity differs')
    stop=json.loads((state/'TRAINING_STOP.json').read_text())
    assert stop['updates']==384 and stop['fits']==6 and stop['validation_calls']==0
    assert result['actual_counts']['new_updates']==384 and len(result['fits'])==6
    before=preservation();assert before==result['preservation']
    _,returns,vol,blocks,_=evaluation_blocks(artifacts['DATA_REPAIR.json'], artifacts['FROZEN_TRAINING.json'])
    rows=list(csv.DictReader((state/'POSITIONS.csv').open()))
    days=list(csv.DictReader((state/'DAILY.csv').open()))
    assert len(rows)==2415 and len(days)==3864
    assert sha((state/'POSITIONS.csv').read_bytes())==result['positions_sha256']
    assert sha((state/'DAILY.csv').read_bytes())==result['daily_sha256']
    verify_source_rows(rows,blocks,returns,vol)
    readbacks=0;model_residual=0.;initials={}
    for fit in result['fits']:
        arm,seed=fit['arm'],fit['seed'];path=state/fit['checkpoint_file']
        assert sha(path.read_bytes())==fit['checkpoint_sha256']
        cp=torch.load(path,weights_only=False,map_location='cpu')
        assert cp['updates']==64 and cp['seed']==seed and cp['arm']==arm
        assert cp['source_commit']==result['source_commit'] and cp['config_sha256']==config_sha and cp['training_identity']==identity
        assert sorted({int(v['step']) for v in cp['optimizer']['state'].values()})==fit['adam_ages']==[64]
        group=cp['optimizer']['param_groups'][0]
        assert group['lr']==.001 and group['betas']==(.9,.999) and group['eps']==1e-8 and group['weight_decay']==0
        torch.manual_seed(seed);model=PositionLSTM()
        digest=sha(b''.join(v.numpy().tobytes() for v in model.state_dict().values()))
        assert digest==fit['initial_sha256'];initials[(arm,seed)]=digest
        model.load_state_dict(cp['model']);model.eval()
        for block in blocks:
            subset=[r for r in rows if r['block']==block['dates'][0]]
            expected=np.array([float(r[f'{arm}_seed{seed}']) for r in subset]).reshape(block['mask'].shape)
            actual=np.zeros(expected.shape);actual[block['mask']]=model_outputs(model,arm_inputs(block['x'],arm)).numpy()
            error=float(np.abs(actual-expected).max());model_residual=max(model_residual,error)
            assert error<=1e-12;readbacks+=1
    for seed in SEEDS:assert initials[('trend',seed)]==initials[('trend_cpd',seed)]
    for row in rows:
        for arm in ARMS:
            assert abs(float(row[arm+'_ensemble'])-sum(float(row[f'{arm}_seed{s}']) for s in SEEDS)/3)<1e-15
            if row['eligible']=='0':assert all(float(row[f'{arm}_seed{s}'])==0 for s in SEEDS)
    policies=[a+'_'+s for a in ARMS for s in ('seed2001','seed2002','seed2003','ensemble')]
    allseries={};joint=[];checks=0;residual=0.
    for block in result['blocks']:
        subset=[r for r in rows if r['block']==block['start']];current={}
        for policy in policies:
            net,gross,cost=decimal_path(subset,policy)
            current[policy]=net;allseries.setdefault(policy,[]).append(net)
            saved=np.array([float(r['fixed_cost_adjusted_price_proxy']) for r in days if r['block']==block['start'] and r['policy']==policy])
            error=float(np.abs(net-saved).max());residual=max(residual,error);assert error<1e-13
            stats=block['policies'][policy];financial=stats['financial']
            for actual,key in [(net,'fixed_cost_adjusted_price_proxy'),(gross,'gross_price_proxy'),(cost,'fixed_cost_total')]:
                assert abs(float(actual.sum())-financial[key])<1e-13
            try:sr=scored_sharpe(net)
            except InvalidScore:sr=None
            assert sr is None and stats['net_price_cost_sharpe'] is None or sr is not None and abs(sr-stats['net_price_cost_sharpe'])<1e-10
            checks+=len(net)+3
        joint.append(np.column_stack([current[a+'_ensemble'] for a in ARMS]))
    for policy in policies:
        net=np.concatenate(allseries[policy]);stats=result['aggregate'][policy]
        assert abs(float(net.sum())-stats['financial']['fixed_cost_adjusted_price_proxy'])<1e-13
        try:sr=scored_sharpe(net)
        except InvalidScore:sr=None
        assert sr is None and stats['net_price_cost_sharpe'] is None or sr is not None and abs(sr-stats['net_price_cost_sharpe'])<1e-10
    ci,invalid=direct_bootstrap(joint)
    assert invalid==result['bootstrap']['invalid_indices']
    if ci is None:assert result['bootstrap']['ci95'] is None
    else:np.testing.assert_allclose(ci,result['bootstrap']['ci95'],rtol=0,atol=1e-10)
    position_abs=np.array([abs(float(r['trend_cpd_ensemble'])) for r in rows if r['eligible']=='1'])
    verify_decision(result,allseries,joint,ci,invalid,position_abs)
    assert preservation()==before
    return dict(status='PASS',config_sha256=config_sha,result_sha256=sha((state/'RESULT.json').read_bytes()),
        model_block_readbacks=readbacks,max_model_prediction_residual=model_residual,
        independent_Decimal_daily_and_summary_checks=checks,max_Decimal_daily_residual=residual,
        bootstrap='Direct portfolio net-series,1000joint14-day draws after costs; no retrades or invalid draw dropping',
        paired_initialization='ALL_THREE_BYTE_IDENTICAL_FRESH',adam_ages='ALL_SIX64',
        data_refreeze='Exact new repair/GP/scaler/calendar SHA bound; no future-fit or mask change',
        new_updates=0,new_wallets=0,replay_scope='18same-policy audit inference sets;0new policy selection or scientific export')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--config-sha',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();value=audit(a.state,a.config_sha);write_json(a.output,value);print(json.dumps(value))
