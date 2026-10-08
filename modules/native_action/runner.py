"""Bounded offline entry points; market acquisition belongs to the caller.

Adapter factory signature: build(options: dict) -> NativeExperiment. It loads
the caller's already-bound minutes, frozen E6 inputs and exact existing mapper.
No data downloading, fitting of experts or account transport occurs here.
"""
from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path
import resource
import time
import numpy as np
from scripts.investment.perpetual_directional import DAY,need
from .teacher import replay_candidates,training_state_relabel
from .train import NativeRewardModel,fit,TRAIN_START,TRAIN_END,EVAL_START,EVAL_END
from .interface import NativeExperiment
from .availability_contract import scheduled_identity


def load_experiment(adapter,options):
    module,sep,name=adapter.partition(':')
    need(bool(sep) and bool(module) and bool(name),'Adapter must be module:factory')
    experiment=getattr(importlib.import_module(module),name)(options)
    need(isinstance(experiment,NativeExperiment),'Factory returns NativeExperiment')
    need(experiment.simulator.budget is not None,'Factory sets initial continuous E6 budget')
    need(experiment.simulator.final_day_target_zero,'Task requires common forced final-day cash convention')
    need(experiment.binding is not None,'Factory records source/input bindings')
    context=experiment.context_at(experiment.simulator.cursor)
    context.validate(experiment.simulator)
    return experiment


def exclusive_json(path,value):
    with Path(path).open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')


def write_row(stream,row):
    stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    stream.flush()


def run(experiment,directory,mode,*,limit_seconds=900,model=None,relabel_training=False):
    need(mode in ('teacher','local','student'),'Explicit native run mode')
    need(0<limit_seconds<=900,'Oracle wall-clock budget at most 900 seconds')
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    sim=experiment.simulator
    if mode=='local':need(experiment.baseline_at is not None,'Exact original selector proposal required')
    if mode=='student':
        need(model is not None,'Frozen H1 student model required')
        eval_range=sim.start==EVAL_START and sim.end==EVAL_END
        train_range=TRAIN_START<=sim.start<sim.end<=TRAIN_END
        if model.metadata.get('schema')=='NATIVE_AVAILABLE_REWARD_RIDGE_V1':
            need(sim.start>=model.metadata['asof_us'],'Masked student must be fitted before its replay interval')
            eval_range=True
        need(eval_range or train_range,'Student runs only declared H1 train or Aug13-Jan2 temporal evaluation')
        need(not relabel_training or train_range,'Relabeling evaluation states is forbidden')
    total=(sim.end-sim.start)//DAY
    need((sim.end-sim.start)%DAY==0,'Complete fixed daily native-action intervals')
    started=time.monotonic()
    rows=0
    identity=None
    label_path=directory/('predictions.jsonl' if mode=='student' else 'teacher.jsonl')
    relabel_path=directory/'student_train_relabels.jsonl'
    relabel_stream=relabel_path.open('x') if relabel_training else None
    status='RUNNING'
    error=None
    try:
        with label_path.open('x') as stream:
            while sim.cursor<sim.end and sim.stop is None:
                remaining=limit_seconds-(time.monotonic()-started)
                need(remaining>0,'Native run wall-clock budget exhausted; completed prefix retained')
                context=experiment.context_at(sim.cursor)
                context.validate(sim)
                current=(scheduled_identity(context.binding) if context.action_available is not None else
                         {k:v for k,v in context.binding.items() if k!='market_binding_sha256'})
                if identity is None:identity=current
                else:need(current==identity,'Expert/rank/mapper identity changed within continuous run')
                if mode=='student':
                    if relabel_stream is not None:
                        row,_=training_state_relabel(sim,context,experiment.mapper,training_end_us=TRAIN_END)
                        write_row(relabel_stream,row)
                    request,rewards=model.request(sim,context)
                    forced=bool(sim.final_day_target_zero and sim.cursor+DAY>=sim.end)
                    if forced:request=np.eye(6)[0]
                    proposal=experiment.mapper(np.asarray(sim.budget),request,context)
                    proposal.validate(sim.budget,len(sim.symbols))
                    before_hash=sim.state_hash()
                    before=float(sim.account.nav())
                    decision=sim.cursor
                    sim.budget=list(proposal.budget)
                    result=sim.advance_day(dict(zip(sim.symbols,proposal.targets,strict=True)))
                    need(result['completed'],'Incomplete student day; preserve prefix and stop')
                    predictions=[float(x) if np.isfinite(x) else None for x in rewards]
                    row=dict(schema='NATIVE_E6_STUDENT_PREDICTION_V1',decision_us=decision,
                             predicted_next_day_reward_USDT=predictions,request=request.tolist(),
                             budget=list(proposal.budget),targets=list(proposal.targets),state_hash=before_hash,
                             observed_next_day_net_increment_USDT=float(sim.account.nav())-before,
                             binding=context.binding,inference_inputs='CAUSAL_CURRENT_STATE_ONLY',
                             forced_terminal_day=forced,optimization_allowed=not forced,
                             distribution_shift=model.metadata['distribution_shift'])
                    if context.action_available is not None:
                        row['e6_available']=context.action_mask().tolist()
                else:
                    baseline=experiment.baseline_at(sim,context) if mode=='local' else None
                    row,winner,actual=replay_candidates(sim,context,experiment.mapper,baseline=baseline,
                        state_role='ACTUAL_SELECTOR_STATE' if mode=='local' else 'TEACHER_SELF',
                        time_limit_seconds=remaining)
                    # Local regret stays on the actual selector trajectory. It
                    # is never accumulated as a fictitious winner portfolio.
                    sim=actual if mode=='local' else winner
                write_row(stream,row)
                rows+=1
                print(json.dumps(dict(stage=mode,days=rows,total=total,NAV=float(sim.account.nav()),
                                      elapsed_seconds=round(time.monotonic()-started,3))),flush=True)
                need(time.monotonic()-started<=limit_seconds,'Wall-clock budget exceeded after day; prefix retained')
            need(rows==total and sim.stop is None and all(p.quantity==0 for p in sim.account.positions.values()),
                 'Full calendar and charged terminal cash close required')
        status='COMPLETE'
    except BaseException as exc:
        status='FAILED_PREFIX_RETAINED'
        error=dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        if relabel_stream is not None:relabel_stream.close()
        case=sim.result()
        case['minute'].write_parquet(directory/'minute.parquet')
        for key in ('trades','funding','rejections','breaches','extrema','liquidations'):
            if key in case:exclusive_json(directory/(key+'.json'),case[key])
        exclusive_json(directory/'summary.json',case['summary'])
        exclusive_json(directory/'RUN.json',dict(status=status,error=error,mode=mode,completed_days=rows,
            required_days=total,elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            binding=experiment.binding,labels_path=str(label_path),
            optimal_scope='SIX_REQUEST_ONE_STEP_GREEDY' if mode=='teacher' else
                          'ACTUAL_SELECTOR_STATE_LOCAL_REGRET' if mode=='local' else 'FROZEN_H1_STUDENT_SELF_TRAJECTORY',
            local_regret_is_equity_curve=False,global_native_upper_bound=False,
            evaluation_role=('DECLARED_AVAILABILITY_AWARE_HISTORICAL_INTERVAL' if
                             experiment.context_at(sim.start).action_available is not None else
                             'PREVIOUSLY_SEEN_TEMPORAL_EVALUATION' if sim.start==EVAL_START else '2024H1_TRAINING'),
            replica_of_old_v3_teacher=False))
    return sim


