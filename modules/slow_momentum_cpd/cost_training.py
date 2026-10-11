"""Attempt4: frozen fresh cost-aligned pair; full calendar, exact output VJP."""
import argparse
import csv
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .core import DAY_US, SYMBOLS, FrozenGP, Scaler, sample_index, trend_features
from .diagnose_training import read_training_close
from .run import ROOT, sequences, sha, utc_us, write_json
from .sharpe import (PositionLSTM, InvalidScore, calendar_axis, decision_mask,
                     scored_sharpe, joint_bootstrap, prepare, save_positions)
from .objective_diagnostic import tensor_cost_returns, verify_evidence
from .cost_feasibility import RATE, FEE, SPREAD, SLIP, arithmetic, aggregate

EXPERIMENT = ROOT / 'research/slow-momentum-cpd-cost-objective-20261011'
PROPOSAL = ROOT / 'research/slow-momentum-cpd-objective-diagnostic-20261011/COST_OBJECTIVE_PROPOSAL.json'
PROPOSAL_SHA = '717cd852a17a8cb553a9443d49e32bc0894b53f73aceeb2df1d3859a17432a0d'
ARMS = ('trend', 'trend_cpd')
SEEDS = (2001, 2002, 2003)
ARCHIVE = Path('/workspace/slow-momentum-state/source/features.zip')


def load_config(expected_sha):
    path = EXPERIMENT / 'CONFIG.json'
    if sha(path.read_bytes()) != expected_sha or sha(PROPOSAL.read_bytes()) != PROPOSAL_SHA:
        raise ValueError('Frozen config/proposal changed')
    config = json.loads(path.read_text())
    for name, identity in config['source_files'].items():
        if sha((ROOT / name).read_bytes()) != identity:
            raise ValueError('Source changed: ' + name)
    return config


def build_episode(available, features, inputs, returns, vol, start, end):
    times = calendar_axis(available, utc_us(start), utc_us(end))
    mask = decision_mask(features, vol)[times]
    local = np.argwhere(mask)
    rows = local.copy()
    rows[:, 0] = times[rows[:, 0]]
    future = returns[times + 1].copy()
    if (not np.isfinite(future[mask]).all() or np.any(future[mask] <= -1)
            or np.any(available[times + 1] >= utc_us(end))):
        raise InvalidScore('Missing eligible mature return; never change causal mask')
    risk = vol[times].copy()
    scale = np.zeros_like(risk)
    scale[mask] = RATE / risk[mask] / 5
    x = sequences(inputs, rows)
    if not np.isfinite(x).all():
        raise ValueError('Nonfinite causal feature window')
    return dict(clock=available[times], times=times, mask=mask, local=local,
                rows=rows, x=x, future=future, scale=scale, vol=risk)


def train_episode():
    available, close = read_training_close(ARCHIVE)  # pre2023 predicate only
    trend, returns, vol = trend_features(close)
    frozen_path = ROOT / 'research/slow-momentum-cpd-20261011/results/FROZEN_TRAINING.json'
    if sha(frozen_path.read_bytes()) != '8587adcb407ba7b55e66eed6e1d06596cbbcb1e743f5fe04a822b98eee6b4bd2':
        raise ValueError('Frozen GP/scaler identity')
    f = json.loads(frozen_path.read_text())
    cutoff = utc_us('2023-01-01')
    if max(f['latest_training_label_end_us'], f['scaler_latest_available_us']) >= cutoff or f['fit']['latest_fit_available_us'] >= cutoff - DAY_US:
        raise ValueError('Future-fitted GP/scaler')
    gp = FrozenGP(f['mean'], f['scale'], np.asarray(f['stationary_log_parameters']),
                  np.asarray(f['change_log_parameters']), np.asarray(f['locations']), 21, f['fit'])
    scaler = Scaler(np.asarray(f['scaler_mean']), np.asarray(f['scaler_scale']))
    features = np.concatenate((trend, gp.transform(returns)), axis=2)
    ep = build_episode(available, features, scaler.transform(features), returns, vol,
                       '2021-01-01', '2023-01-01')
    mature = sample_index(trend, returns, vol, available, utc_us('2021-01-01'), cutoff)
    if not np.array_equal(mature, ep['rows']):
        raise ValueError('Causal mask differs from original mature endpoint axis')
    if len(ep['clock']) != 729 or len(ep['rows']) != 2526 or len(np.unique(ep['rows'][:, 0])) != 719:
        raise ValueError('Frozen training calendar/endpoint count differs')
    if sha(ep['rows'].astype('<i8').tobytes()) != '983baa27d9c0105c48b7c7debfea24089c28bff277014e1e43e2b27721d9e50f':
        raise ValueError('Frozen training row SHA differs')
    return ep


