"""Thin repaired-source orchestration of the already tested fixed cost objective.

No alternative model, financial kernel, or mask rule. Old frozen runners stay
byte-identical; their pure objective/VJP/report functions are reused directly.
"""
import argparse
import csv
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .run import ROOT, sha, write_json
from .cost_training import (ARMS, SEEDS, PositionLSTM, InvalidScore, arm_inputs,
    model_outputs, output_vjp, objective, position_grid, report, score_aggregate,
    portfolio_bootstrap, scan_output, step_receipt, episode_identity)
from .sharpe import save_positions
from .objective_diagnostic import verify_evidence
from .repaired_data import EXPERIMENT, training_episode, evaluation_blocks


def preservation():
    value = verify_evidence()
    additional = {}
    for name in ('slow-momentum-cpd-objective-diagnostic-20261011', 'slow-momentum-cpd-cost-objective-20261011'):
        path = ROOT / 'research' / name / 'DELIVERY_MANIFEST.json'
        manifest = json.loads(path.read_text())
        for filename, identity in manifest['files'].items():
            data = (ROOT / filename).read_bytes()
            if sha(data) != identity['sha256'] or len(data) != identity['bytes']:
                raise ValueError('Frozen predecessor changed: ' + filename)
        additional[name] = len(manifest['files'])
    return dict(prior=value, additional_manifest_files=additional)


def load(config_sha):
    path = EXPERIMENT / 'CONFIG.json'
    if sha(path.read_bytes()) != config_sha:
        raise ValueError('Frozen repaired config differs')
    config = json.loads(path.read_text())
    for name, digest in config['source_files'].items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError('Frozen source differs: ' + name)
    artifacts = {}
    for name, digest in config['prefit_artifacts'].items():
        data = (EXPERIMENT / 'prefit' / name).read_bytes()
        if sha(data) != digest:
            raise ValueError('Frozen refitted artifact differs: ' + name)
        artifacts[name] = json.loads(data)
    ep = training_episode(artifacts['DATA_REPAIR.json'], artifacts['FROZEN_TRAINING.json'])
    identity = episode_identity(ep)
    identity['reader'] = 'Predicate-bound pre2023; repaired source and newly training-frozen GP/scaler; validation reads0'
    if identity != artifacts['CALENDAR.json']:
        raise ValueError('Repaired training episode differs from prefit identity')
    if artifacts['FROZEN_TRAINING.json']['data_repair_sha256'] != config['prefit_artifacts']['DATA_REPAIR.json']:
        raise ValueError('GP/scaler repair binding differs')
    return config, artifacts, ep, identity


