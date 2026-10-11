"""Independent Decimal saved-policy audit plus terminal model readback, no fits."""
import argparse
import csv
import json
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
import torch

from .cost_training import (EXPERIMENT, ARMS, SEEDS, PROPOSAL_SHA, load_config,
                            train_episode, episode_identity, arm_inputs, model_outputs)
from .objective_diagnostic import verify_evidence
from .run import sha, write_json, utc_us
from .sharpe import PositionLSTM, prepare, scored_sharpe, InvalidScore
from .core import DAY_US, SYMBOLS


def decimal_path(rows, policy):
    """Independent ordered carry/fill ledger; actual costs before any resampling."""
    with localcontext() as ctx:
        ctx.prec=50
        D=lambda value:Decimal(str(value))
        rate=D(.15/np.sqrt(365));fee=D('.00055');spread=D('.0004');slip=D('.0004')
        carry=[Decimal(0)]*5;net=[];gross=[];costs=[]
        for begin in range(0,len(rows),5):
            g,c=Decimal(0),Decimal(0)
            for a,row in enumerate(rows[begin:begin+5]):
                active=row['eligible']=='1'
                w=rate*D(row[policy])/D(row['daily_vol'])/5 if active else Decimal(0)
                r=D(row['scaled_next_return'])*D(row['daily_vol'])/rate if active else Decimal(0)
                trade=w-carry[a]
                # Fee on adverse fill notional, spread and slip paid once.
                c+=(spread+slip)*abs(trade)+fee*(abs(trade)+(spread+slip)*trade)
                g+=w*r;carry[a]=w*(1+r)
            gross.append(float(g));costs.append(float(c));net.append(float(g-c))
        terminal=sum((spread+slip)*abs(-v)+fee*(abs(-v)+(spread+slip)*(-v)) for v in carry)
        costs[-1]+=float(terminal);net[-1]-=float(terminal)
        return np.asarray(net),np.asarray(gross),np.asarray(costs)


def direct_bootstrap(blocks):
    rng=np.random.default_rng(9901);deltas=[];invalid=[]
    for replicate in range(1000):
        pieces=[]
        for pair in blocks:
            starts=rng.integers(0,len(pair)-13,size=int(np.ceil(len(pair)/14)))
            index=np.concatenate([np.arange(start,start+14) for start in starts])[:len(pair)]
            pieces.append(pair[index])
        draw=np.concatenate(pieces)
        try:deltas.append(scored_sharpe(draw[:,1])-scored_sharpe(draw[:,0]))
        except InvalidScore:invalid.append(replicate)
    return None if invalid else np.quantile(deltas,[.025,.975]).tolist(),invalid


def verify_source_rows(rows, blocks, returns, vol):
    for block in blocks:
        subset=[row for row in rows if row['block']==block['dates'][0]]
        assert len(subset)==len(block['clock'])*5
        for index,row in enumerate(subset):
            date,a=divmod(index,5);t=block['times'][date]
            assert row['symbol']==SYMBOLS[a] and int(row['available_us'])==int(block['clock'][date])
            assert int(row['label_end_us'])==int(block['clock'][date]+DAY_US)<utc_us(block['dates'][1])
            assert int(row['eligible'])==int(block['mask'][date,a])
            risk=vol[t,a]
            if np.isfinite(risk):assert float(row['daily_vol'])==risk
            else:assert row['daily_vol']==''
            observed=np.isfinite(returns[t+1,a]) and np.isfinite(risk) and risk>0
            if observed:assert abs(float(row['scaled_next_return'])-(.15/np.sqrt(365))*returns[t+1,a]/risk)<1e-15
            else:assert row['scaled_next_return']==''


