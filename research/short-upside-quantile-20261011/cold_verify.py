"""Public byte restore and algebraic saved-forecast verification, zero refits."""
import argparse
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile
import numpy as np
import tail
from tail import SYMBOLS,Q,summarize,feature,forecast,pinball,bootstrap,downsize
from prepare import digest,file_sha

PREFIX='research/short-upside-quantile-20261011/'


def run(commit,directory):
    directory.mkdir(parents=True,exist_ok=False)
    denied=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            name=str(Path(args[0]).absolute())
            if any(name.startswith('/workspace/'+p+'/') for p in ('tail-risk-state','har-rv-state','core5-2022-rv-state','btc-beta-residual-state','october2022-union-state','october2022-complete-state')):
                denied.append(name);raise RuntimeError('Original STATE access forbidden')
    sys.addaudithook(audit)
    def forbidden(*a,**k):
        raise RuntimeError('New fit forbidden during cold verification')
    tail.fit_quantile=tail.calibrate=forbidden
    def fetch(sha,path):
        with urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+sha+'/'+path,timeout=20) as r:
            b=r.read(8000001)
        assert len(b)<8000001
        return b
    manifest=json.loads(fetch(commit,PREFIX+'PUBLIC_BUNDLE.json'))
    chunks=[]
    for part in manifest['parts']:
        b=fetch(commit,PREFIX+part['path'])
        assert len(b)==part['bytes'] and digest(b)==part['SHA256'];chunks.append(b)
    b=b''.join(chunks)
    assert len(b)==manifest['bytes'] and digest(b)==manifest['SHA256']
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        assert z.testzip() is None and set(z.namelist())==set(manifest['members'])
        for name,row in manifest['members'].items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            b=z.read(name)
            assert len(b)==row['bytes'] and digest(b)==row['SHA256']
            p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    result=json.loads((directory/'diagnostic/RESULT.json').read_bytes())
    for name,sha in result['artifacts'].items():
        assert file_sha(directory/'diagnostic'/name)==sha
    sources=[]
    for line in fetch(result['source_commit'],PREFIX+'SOURCE_SHA256.txt').decode().splitlines():
        expected,path=line.split(maxsplit=1)
        assert digest(fetch(result['source_commit'],path))==expected
        sources.append(dict(path=path,SHA256=expected))
    oldpanels=[]
    for row in manifest['reuse']:
        b=fetch(row['commit'],row['path']);assert digest(b)==row['SHA256']
        if 'read_only_member' in row:
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                b=z.read(row['read_only_member'])
        oldpanels.append(np.load(io.BytesIO(b),allow_pickle=False))
    trade2021,october,november=oldpanels
    new=np.load(directory/'prepared/NEW_MARK2021.npz',allow_pickle=False)
    assert tuple(new['symbol_order'])==SYMBOLS
    values=dict(symbol_order=np.asarray(SYMBOLS),A2021_available_us=new['available_us'],A2021_mark=new['mark'],
        A2021_trade=np.column_stack([trade2021[s][:334*288] for s in SYMBOLS]),
        A2022_available_us=np.r_[october['available_us'],november['available_us']],
        A2022_mark=np.column_stack([np.r_[october['markPriceKlines_'+s],november['markPriceKlines_'+s]] for s in SYMBOLS]),
        A2022_trade=np.column_stack([np.r_[october['klines_'+s],november['klines_'+s]] for s in SYMBOLS]))
    np.savez_compressed(directory/'prepared/SOURCE_PANELS.npz',**values)
    recovery=json.loads((directory/'prepared/RECOVERY.json').read_bytes())
    for name,sha in recovery['artifacts'].items():
        assert file_sha(directory/'prepared'/name)==sha
    profiles={label:summarize(values[label+'_mark'],values[label+'_available_us']) for label in ('A2021','A2022')}
    model=json.loads((directory/'diagnostic/MODEL.json').read_bytes());p=profiles['A2021'];ix=np.asarray(model['train_indices'])
    x=np.asarray([feature(p,int(i))[0] for i in ix]);sigma=np.asarray([feature(p,int(i))[1] for i in ix]);actual=p['excursion'][ix+1]
    largest_certificate_error=0.
    for j,m in enumerate(model['models']):
        np.testing.assert_array_equal(x[:,j,:].mean(0),m['mean'])
        np.testing.assert_array_equal(x[:,j,:].std(0),m['std'])
        design=np.column_stack([np.ones(211),(x[:,j,:]-m['mean'])/m['std']]);y=actual[:,j]/sigma[:,j]
        lp=m['LP'];beta=np.asarray(lp['coefficients']);dual=np.asarray(lp['dual'])
        u=np.asarray(lp['residual_positive']);v=np.asarray(lp['residual_negative'])
        errors=[float(abs(design@beta+u-v-y).max()),float(abs(design.T@dual).max()),abs(float(pinball(y,design@beta).sum()-lp['normalized_pinball_sum']))]
        largest_certificate_error=max(largest_certificate_error,*errors)
        assert max(errors)<1e-6 and min(dual)>=Q-1-1e-7 and max(dual)<=Q+1e-7
        assert float(np.quantile(y,Q))==m['empirical_scaled'] and float(np.quantile(actual[:,j],Q))==m['empirical_unconditional']
    constant=np.array([m['empirical_unconditional'] for m in model['models']])
    static=np.asarray([np.minimum(1,constant/forecast(p,int(i),model)['CONDITIONAL']) for i in ix]).mean(0)
    np.testing.assert_array_equal(static,result['static_training_short_scale'])
    saved=np.load(directory/'diagnostic/SAVED_FORECASTS_TARGETS.npz',allow_pickle=False)
    maximum_forecast_error=0.;maximum_target_error=0.;gates={'future_suffix_error_zero':result['future_suffix_forecast_error']==0}
    for block,label in (('SEP_NOV2021','A2021'),('NOV2022','A2022')):
        profile=profiles[label];c=np.load(directory/('prepared/BASE'+label[1:]+'.npz'),allow_pickle=False)
        dates=saved[block+'_decision_us'];indices=np.searchsorted(profile['available'],dates)
        np.testing.assert_array_equal(profile['available'][indices],dates)
        np.testing.assert_array_equal(profile['available'][indices+1],saved[block+'_label_mature_us'])
        actual=profile['excursion'][indices+1];np.testing.assert_array_equal(actual,saved[block+'_actual'])
        for k,i in enumerate(indices):
            f=forecast(profile,int(i),model);j=int(np.searchsorted(c['decision_us'],dates[k]));base=c['base'][j]
            for a,v in f.items():
                maximum_forecast_error=max(maximum_forecast_error,float(abs(v-saved[block+'_forecast_'+a][k]).max()))
            for a,s in (('BASE',None),('CONDITIONAL',np.minimum(1,constant/f['CONDITIONAL'])),('VOL_SCALED',np.minimum(1,constant/f['VOL_SCALED'])),('STATIC_TRAIN',static)):
                w=base if s is None else downsize(base,s,c['past_returns'][j])[0]
                maximum_target_error=max(maximum_target_error,float(abs(w-saved[block+'_weights_'+a][k]).max()))
        loss={a:pinball(actual,saved[block+'_forecast_'+a]) for a in ('CONDITIONAL','VOL_SCALED','UNCONDITIONAL')}
        ci=bootstrap(np.column_stack([(loss['CONDITIONAL']-loss[a]).mean(1) for a in ('VOL_SCALED','UNCONDITIONAL')]))
        np.testing.assert_array_equal(ci,result['diagnostic_blocks'][block]['paired_bootstrap95'])
        coverage=float((actual<=saved[block+'_forecast_CONDITIONAL']).mean())
        assert coverage==result['diagnostic_blocks'][block]['conditional_coverage']
        gates[block+'_coverage']=.8<=coverage<=.98
        comparison=result['diagnostic_blocks'][block]['comparisons']['VOL_SCALED']
        improvement=1-float(loss['CONDITIONAL'].mean()/loss['VOL_SCALED'].mean())
        improved=int(np.sum(loss['CONDITIONAL'].mean(0)<loss['VOL_SCALED'].mean(0)))
        assert improvement==comparison['relative_pinball_improvement'] and improved==comparison['improved_assets']
        gates[block+'_relative_improvement_ge002']=improvement>=.02;gates[block+'_at_least3_assets']=improved>=3
        for j,a in enumerate(('VOL_SCALED','UNCONDITIONAL')):
            gates[block+'_'+a+'_bootstrap_upper_negative']=bool(ci[j,1]<0)
    assert gates==result['gates'] and not all(gates.values())
    assert maximum_forecast_error<1e-12 and maximum_target_error<1e-12 and not denied
    proof=dict(status='PASS_PUBLIC_SAVED_QUANTILE_COLD_RESTORE',artifact_commit=commit,source_commit=result['source_commit'],
        recovered_members=len(manifest['members']),source_checks=sources,new_fits=0,new_solver_calls=0,wallets=0,
        original_STATE_open_attempts=len(denied),maximum_forecast_error=maximum_forecast_error,maximum_target_error=maximum_target_error,
        maximum_LP_certificate_error=largest_certificate_error,forecast_rows=120,training_rows_each_asset=211,
        model_and_scaler_train_only=True,bootstrap_and_gate_exact=True,source_panels_byte_exact=True,
        scientific_result='STOP_FIXED_SHORT_UPSIDE_QUANTILE',existing_large_sources_reuploaded=0)
    (directory/'PUBLIC_RESTORE.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');print(json.dumps(proof))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--directory',type=Path,required=True)
    a=p.parse_args();run(a.commit,a.directory)