def export(units, state, artifacts, progress, persist):
    available, returns, vol, blocks, source = evaluation_blocks(artifacts['DATA_REPAIR.json'], artifacts['FROZEN_TRAINING.json'])
    results, series, positions_abs, joint, rows = [], {}, {}, [], []
    for block in blocks:
        policies, current = {}, {}
        for arm in ARMS:
            for seed in SEEDS:
                model = units[(arm, seed)]['model']; model.eval()
                values = model_outputs(model, arm_inputs(block['x'], arm)).numpy().astype(float)
                progress['completed_model_block_exports'] += 1; persist()
                position = np.zeros(block['mask'].shape); position[block['mask']] = values
                block['position'][arm].append(position)
            values = np.asarray(block['position'][arm])
            for suffix, position in [(f'seed{s}', values[k]) for k,s in enumerate(SEEDS)] + [('ensemble', values.mean(0))]:
                name = arm + '_' + suffix
                stats, daily, details = report(position, block)
                policies[name], current[name] = stats, daily
                series.setdefault(name, []).append(daily)
                positions_abs.setdefault(name, []).append(np.abs(position[block['mask']]))
                rows.extend(dict(block=block['dates'][0], policy=name, available_us=int(block['clock'][i]), label_end_us=int(block['clock'][i])+86400000000, **item) for i,item in enumerate(details))
        results.append(dict(start=block['dates'][0], end_exclusive=block['dates'][1], policies=policies))
        joint.append((block['clock'], np.column_stack([current[a+'_ensemble'] for a in ARMS])))
    combined = {name:score_aggregate([b['policies'][name] for b in results], series[name], positions_abs[name]) for name in series}
    diff = lambda left,right: None if left is None or right is None else right-left
    delta = diff(*[combined[a+'_ensemble']['net_price_cost_sharpe'] for a in ARMS])
    seeds = [diff(*[combined[f'{a}_seed{s}']['net_price_cost_sharpe'] for a in ARMS]) for s in SEEDS]
    block_delta = [diff(*[b['policies'][a+'_ensemble']['net_price_cost_sharpe'] for a in ARMS]) for b in results]
    bootstrap = portfolio_bootstrap(joint)
    gates = dict(absolute_CPD_cost_adjusted_positive=combined['trend_cpd_ensemble']['financial']['fixed_cost_adjusted_price_proxy']>0,
        aggregate_net_sharpe_increment_positive=delta is not None and delta>0,
        all_three_blocks_increment_positive=all(d is not None and d>0 for d in block_delta),
        at_least_two_seeds_increment_positive=sum(d is not None and d>0 for d in seeds)>=2,
        conditional_bootstrap_lower_positive=bootstrap['status']=='VALID' and bootstrap['ci95'][0]>0)
    valid = all(p['score_status']=='VALID' for p in combined.values()) and all(p['score_status']=='VALID' for b in results for p in b['policies'].values())
    near = combined['trend_cpd_ensemble']['near_cash_flag']
    position_sha = save_positions(state, blocks, available, returns, vol, SEEDS)
    with (state/'DAILY.csv').open('x', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n');writer.writeheader();writer.writerows(rows)
    return dict(blocks=results, aggregate=combined, aggregate_ensemble_increment=delta,
        seed_increments=seeds, block_ensemble_increments=block_delta, bootstrap=bootstrap, gates=gates,
        all_frozen_statistical_gates_pass=all(gates.values()), all_required_scores_valid=valid, near_cash_flag=near,
        decision='PASS_PROXY_GATES_ONLY_NO_WALLET' if all(gates.values()) and valid and not near else 'STOP_NO_FURTHER_RECIPE',
        positions_sha256=position_sha, daily_sha256=sha((state/'DAILY.csv').read_bytes()), source_price_members=source,
        scope='Repaired-data adaptation on seen development; static price/cost proxy; actual funding/nativewalletNOTBOUND, netProfit/APRUNKNOWN; no pristineOOS or cost-only attribution against older data versions')


def run(state, config_sha, published):
    began=time.monotonic()
    config, artifacts, ep, identity=load(config_sha)
    if subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()!=published:
        raise ValueError('Published HEAD differs')
    proof=json.loads((state/'SOURCE_PUBLIC_READBACK.json').read_text())
    if proof['status']!='PASS' or proof['published_commit']!=published or proof['config_sha256']!=config_sha:
        raise ValueError('Public readback does not bind config/source')
    if (state/'STARTED.json').exists():
        raise FileExistsError('No implicit scientific retry')
    before=preservation()
    write_json(state/'STARTED.json', dict(attempt=4, source_commit=published, config_sha256=config_sha, training_identity=identity, data_version='TEN_OFFICIAL_CLOSES_REPAIRED_TRAIN_REFROZEN'))
    progress=dict(stage='INITIALIZING',models_initialized=0,completed_updates=0,completed_fits=0,fits={},validation_calls=0,completed_model_block_exports=0)
    def persist():
        temp=state/'PROGRESS.tmp';temp.write_text(json.dumps(progress,indent=2)+'\n');temp.replace(state/'PROGRESS.json')
    units={};fits=[]
    try:
        torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        for seed in SEEDS:
            for arm in ARMS:
                torch.manual_seed(seed);model=PositionLSTM();progress['models_initialized']+=1
                units[(arm,seed)]=dict(model=model,initial_sha256=sha(b''.join(v.detach().numpy().tobytes() for v in model.state_dict().values())),rng=torch.get_rng_state().clone())
            if units[('trend',seed)]['initial_sha256']!=units[('trend_cpd',seed)]['initial_sha256']:raise ValueError('Paired initial state differs')
        for seed in SEEDS:
            for arm in ARMS:
                unit=units[(arm,seed)];model=unit['model'];torch.set_rng_state(unit['rng'])
                optimizer=torch.optim.Adam(model.parameters(),lr=.001,betas=(.9,.999),eps=1e-8,weight_decay=0)
                x=arm_inputs(ep['x'],arm);key=f'{arm}_seed{seed}'
                progress['stage']='TRAINING';progress['fits'][key]=0;persist()
                fit_start=time.monotonic();curve=[];clipped=0
                for update in range(64):
                    loss,net,weights,p=output_vjp(model,x,ep,128)
                    if update%16==0:
                        curve.append(dict(update=update,loss=loss,mean=float(net.mean()),variance=float(net.var()),epsilon_denominator_fraction=float(1e-9/(net.var()+1e-9)),mean_abs_position=float(np.abs(p).mean()),gross_target_mean=float(np.abs(weights).sum(1).mean())))
                    gradient=nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);clipped+=int(float(gradient)>1)
                    step_receipt(optimizer,model,progress,key,persist)
                    if (update+1)%16==0: print(f'TRAIN {key} {update+1}/64 total={progress["completed_updates"]}/384 loss={loss:.7f}',flush=True)
                    if time.monotonic()-began>=1200:raise TimeoutError('TOTAL1200s_STOP')
                model.eval();p=model_outputs(model,x);loss,net,_=objective(p.to(torch.float64),ep)
                terminal,_,_=report(position_grid(p,ep).numpy(),ep)
                if terminal['score_status']!='VALID':raise InvalidScore('INVALID_TERMINAL_TRAIN_SCORE_STOP')
                curve.append(dict(update=64,loss=float(loss),mean=float(net.mean()),variance=float(net.var(unbiased=False)),epsilon_denominator_fraction=1e-9/(float(net.var(unbiased=False))+1e-9),mean_abs_position=float(p.abs().mean())))
                path=state/f'{key}-step64.pt'
                torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),torch_rng=torch.get_rng_state(),arm=arm,seed=seed,updates=64,source_commit=published,config_sha256=config_sha,training_identity=identity),path)
                fit=dict(arm=arm,seed=seed,updates=64,initial_sha256=unit['initial_sha256'],checkpoint_sha256=sha(path.read_bytes()),checkpoint_file=path.name,adam_ages=sorted({int(v['step']) for v in optimizer.state.values()}),train_curve=curve,train_terminal=terminal,clipped_updates=clipped,seconds=time.monotonic()-fit_start,convergence='NOT_ESTABLISHED_FIXED_BUDGET')
                write_json(state/f'FIT_{key}.json',fit);fits.append(fit);progress['completed_fits']+=1;persist();scan_output(state)
        write_json(state/'TRAINING_STOP.json',dict(reason='ALL_SIX_FIXED64_COMPLETE',fits=6,updates=384,validation_calls=0,terminal_checkpoint_shas=[f['checkpoint_sha256'] for f in fits]))
        progress['stage']='FINAL_DEVELOPMENT_EXPORT';progress['validation_calls']=1;persist()
        evaluated=export(units,state,artifacts,progress,persist)
        if time.monotonic()-began>=1200:raise TimeoutError('TOTAL1200s_STOP')
        after=preservation()
        if after!=before:raise ValueError('Predecessor evidence changed')
        result=dict(schema='REPAIRED_CPD_COST_OBJECTIVE_ATTEMPT4_RESULT_V1',source_commit=published,config_sha256=config_sha,
            training_identity=identity,fits=fits,preservation=after,**evaluated,
            actual_counts=dict(new_fresh_fits=6,new_updates=384,scientific_attempts_cumulative=4,fresh_fits_cumulative=18,updates_cumulative=14208,
                new_GP_groups=1,new_GP_optimizer_calls=2,new_scaler_fits=1,final_validation_export_calls=1,final_model_block_prediction_sets=18,wallets=0,provider_downloads=0),seconds=time.monotonic()-began)
        write_json(state/'RESULT.json',result);progress['stage']='COMPLETE';persist();scan_output(state)
        print(json.dumps(dict(status='COMPLETE',decision=result['decision'],gates=result['gates'],aggregate_increment=result['aggregate_ensemble_increment'],bootstrap=result['bootstrap'],seconds=result['seconds'])),flush=True)
    except Exception as exc:
        progress['stage']='FAILED';progress['error']=repr(exc);persist()
        if 'optimizer' in locals():
            torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),torch_rng=torch.get_rng_state(),fit=key,completed_updates=progress['fits'][key],source_commit=published,config_sha256=config_sha,failed=True),state/'PARTIAL_FAILED_MODEL.pt')
        write_json(state/'FAILED.json',dict(error=repr(exc),progress=progress,no_retry=True,completed_fit_receipts=[f['checkpoint_sha256'] for f in fits]))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--config-sha',required=True);p.add_argument('--published-commit',required=True)
    a=p.parse_args();run(a.state,a.config_sha,a.published_commit)