def verify_decision(result, allseries, joint, ci, invalid, positions):
    def score(name):
        try:return scored_sharpe(np.concatenate(allseries[name]))
        except InvalidScore:return None
    def diff(left,right):return None if left is None or right is None else right-left
    delta=diff(score('trend_ensemble'),score('trend_cpd_ensemble'))
    seeds=[diff(score(f'trend_seed{s}'),score(f'trend_cpd_seed{s}')) for s in SEEDS]
    byblock=[]
    for pair in joint:
        try:byblock.append(scored_sharpe(pair[:,1])-scored_sharpe(pair[:,0]))
        except InvalidScore:byblock.append(None)
    for actual,saved in [(delta,result['aggregate_ensemble_increment'])]+list(zip(seeds,result['seed_increments'],strict=True))+list(zip(byblock,result['block_ensemble_increments'],strict=True)):
        assert actual is None and saved is None or actual is not None and saved is not None and abs(actual-saved)<1e-10
    gates=dict(absolute_CPD_cost_adjusted_positive=bool(np.concatenate(allseries['trend_cpd_ensemble']).sum()>0),
               aggregate_net_sharpe_increment_positive=delta is not None and delta>0,
               all_three_blocks_increment_positive=all(x is not None and x>0 for x in byblock),
               at_least_two_seeds_increment_positive=sum(x is not None and x>0 for x in seeds)>=2,
               conditional_bootstrap_lower_positive=not invalid and ci is not None and ci[0]>0)
    assert gates==result['gates'] and result['all_frozen_statistical_gates_pass']==all(gates.values())
    near=bool(positions.mean()<.001 or (positions<.001).mean()>=.99)
    assert near==result['near_cash_flag']
    valid=True
    for parts in allseries.values():
        for values in parts+[np.concatenate(parts)]:
            try:scored_sharpe(values)
            except InvalidScore:valid=False
    assert valid==result['all_required_scores_valid']
    assert result['decision']==('PASS_PROXY_GATES_ONLY_NO_WALLET' if all(gates.values()) and not near and valid else 'STOP_NO_FURTHER_RECIPE')