def probe(experiment,day_index=0,limit_seconds=900):
    """Caller-authorized first/later-day probe, staying on exact baseline states."""
    sim=experiment.simulator
    need(day_index>=0 and sim.start+day_index*DAY<sim.end,'Probe day within calendar')
    need(day_index==0 or experiment.baseline_at is not None,'Later probe requires exact baseline trajectory')
    start=time.monotonic()
    for _ in range(day_index):
        need(time.monotonic()-start<limit_seconds,'Probe baseline continuation budget exceeded')
        context=experiment.context_at(sim.cursor)
        proposal=experiment.baseline_at(sim,context)
        proposal.validate(sim.budget,len(sim.symbols))
        sim.budget=list(proposal.budget)
        result=sim.advance_day(dict(zip(sim.symbols,proposal.targets,strict=True)))
        need(result['completed'],'Incomplete baseline probe prefix')
    context=experiment.context_at(sim.cursor)
    baseline=experiment.baseline_at(sim,context) if experiment.baseline_at else None
    row,_,_=replay_candidates(sim,context,experiment.mapper,baseline=baseline,
        state_role='ACTUAL_SELECTOR_STATE' if baseline else 'TEACHER_SELF',
        time_limit_seconds=limit_seconds-(time.monotonic()-start))
    row['probe_only']=True
    row['probe_day_index']=day_index
    row['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    train=sub.add_parser('train')
    train.add_argument('--labels',nargs='+',required=True)
    train.add_argument('--output',required=True)
    for name in ('teacher','local','student','probe'):
        p=sub.add_parser(name)
        p.add_argument('--adapter',required=True,help='module:factory -> NativeExperiment')
        p.add_argument('--options',required=True,help='Local JSON containing bound source/input paths')
        p.add_argument('--output',required=True)
        p.add_argument('--limit-seconds',type=float,default=900)
        if name=='probe':p.add_argument('--day-index',type=int,default=0)
        if name=='student':
            p.add_argument('--model',required=True)
            p.add_argument('--relabel-training',action='store_true')
            p.add_argument('--availability-aware',action='store_true',help='Load the explicit masked model schema')
    args=parser.parse_args()
    if args.command=='train':
        rows=[]
        hashes={}
        import hashlib
        for path in args.labels:
            data=Path(path).read_bytes()
            hashes[str(Path(path).resolve())]=hashlib.sha256(data).hexdigest()
            rows.extend(json.loads(line) for line in data.splitlines() if line)
        model=fit(rows)
        model.metadata['teacher_file_sha256']=hashes
        model.save(args.output)
        print(json.dumps(model.metadata,ensure_ascii=False),flush=True)
        return
    options=json.loads(Path(args.options).read_text())
    experiment=load_experiment(args.adapter,options)
    if args.command=='probe':
        exclusive_json(args.output,probe(experiment,args.day_index,args.limit_seconds))
        return
    if args.command=='student' and args.availability_aware:
        from .availability import AvailableRewardModel
        model=AvailableRewardModel.load(args.model)
    else:model=NativeRewardModel.load(args.model) if args.command=='student' else None
    run(experiment,args.output,args.command,limit_seconds=args.limit_seconds,model=model,
        relabel_training=getattr(args,'relabel_training',False))


if __name__=='__main__':main()