def episode_identity(ep):
    return dict(calendar_days=len(ep['clock']), eligible_endpoints=len(ep['rows']),
                eligible_dates=int(ep['mask'].any(1).sum()),
                all_cash_calendar_days=int((~ep['mask'].any(1)).sum()),
                first_available_us=int(ep['clock'][0]), last_available_us=int(ep['clock'][-1]),
                latest_label_end_us=int(ep['clock'][-1] + DAY_US),
                clocks_sha256=sha(ep['clock'].astype('<i8').tobytes()),
                train_rows_sha256=sha(ep['rows'].astype('<i8').tobytes()),
                inputs_sha256=sha(ep['x'].tobytes()), mask_sha256=sha(ep['mask'].tobytes()),
                current_vol_sha256=sha(ep['vol'].astype('<f8').tobytes()),
                future_outcome_sha256=sha(ep['future'].astype('<f8').tobytes()),
                reader='Predicate-bound pre2023; GP/scaler frozen, no validation or fits')


def position_grid(values, ep):
    grid = torch.zeros(ep['mask'].shape, dtype=torch.float64)
    row = ep['local']
    grid[row[:, 0], row[:, 1]] = values.to(torch.float64)
    return grid


def objective(values, ep):
    if not torch.isfinite(values).all() or torch.any(values.abs() > 1):
        raise ValueError('Invalid bounded position')
    weights = position_grid(values, ep) * torch.from_numpy(ep['scale'])
    detached = weights.detach()
    if torch.any(detached.abs() > .3) or torch.any(detached.abs().sum(1) > .6):
        raise ValueError('RAW_TARGET_CAP_STOP; no clipping')
    net, _ = tensor_cost_returns(weights, torch.from_numpy(ep['future']), torch.from_numpy(ep['mask']))
    mean = net.mean()
    variance = ((net - mean) ** 2).mean()
    loss = -np.sqrt(365) * mean / torch.sqrt(variance + 1e-9)
    if not torch.isfinite(loss):
        raise ValueError('Nonfinite whole-calendar loss')
    return loss, net, weights


def model_outputs(model, x, batch=128):
    with torch.no_grad():
        return torch.cat([model(torch.from_numpy(x[k:k + batch])) for k in range(0, len(x), batch)])


def arm_inputs(x, arm):
    if arm not in ARMS:
        raise ValueError('Unknown arm')
    result = x.copy()
    if arm == 'trend':
        result[:, :, 8:] = 0  # AFTER shared frozen scaler transformation
    return result


def portfolio_bootstrap(blocks):
    joint = [(clock, np.repeat(pair[:, None, :], 5, axis=1)) for clock, pair in blocks]
    return joint_bootstrap(joint, 1000, 14, 9901)


def output_vjp(model, x, ep, batch=128):
    """One whole-path adjoint, then exact deterministic feature-chunk replay."""
    model.train()
    outputs = model_outputs(model, x, batch)
    leaf = outputs.to(torch.float64).detach().requires_grad_(True)
    loss, net, weights = objective(leaf, ep)
    adjoint, = torch.autograd.grad(loss, leaf)
    model.zero_grad(set_to_none=True)
    for k in range(0, len(x), batch):
        replay = model(torch.from_numpy(x[k:k + batch]))
        if not torch.equal(replay.detach(), outputs[k:k + batch]):
            raise ValueError('Deterministic output VJP replay differs')
        replay.backward(adjoint[k:k + batch].to(replay.dtype))
    if any(p.grad is None or not torch.isfinite(p.grad).all() for p in model.parameters()):
        raise ValueError('Invalid complete parameter VJP')
    return float(loss.detach()), net.detach().numpy(), weights.detach().numpy(), outputs.numpy()


def report(position, ep):
    weights = position * ep['scale']
    if np.max(np.abs(weights)) > .3 or np.max(np.abs(weights).sum(1)) > .6:
        raise ValueError('RAW_TARGET_CAP_STOP; no clipping')
    financial, daily = arithmetic(weights, ep['future'])
    values = np.array([d['fixed_cost_adjusted_price_proxy'] for d in daily])
    actual, _ = tensor_cost_returns(torch.from_numpy(weights), torch.from_numpy(ep['future']), torch.from_numpy(ep['mask']))
    np.testing.assert_allclose(actual.numpy(), values, rtol=0, atol=1e-14)
    p = np.abs(position[ep['mask']])
    try:
        sr, status = scored_sharpe(values), 'VALID'
    except InvalidScore:
        sr, status = None, 'INVALID_ZERO_OR_NONFINITE_VARIANCE'
    stats = dict(financial=financial, net_price_cost_sharpe=sr, score_status=status,
                 eligible_count=len(p), position_abs_mean=float(p.mean()),
                 position_abs_quantiles=np.quantile(p, [.1, .5, .9, .99]).tolist(),
                 abs_position_below_fraction={str(t): float((p < t).mean()) for t in (.001, .01, .05)},
                 near_cash_flag=bool(p.mean() < .001 or (p < .001).mean() >= .99),
                 near_cash_scope='Fixed descriptive .001 threshold; user forbids presenting near-all-cash as success. No policy dead-zone or loss change.')
    return stats, values, daily


