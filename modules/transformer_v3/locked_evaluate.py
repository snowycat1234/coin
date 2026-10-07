"""All five bridge experiments; weights/risk frozen, no best-bridge selection."""
import argparse,json,os,platform,subprocess,sys
from pathlib import Path
import numpy as np
from modules.transformer_v2.train import atomic,sha
from modules.transformer_v2.evaluate import portfolio_targets
from .locked_bridge_data import require_freeze,SCENARIOS
from .locked_features import build_features,immutable_infer,immutable_legacy_transformer
from .train_policy import FAMILIES,SEEDS
from .policy_portfolio import policy_targets
from .evaluate_policy import save_targets
from .wallet import run_tasks

V2_FAMILIES=('TRANSFORMER_SHARED','CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK')
BASELINES=('BASE_CASH','BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3')
DAY=86_400_000_000

def frozen_predictions(state,v2,input_manifest,collector_root,development_work,source_run):
    state=Path(state);v2=Path(v2);d,indices=build_features(state,input_manifest,collector_root,development_work,source_run)
    tag='raw_fraction' if input_manifest['funding_scale']==1 else 'raw_percent';scenario=input_manifest['scenario']
    folder=state/'locked-predictions'/scenario/tag;folder.mkdir(parents=True,exist_ok=True)
    old=json.loads((v2/'FINAL_FITS.json').read_text());new=json.loads((state/'POLICY_FINAL_FITS.json').read_text())
    if old['status']!='COMPLETE' or new['status']!='COMPLETE':raise ValueError('Protected old and new final weights required')
    predictions={};receipts=[];source=json.loads((state/'bridge-work'/scenario/tag/'INPUT_MANIFEST.json').read_text())
    source_sha=sha(state/'bridge-work'/scenario/tag/'INPUT_MANIFEST.json')
    for family in (*V2_FAMILIES,*FAMILIES):
        files=[]
        for seed in SEEDS:
            fit=next(r for r in (new if family in FAMILIES else old)['results'] if r['task']['tag']==tag and r['task']['family']==family and r['task']['seed']==seed)
            path=folder/f'{family}_seed{seed}.npz';receipt=path.with_suffix('.json')
            binding=dict(input_manifest_sha256=source_sha,weights_sha256=fit['result']['weights_sha256'],scaler_sha256=fit['result']['scaler_sha256'],
                         inference_source_sha256=sha(Path(__file__).with_name('locked_features.py')),source_sha256=sha(__file__))
            if receipt.exists():
                prior=json.loads(receipt.read_text())
                if prior['binding']!=binding or sha(path)!=prior['prediction_sha256']:raise ValueError('Frozen bridge prediction changed')
                with np.load(path) as f:pred={k:f[k].copy() for k in f.files}
            else:
                pred=immutable_infer(d,indices,family,fit['folder'],binding['weights_sha256'],binding['scaler_sha256'])
                np.savez_compressed(path,**pred);atomic(receipt,dict(binding=binding,prediction_sha256=sha(path),no_weight_update=True,no_teacher_input=True))
            if not np.array_equal(pred['indices'],indices):raise ValueError('Bridge prediction calendar changed')
            files.append(pred);receipts.append(dict(family=family,seed=seed,path=str(path),sha256=sha(path),binding=binding))
        predictions[family]={k:np.mean([p[k] for p in files],0) for k in files[0] if k!='indices'}
    study=json.loads(Path(source_run,tag,'RESEARCH.json').read_text())['study_dir']
    path=folder/'OLD_FROZEN_TRANSFORMER_SHARED.npz';receipt=path.with_suffix('.json')
    if receipt.exists():
        r=json.loads(receipt.read_text())
        if r['input_manifest_sha256']!=source_sha or sha(path)!=r['sha256']:raise ValueError('Stale baseline bridge prediction changed')
        with np.load(path) as f:pred={k:f[k].copy() for k in f.files}
    else:
        pred,proof=immutable_legacy_transformer(d,indices,study);np.savez_compressed(path,**pred)
        atomic(receipt,dict(input_manifest_sha256=source_sha,sha256=sha(path),proof=proof))
    predictions['OLD_FROZEN_TRANSFORMER_SHARED']=pred
    frozen=dict(input_manifest_sha256=source_sha,files=receipts,legacy_receipt_sha256=sha(receipt),seed_rule='ALL_THREE_FIXED_PREDICTIONS_AVERAGED_NO_WINNER',
                scenario=scenario,funding_scale=input_manifest['funding_scale'],no_locked_labels_for_training=True,all_predictions_before_wallet=True)
    marker=folder/'PREDICTIONS_FROZEN.json'
    if marker.exists():
        if json.loads(marker.read_text())!=frozen:raise ValueError('Bridge forecast freeze changed')
    else:atomic(marker,frozen)
    return d,indices,predictions