def audit(state, config_sha):
    load_config(config_sha)
    result=json.loads((state/'RESULT.json').read_text())
    assert result['config_sha256']==config_sha and result['proposal_sha256']==PROPOSAL_SHA
    assert result['actual_counts']['new_updates']==384 and len(result['fits'])==6
    stop=json.loads((state/'TRAINING_STOP.json').read_text())
    assert stop['fits']==6 and stop['updates']==384 and stop['validation_calls']==0
    before=verify_evidence()
    ep=train_episode();assert episode_identity(ep)==result['training_identity']
    _,available,returns,vol,_,_,_,blocks,_=prepare(Path('/workspace/slow-momentum-state/source/features.zip'))
    rows=list(csv.DictReader((state/'POSITIONS.csv').open()))
    days=list(csv.DictReader((state/'DAILY.csv').open()))
    assert len(rows)==2415 and len(days)==3864
    assert sha((state/'POSITIONS.csv').read_bytes())==result['positions_sha256']
    assert sha((state/'DAILY.csv').read_bytes())==result['daily_sha256']
    verify_source_rows(rows,blocks,returns,vol)
    infer=0;max_prediction_error=0.;paired={};fits={}
    for fit in result['fits']:
        arm,seed=fit['arm'],fit['seed'];path=state/fit['checkpoint_file']
        assert sha(path.read_bytes())==fit['checkpoint_sha256']
        cp=torch.load(path,weights_only=False,map_location='cpu')
        assert cp['updates']==64 and cp['seed']==seed and cp['arm']==arm
        assert cp['source_commit']==result['source_commit'] and cp['config_sha256']==config_sha
        assert cp['training_identity']==result['training_identity']
        ages=sorted({int(v['step']) for v in cp['optimizer']['state'].values()})
        assert ages==fit['adam_ages']==[64]
        group=cp['optimizer']['param_groups'][0]
        assert group['lr']==.001 and group['betas']==(.9,.999) and group['eps']==1e-8 and group['weight_decay']==0
        torch.manual_seed(seed);model=PositionLSTM()
        initial=sha(b''.join(v.numpy().tobytes() for v in model.state_dict().values()))
        assert initial==fit['initial_sha256'];paired[(arm,seed)]=initial
        model.load_state_dict(cp['model']);model.eval();fits[(arm,seed)]=fit
        for block in blocks:
            subset=[row for row in rows if row['block']==block['dates'][0]]
            expected=np.array([float(row[f'{arm}_seed{seed}']) for row in subset]).reshape(len(block['clock']),5)
            actual=np.zeros(expected.shape);actual[block['mask']]=model_outputs(model,arm_inputs(block['x'],arm)).numpy()
            error=float(np.max(np.abs(actual-expected)));max_prediction_error=max(max_prediction_error,error)
            assert error<=1e-12;infer+=1
    for seed in SEEDS:assert paired[('trend',seed)]==paired[('trend_cpd',seed)]
    for block in blocks:
        subset=[row for row in rows if row['block']==block['dates'][0]]
        for index,row in enumerate(subset):
            t,a=divmod(index,5)
            assert row['symbol']==SYMBOLS[a] and int(row['available_us'])==int(block['clock'][t])
            assert int(row['label_end_us'])==int(block['clock'][t]+DAY_US)
            assert int(row['eligible'])==int(block['mask'][t,a])
            for arm in ARMS:
                assert abs(float(row[arm+'_ensemble'])-sum(float(row[f'{arm}_seed{s}']) for s in SEEDS)/3)<1e-15
                if row['eligible']=='0':assert all(float(row[f'{arm}_seed{s}'])==0 for s in SEEDS)
    allseries={};joint=[];checks=0;residual=0.
    policies=[a+'_'+s for a in ARMS for s in ('seed2001','seed2002','seed2003','ensemble')]
    for block in result['blocks']:
        subset=[row for row in rows if row['block']==block['start']];current={}
        for policy in policies:
            net,gross,cost=decimal_path(subset,policy);current[policy]=net;allseries.setdefault(policy,[]).append(net)
            expected=[row for row in days if row['block']==block['start'] and row['policy']==policy]
            saved=np.array([float(row['fixed_cost_adjusted_price_proxy']) for row in expected])
            error=float(np.max(np.abs(net-saved)));residual=max(residual,error);assert error<1e-13
            stats=block['policies'][policy];finance=stats['financial']
            assert abs(float(net.sum())-finance['fixed_cost_adjusted_price_proxy'])<1e-13
            assert abs(float(gross.sum())-finance['gross_price_proxy'])<1e-13
            assert abs(float(cost.sum())-finance['fixed_cost_total'])<1e-13
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
    if ci is not None:np.testing.assert_allclose(ci,result['bootstrap']['ci95'],rtol=0,atol=1e-10)
    else:assert result['bootstrap']['ci95'] is None
    positions=np.array([abs(float(row['trend_cpd_ensemble'])) for row in rows if row['eligible']=='1'])
    verify_decision(result,allseries,joint,ci,invalid,positions)
    assert verify_evidence()==before==result['preservation']
    return dict(status='PASS',config_sha256=config_sha,result_sha256=sha((state/'RESULT.json').read_bytes()),
                model_block_readbacks=infer,max_model_prediction_residual=max_prediction_error,
                independent_Decimal_daily_and_summary_checks=checks,max_Decimal_daily_residual=residual,
                bootstrap='Independent direct portfolio net-series1000joint draws; no retrading or draw dropping',
                paired_initialization='ALL_THREE_BYTE_IDENTICAL_FRESH',adam_ages='ALL_SIX64',
                predecessor_manifest_files_preserved=185,new_training_updates=0,new_wallets=0,
                replay_scope='18same-policy audit inference sets, not new policy selection or training')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--state',type=Path,required=True);parser.add_argument('--config-sha',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();value=audit(args.state,args.config_sha);write_json(args.output,value);print(json.dumps(value))