def score_aggregate(parts, series, position_abs):
    financial = aggregate([p['financial'] for p in parts])
    values = np.concatenate(series)
    try:
        sr, status = scored_sharpe(values), 'VALID'
    except InvalidScore:
        sr, status = None, 'INVALID_ZERO_OR_NONFINITE_VARIANCE'
    p = np.concatenate(position_abs)
    return dict(financial=financial, net_price_cost_sharpe=sr, score_status=status,
                position_abs_mean=float(p.mean()), position_abs_quantiles=np.quantile(p,[.1,.5,.9,.99]).tolist(),
                abs_position_below_fraction={str(t):float((p<t).mean()) for t in (.001,.01,.05)},
                near_cash_flag=bool(p.mean()<.001 or (p<.001).mean()>=.99))


def evaluate(units, state):
    _, available, returns, vol, _, _, _, blocks, source = prepare(ARCHIVE)
    result, allseries, allabs, joint, daily_rows = [], {}, {}, [], []
    for block in blocks:
        times, mask = block['times'], block['mask']
        ep = dict(mask=mask, scale=np.zeros(mask.shape), future=returns[times+1], clock=block['clock'])
        ep['scale'][mask] = RATE / vol[times][mask] / 5
        summaries, current_series = {}, {}
        for arm in ARMS:
            for seed in SEEDS:
                model = units[(arm,seed)]['model']
                model.eval()
                x = arm_inputs(block['x'], arm)
                values = model_outputs(model,x).numpy().astype(float)
                positions = np.zeros(mask.shape)
                positions[mask] = values
                block['position'][arm].append(positions)
            positions = np.asarray(block['position'][arm])
            for suffix, p in [(f'seed{s}',positions[k]) for k,s in enumerate(SEEDS)] + [('ensemble',positions.mean(0))]:
                name=arm+'_'+suffix
                stats, daily, rows = report(p,ep)
                summaries[name], current_series[name] = stats,daily
                allseries.setdefault(name,[]).append(daily)
                allabs.setdefault(name,[]).append(np.abs(p[mask]))
                for i,row in enumerate(rows):
                    daily_rows.append(dict(block=block['dates'][0],policy=name,available_us=int(ep['clock'][i]),label_end_us=int(ep['clock'][i]+DAY_US),**row))
        result.append(dict(start=block['dates'][0],end_exclusive=block['dates'][1],policies=summaries))
        # Existing bootstrap sums asset-axis/5. Repeating each portfolio series
        # in all5 slots preserves the exact net series and same index draws.
        pair=np.column_stack([current_series[a+'_ensemble'] for a in ARMS])
        joint.append((ep['clock'], pair))
    agg={name:score_aggregate([b['policies'][name] for b in result],allseries[name],allabs[name]) for name in allseries}
    def difference(a,b):
        return None if a is None or b is None else b-a
    delta=difference(agg['trend_ensemble']['net_price_cost_sharpe'],agg['trend_cpd_ensemble']['net_price_cost_sharpe'])
    seeds=[difference(agg[f'trend_seed{s}']['net_price_cost_sharpe'],agg[f'trend_cpd_seed{s}']['net_price_cost_sharpe']) for s in SEEDS]
    byblock=[difference(b['policies']['trend_ensemble']['net_price_cost_sharpe'],b['policies']['trend_cpd_ensemble']['net_price_cost_sharpe']) for b in result]
    boot=portfolio_bootstrap(joint)
    gates=dict(absolute_CPD_cost_adjusted_positive=agg['trend_cpd_ensemble']['financial']['fixed_cost_adjusted_price_proxy']>0,
               aggregate_net_sharpe_increment_positive=delta is not None and delta>0,
               all_three_blocks_increment_positive=all(x is not None and x>0 for x in byblock),
               at_least_two_seeds_increment_positive=sum(x is not None and x>0 for x in seeds)>=2,
               conditional_bootstrap_lower_positive=boot['status']=='VALID' and boot['ci95'][0]>0)
    near=agg['trend_cpd_ensemble']['near_cash_flag']
    valid=all(p['score_status']=='VALID' for p in agg.values()) and all(p['score_status']=='VALID' for b in result for p in b['policies'].values())
    positions_sha=save_positions(state,blocks,available,returns,vol,SEEDS)
    with (state/'DAILY.csv').open('x',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(daily_rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(daily_rows)
    return dict(blocks=result,aggregate=agg,aggregate_ensemble_increment=delta,
                seed_increments=seeds,block_ensemble_increments=byblock,bootstrap=boot,gates=gates,
                all_frozen_statistical_gates_pass=all(gates.values()),near_cash_flag=near,
                all_required_scores_valid=valid,
                decision='PASS_PROXY_GATES_ONLY_NO_WALLET' if all(gates.values()) and not near and valid else 'STOP_NO_FURTHER_RECIPE',
                positions_sha256=positions_sha,daily_sha256=sha((state/'DAILY.csv').read_bytes()),source_price_members=source,
                scope='Seen-development static price/cost proxy; funding NOT_MEASURED_NOT_KNOWN_ZERO/nativewallet0/realnetProfitAPRUNKNOWN; conditional CI unadjusted for prior research')


def scan_output(state):
    count=sum(p.stat().st_size for p in state.rglob('*') if p.is_file())
    if count>10485760:
        raise ValueError('10MiB_OUTPUT_STOP')
    return count


def step_receipt(optimizer, model, progress, key, persist=None):
    optimizer.step()
    # Count the actual returned optimizer call even if its state is invalid.
    progress['completed_updates'] += 1
    progress['fits'][key] += 1
    if persist is not None:
        persist()
    if any(not torch.isfinite(v).all() for v in model.parameters()) or any(not torch.isfinite(v).all() for item in optimizer.state.values() for v in item.values() if torch.is_tensor(v)):
        raise ValueError('NONFINITE_ADAM_OR_PARAMETER_STOP')


def run(state, config_sha, published):
    started=time.monotonic()
    config=load_config(config_sha)
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()!=published:
        raise ValueError('Published HEAD differs')
    public=json.loads((state/'SOURCE_PUBLIC_READBACK.json').read_text())
    if public['published_commit']!=published or public['status']!='PASS':
        raise ValueError('Public source verification absent')
    if (state/'STARTED.json').exists():
        raise FileExistsError('No implicit experiment retry/resume')
    before=verify_evidence()
    ep=train_episode()
    identity=episode_identity(ep)
    checked=json.loads((EXPERIMENT/'prefit/CALENDAR.json').read_text())
    if identity!=checked:
        raise ValueError('Prefit training calendar changed')
    write_json(state/'STARTED.json',dict(attempt=4,config_sha256=config_sha,published_source_commit=published,train_identity=identity))
    units={}
    progress=dict(stage='INITIALIZING',models_initialized=0,completed_updates=0,completed_fits=0,fits={},validation_calls=0)
    def persist():
        temp=state/'PROGRESS.tmp';temp.write_text(json.dumps(progress,indent=2)+'\n');temp.replace(state/'PROGRESS.json')
    try:
        for seed in SEEDS:
            for arm in ARMS:
                torch.manual_seed(seed)
                model=PositionLSTM()
                progress['models_initialized']+=1
                initial=sha(b''.join(p.detach().numpy().tobytes() for p in model.state_dict().values()))
                units[(arm,seed)]=dict(model=model,initial_sha256=initial,rng=torch.get_rng_state().clone())
            if units[('trend',seed)]['initial_sha256']!=units[('trend_cpd',seed)]['initial_sha256']:
                raise ValueError('Paired initialization differs')
        fits=[]
        for seed in SEEDS:
            for arm in ARMS:
                unit=units[(arm,seed)];model=unit['model'];torch.set_rng_state(unit['rng'])
                optimizer=torch.optim.Adam(model.parameters(),lr=.001,betas=(.9,.999),eps=1e-8,weight_decay=0)
                x=arm_inputs(ep['x'], arm)
                key=f'{arm}_seed{seed}';progress['stage']='TRAINING';progress['fits'][key]=0;persist()
                begin=time.monotonic();curve=[];clipped=0
                for update in range(64):
                    loss,net,weights,p=output_vjp(model,x,ep,128)
                    if update%16==0:
                        curve.append(dict(update=update,loss=loss,mean=float(net.mean()),variance=float(net.var()),epsilon_denominator_fraction=1e-9/(net.var()+1e-9),mean_abs_position=float(np.abs(p).mean()),gross_target_mean=float(np.abs(weights).sum(1).mean())))
                    gradient=nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
                    clipped+=int(float(gradient)>1)
                    step_receipt(optimizer,model,progress,key,persist)
                    if (update+1)%16==0:print(f'TRAIN {key} {update+1}/64 total={progress["completed_updates"]}/384 loss={loss:.7f}',flush=True)
                    if time.monotonic()-started>=1200:raise TimeoutError('TOTAL1200s_STOP')
                model.eval();outputs=model_outputs(model,x)
                loss,net,_=objective(outputs.to(torch.float64),ep)
                terminal,_,_=report(position_grid(outputs,ep).numpy(),ep)
                if terminal['score_status']!='VALID':
                    raise InvalidScore('INVALID_TERMINAL_TRAIN_SCORE_STOP')
                curve.append(dict(update=64,loss=float(loss),mean=float(net.mean()),variance=float(net.var(unbiased=False)),epsilon_denominator_fraction=1e-9/(float(net.var(unbiased=False))+1e-9),mean_abs_position=float(outputs.abs().mean())))
                checkpoint=state/f'{key}-step64.pt'
                torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),torch_rng=torch.get_rng_state(),seed=seed,arm=arm,updates=64,config_sha256=config_sha,source_commit=published,training_identity=identity),checkpoint)
                fit=dict(arm=arm,seed=seed,updates=64,initial_sha256=unit['initial_sha256'],checkpoint_sha256=sha(checkpoint.read_bytes()),checkpoint_file=checkpoint.name,adam_ages=sorted({int(v['step']) for v in optimizer.state.values()}),train_curve=curve,train_terminal=terminal,clipped_updates=clipped,seconds=time.monotonic()-begin,convergence='NOT_ESTABLISHED_FIXED_BUDGET')
                write_json(state/f'FIT_{key}.json',fit);fits.append(fit);progress['completed_fits']+=1;persist();scan_output(state)
        write_json(state/'TRAINING_STOP.json',dict(reason='ALL_SIX_FIXED64_COMPLETE',fits=6,updates=384,validation_calls=0,terminal_checkpoint_shas=[f['checkpoint_sha256'] for f in fits]))
        progress['stage']='FINAL_DEVELOPMENT_EXPORT';progress['validation_calls']=1;persist()
        evaluated=evaluate(units,state)
        preservation=verify_evidence()
        if preservation!=before:raise ValueError('Predecessor evidence changed')
        result=dict(schema='CPD_COST_OBJECTIVE_ATTEMPT4_RESULT_V1',source_commit=published,config_sha256=config_sha,proposal_sha256=PROPOSAL_SHA,training_identity=identity,fits=fits,preservation=preservation,**evaluated,
                    actual_counts=dict(new_fresh_fits=6,new_updates=384,scientific_attempts_cumulative=4,fresh_fits_cumulative=18,updates_cumulative=14208,final_validation_export_calls=1,final_model_block_prediction_sets=18,new_GP_scaler_fits=0,wallets=0,provider_downloads=0),seconds=time.monotonic()-started)
        write_json(state/'RESULT.json',result);progress['stage']='COMPLETE';persist();scan_output(state)
        print(json.dumps(dict(status='COMPLETE',decision=result['decision'],gates=result['gates'],aggregate={k:v for k,v in result['aggregate'].items() if k.endswith('ensemble')},seconds=result['seconds'])),flush=True)
    except Exception as exc:
        progress['stage']='FAILED';progress['error']=repr(exc);persist()
        if 'optimizer' in locals() and 'model' in locals():
            torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),torch_rng=torch.get_rng_state(),fit=key,completed_updates=progress['fits'][key],failed=True,source_commit=published,config_sha256=config_sha),state/'PARTIAL_FAILED_MODEL.pt')
        write_json(state/'FAILED.json',dict(error=repr(exc),progress=progress,source_commit=published,config_sha256=config_sha,no_retry=True))
        raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('check','run'));parser.add_argument('--state',type=Path,required=True);parser.add_argument('--config-sha',required=True);parser.add_argument('--published-commit')
    a=parser.parse_args();load_config(a.config_sha);a.state.mkdir(parents=True,exist_ok=True)
    if a.action=='check':
        ep=train_episode();identity=episode_identity(ep);write_json(a.state/'CALENDAR.json',identity);print(json.dumps(identity))
    else:
        if not a.published_commit:raise ValueError('Published source required')
        run(a.state,a.config_sha,a.published_commit)


if __name__=='__main__':main()
