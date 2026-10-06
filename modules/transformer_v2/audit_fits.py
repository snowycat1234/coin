"""Independent read-only audit of every completed fit and train-only scaler."""
import argparse,json
from pathlib import Path
import numpy as np
from .data import load_development,chronological_inner,train_scaler
from .train import sha,atomic,target_scale

def audit_final(state,collector_root,work,source_run):
    import torch
    from .final_fit import final_indices
    state=Path(state);final=json.loads((state/'FINAL_FITS.json').read_text());assert final['status']=='COMPLETE' and final['completed']==24
    plan=state/'FINAL_FIT_PLAN.json';recipe=json.loads(plan.read_text());assert recipe['final_fit_source_sha256']==sha(Path(__file__).with_name('final_fit.py'))
    d=load_development(collector_root,work,source_run);rows=[]
    for fit in final['results']:
        task=fit['task'];folder=Path(fit['folder']);result=json.loads((folder/'RESULT.json').read_text());assert result==fit['result']
        assert result['binding']['final_fit_plan_sha256']==sha(plan)
        indices,active,cutoff=final_indices(d,task['scenario']);assert indices.tolist()==task['training_indices'] and active.tolist()==task['active']
        mu,sd=train_scaler(d['x'],d['availability'],indices);ys,rm,rs=target_scale(d,indices,task['scenario'],active)
        expected=dict(mu=mu,sd=sd,utility_sd=ys,regime_mu=rm,regime_sd=rs)
        with np.load(folder/'scaler.npz') as saved:assert all(np.array_equal(saved[k],v) for k,v in expected.items())
        assert sha(folder/'scaler.npz')==result['scaler_sha256'] and sha(folder/'weights.pt')==result['weights_sha256']
        assert result['best_epoch']==task['epochs']==int(round(np.median(task['development_inner_epochs']))) and result['validation_rows']==0
        weights=torch.load(folder/'weights.pt',map_location='cpu',weights_only=True);assert all(torch.isfinite(v).all() for v in weights.values());del weights
        rows.append(dict(family=task['family'],seed=task['seed'],funding_scale=1. if task['scenario']==0 else .01,
                         fixed_epochs=task['epochs'],training_dates=len(indices),max_label_end=str(d['label_end'][indices].max()),cutoff=str(cutoff),
                         weights_sha256=result['weights_sha256'],scaler_sha256=result['scaler_sha256'],parameters=result['parameters'],device=result['device'],
                         train_only_scaler_verified=True,inner_or_locked_early_stopping=False))
    result=dict(status='ALL24_FINAL_PAST_ONLY_FITS_AUDITED',rows=rows,final_fits_sha256=sha(state/'FINAL_FITS.json'),final_plan_sha256=sha(plan),
                protocol_sha256=final['protocol_sha256'],locked_read=False,failed_attempt_files=[str(p.relative_to(state)) for p in (state/'final-fits').rglob('FINAL_FAILURE_*.json')])
    atomic(state/'TRANSFORMER_V2_FINAL_FIT_AUDIT.json',result);return result

def audit(state,collector_root,work,source_run):
    state=Path(state);repo=Path(__file__).resolve().parents[2];proto=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'
    protocol=json.loads(proto.read_text());binding=json.loads((state/'TRAIN_BINDING.json').read_text())
    assert binding['protocol_sha256']==sha(proto)
    for name,digest in binding['source_sha256'].items():assert sha(Path(__file__).with_name(name))==digest
    d=load_development(collector_root,work,source_run);rows=[]
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
        for fi,fold in enumerate(d['folds'],1):
            train=np.array(sorted({i for _,_,i in fold['train']}));inner,valid=chronological_inner(train,d['dates'],d['label_end'])
            assert (d['label_end'][train]<fold['cutoff']).all()
            active=np.array([s in fold['active'] for s in d['symbols']]);expected={}
            for phase,indices in [('inner',inner),('refit',train)]:
                mu,sd=train_scaler(d['x'],d['availability'],indices);ys,rm,rs=target_scale(d,indices,scenario,active)
                expected[phase]=dict(mu=mu,sd=sd,utility_sd=ys,regime_mu=rm,regime_sd=rs)
            for family in protocol['models']:
                for seed in protocol['seeds']:
                    folder=state/'fits'/tag/f'fold{fi}'/family/f'seed{seed}';complete=json.loads((folder/'FIT_COMPLETE.json').read_text())
                    assert complete['binding']==binding and complete['active']==fold['active']
                    for phase in ('inner','refit'):
                        result=json.loads((folder/phase/'RESULT.json').read_text());assert result['binding']==binding
                        assert result['weights_sha256']==sha(folder/phase/'weights.pt') and result['scaler_sha256']==sha(folder/phase/'scaler.npz')
                        assert result['device']=='cuda' and result['parameters']<10_000_000
                        with np.load(folder/phase/'scaler.npz') as saved:
                            assert all(np.array_equal(saved[k],v) for k,v in expected[phase].items()),'Scaler/target scaling did not use its exact fitting train rows'
                    prediction=folder/'refit/PREDICTIONS.npz';assert sha(prediction)==complete['prediction_sha256']
                    with np.load(prediction) as saved:
                        assert np.array_equal(saved['indices'],fold['calendar'])
                        assert saved['utility'].shape==(len(fold['calendar']),10,2) and saved['relative'].shape==(len(fold['calendar']),10,3)
                        assert all(np.isfinite(saved[k]).all() for k in ('utility','relative','utility_pool','relative_pool','regime_pool'))
                        assert np.allclose(saved['utility'],saved['utility_pool'].mean(1)) and np.allclose(saved['relative'],saved['relative_pool'].mean(1))
                        if family in ('TRANSFORMER_SHARED','CROSS_ASSET_UTILITY'):assert np.allclose(saved['relative'][...,1],-saved['utility'][...,1])
                    selection=json.loads((folder/'inner/RESULT.json').read_text());refit=json.loads((folder/'refit/RESULT.json').read_text())
                    assert 1<=selection['best_epoch']<=40 and refit['best_epoch']==selection['best_epoch']==complete['best_epoch']
                    history=[json.loads(line) for line in (folder/'inner/epochs.jsonl').read_text().splitlines()]
                    assert all(np.isfinite(r['train_loss']) and np.isfinite(r['val_loss']) for r in history)
                    selected=next(r for r in history if r['epoch']==selection['best_epoch']);assert abs(selected['val_loss']-selection['inner_validation_loss'])<1e-10
                    rows.append(dict(family=family,seed=seed,fold=fi,funding_scale=1. if scenario==0 else .01,parameters=refit['parameters'],best_epoch=selection['best_epoch'],
                                     inner_validation_loss=selection['inner_validation_loss'],training_rows=refit['training_rows'],prediction_sha256=sha(prediction),device='cuda',
                                     max_training_label_end=str(d['label_end'][train].max()),cutoff=str(fold['cutoff']),train_only_scaler_verified=True))
    assert len(rows)==120
    result=dict(status='ALL120_CUDA_FITS_HASH_SCALER_MATURITY_PREDICTION_AUDITED',rows=rows,protocol_sha256=sha(proto),locked_read=False,
                failed_attempt_files=[str(p.relative_to(state)) for p in (state/'fits').rglob('FAILURE_ATTEMPT_*.json')])
    atomic(state/'TRANSFORMER_V2_FIT_AUDIT.json',result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);p.add_argument('--final-only',action='store_true');a=p.parse_args()
    result=(audit_final if a.final_only else audit)(a.state,a.collector_root,a.work,a.source_run);print(result['status'])

if __name__=='__main__':main()