def tasks_for(a,input_manifest):
    state=Path(a.state);release_path,release=require_freeze(state)
    d,indices,predictions=frozen_predictions(state,a.v2_state,input_manifest,a.collector_root,a.work,a.source_run)
    tag='raw_fraction' if input_manifest['funding_scale']==1 else 'raw_percent';scenario=input_manifest['scenario']
    root=state/'locked-bridge-native'/scenario/tag
    active=d['ready'][indices]&np.array([s in release['active_symbols'] for s in d['symbols']])[None,:]
    window=dict(id='LOCKED_20260301_20260831',start=1772323200000000,end=1788220800000000,days=184,fold='LOCKED',active_symbols=release['active_symbols'])
    tasks=[];manifest=state/'bridge-work'/scenario/tag/'INPUT_MANIFEST.json'
    def add(family,mapping,profile,weights):
        path=state/'locked-bridge-targets'/scenario/tag/f'{family}_{profile}_{mapping}.npz';weights=weights.copy();weights[-1]=0.
        save_targets(path,d['dates'][indices].as_unit('us').asi8+DAY,weights,d['symbols'])
        tasks.append(dict(id=f'{family}/{profile}/{mapping}',state=str(root),family=family,seed='FROZEN_LEGACY' if family=='OLD_FROZEN_TRANSFORMER_SHARED' else 'ENSEMBLE',mapping=mapping,profile=profile,
            window=window,funding_scale=input_manifest['funding_scale'],scenario=scenario,work=input_manifest['work'],collector_root=a.collector_root,source_run=a.source_run,
            target_path=str(path),target_sha256=sha(path),protocol_sha256=release['protocol_sha256'],locked_release_path=str(release_path),locked_release_sha256=sha(release_path),
            market_input_manifest_path=str(manifest),market_input_manifest_sha256=sha(manifest),funding_estimates=input_manifest['estimates'],
            bridge_preregistration_sha256=input_manifest['preregistration_sha256'],noncausal=False))
    for profile in ('FULL','HALF'):
        gross=.6 if profile=='FULL' else .3
        for family,pred in predictions.items():
            for mapping in (('DIRECTIONAL',) if family=='OLD_FROZEN_TRANSFORMER_SHARED' else ('DIRECTIONAL','NEUTRAL','COMBINED')):
                weights=policy_targets(pred,d['sma'][indices],active,mapping,profile) if family in FAMILIES else portfolio_targets(pred,d['sma'][indices],active,mapping)*(1. if profile=='FULL' else .5)
                add(family,mapping,profile,weights)
        for family in BASELINES:
            # Ordinary fixed expert allocation, not the optional exposure-matched
            # helper's redistribution toward a target gross after CASH choices.
            position=dict(BASE_HOLD=np.ones_like(d['sma'][indices]),BASE_SMA200_SIGNED=d['sma'][indices],
                          BASE_STATIC_DIRECTION3=.5*d['sma'][indices]+.25,BASE_CASH=np.zeros_like(d['sma'][indices]))[family]
            weights=np.where(np.isfinite(position),position,0.)*active*gross/np.maximum(active.sum(1,keepdims=True),1)
            add(family,'DIRECTIONAL',profile,weights)
    if len(tasks)!=40:raise ValueError('Exactly40 fixed locked comparisons per bridge/funding source')
    atomic(root/'LOCKED_TARGETS_FROZEN.json',dict(tasks=tasks,scenario=scenario,source_manifest_sha256=sha(manifest),no_outcome_driven_selection=True))
    return tasks,root

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--v2-state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);p.add_argument('--workers',type=int,default=10)
    p.add_argument('--single-source',action='store_true');p.add_argument('--scenario',choices=SCENARIOS);p.add_argument('--funding-scale',type=float,choices=(1.,.01));a=p.parse_args()
    if platform.system()!='Linux' or os.environ.get('WSL_DISTRO_NAME'):raise RuntimeError('Independent Linux server only')
    state=Path(a.state);require_freeze(state);inputs=json.loads((state/'BRIDGE_INPUTS.json').read_text())
    if inputs['total']!=10:raise ValueError('All five bridges and both funding interpretations required')
    if a.single_source:
        manifest=next(r for r in inputs['scenarios'] if r['scenario']==a.scenario and r['funding_scale']==a.funding_scale)
        tasks,root=tasks_for(a,manifest);run_tasks(tasks,root,'LOCKED_BRIDGE_RESULTS',a.workers);return
    results=[]
    for scenario in SCENARIOS:
        for scale in (1.,.01):
            manifest=next(r for r in inputs['scenarios'] if r['scenario']==scenario and r['funding_scale']==scale)
            # The market adapter captures WORK on import. A whole fresh process
            # per source prevents a previous scenario's rate table from leaking
            # into reference preparation, inference or native worker setup.
            atomic(state/'locked-bridge-progress.json',dict(stage='IMPUTED_LOCKED_SENSITIVITY',completed=len(results),total=400,active_scenario=scenario,funding_scale=scale))
            command=[sys.executable,'-u','-m','modules.transformer_v3.locked_evaluate','--single-source','--scenario',scenario,'--funding-scale',str(scale),
                     '--state',a.state,'--v2-state',a.v2_state,'--collector-root',a.collector_root,'--work',a.work,'--source-run',a.source_run,'--workers',str(a.workers)]
            subprocess.run(command,check=True)
            tag='raw_fraction' if scale==1 else 'raw_percent';root=state/'locked-bridge-native'/scenario/tag
            result=json.loads((root/'LOCKED_BRIDGE_RESULTS.json').read_text())
            if result['status']!='COMPLETE' or result['errors'] or len(result['cases'])!=40:raise ValueError('Bridge source did not finish every comparison')
            cases=result['cases']
            results.extend(cases)
            atomic(state/'LOCKED_BRIDGE_PROGRESS_RESULTS.json',dict(cases=results,completed=len(results),total_cases=400,scenarios_required=list(SCENARIOS),original_formal_v2_N_E_preserved=True))
    atomic(state/'IMPUTED_LOCKED_SENSITIVITY.json',dict(status='COMPLETE_IMPUTED_LOCKED_SENSITIVITY',cases=results,total_cases=400,scenarios=list(SCENARIOS),
           min_median_max_required=True,no_best_scenario_headline=True,no_locked_refit_or_selection=True,original_formal_v2_N_E_preserved=True))

if __name__=='__main__':main()
