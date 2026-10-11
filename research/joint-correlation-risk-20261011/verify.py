"""Public-only fresh-state recovery; restore model, never fit or run a wallet."""
import argparse
import io
import json
from pathlib import Path
import shutil
import time
import numpy as np
from joint import SYMBOLS,utc,forecast,size
from inputs import HERE,ROOT,SOURCE,digest,git,save,recover
from diagnostics import NAMES,TARGET_NAMES,prediction,proportional_controls
from scripts.research.public_cross_section_momentum import public_targets
from scripts.investment.public_sma_perpetual import signed_risk_weights

PREFIX='research/joint-correlation-risk-20261011/'


def from_git(commit,path):
    return git('show',commit+':'+PREFIX+path)


def npz(raw):
    with np.load(io.BytesIO(raw),allow_pickle=False) as a:return {k:a[k].copy() for k in a.files}


def run(commit,output):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists()
    assert shutil.disk_usage('/workspace').free>=16106127360
    output.mkdir();start=time.monotonic()
    # Named public artifacts only; zero reads of original model/data STATE.
    result_raw=from_git(commit,'result/RESULT.json');result=json.loads(result_raw)
    model_raw=from_git(commit,'result/MODEL.json');model=json.loads(model_raw)
    assert result['scientific_attempts']==result['fits']==result['parameters']==1
    assert result['conclusion']=='STOP_FIXED_JOINT_CORRELATION_BLEND' and result['wallets']==0
    protocol=from_git(commit,'PROTOCOL.json');assert digest(protocol)==result['protocol_SHA256']
    assert protocol==git('show',result['freeze_commit']+':'+PREFIX+'PROTOCOL.json')
    for filename in ('joint.py','inputs.py','diagnostics.py','run.py'):
        old=from_git(result['source_HEAD'],filename)
        assert old==from_git(commit,filename)==(HERE/filename).read_bytes()
    for filename in ('FROZEN_SOURCE_SHA256.txt','FROZEN_IMPLEMENTATION_SHA256.txt'):
        for line in from_git(commit,filename).decode().splitlines():
            sha,path=line.split(maxsplit=1)
            assert digest(git('show',result['source_HEAD']+':'+path))==sha
            assert digest((ROOT/path).read_bytes())==sha
    for name,row in result['artifacts'].items():
        b=from_git(commit,'result/'+name)
        assert len(b)==row['bytes'] and digest(b)==row['SHA256']
        with (output/name).open('xb') as f:f.write(b)
    assert model['input_SHA256']==result['source_SHA256']
    assert model['latest_label_maturity_us']<model['fit_at_us']==utc('2022-01-01')
    assert tuple(model['symbol_order'])==SYMBOLS and 0<=model['theta']<=1
    source_raw=from_git(commit,'prepared/SOURCE_INPUTS.npz')
    assert digest(source_raw)==result['source_SHA256']
    expected=npz(source_raw)
    recovered,r,source_proof=recover()
    for k in expected:np.testing.assert_array_equal(recovered[k],expected[k])
    t=expected['available_us'];close=expected['close'];c=expected['realized_covariance']
    f=npz(from_git(commit,'result/FORECASTS.npz'));w=npz(from_git(commit,'result/TARGETS.npz'))
    assert tuple(f['forecast_names'])==NAMES and tuple(w['target_names'])==TARGET_NAMES
    for key in ('decision_us','label_maturity_us','roles','symbol_order'):
        np.testing.assert_array_equal(f[key],w[key])
    ids=np.searchsorted(t,w['decision_us']);np.testing.assert_array_equal(ids,w['source_indices'])
    np.testing.assert_array_equal(w['label_maturity_us'],t[ids+1])
    assert (w['label_maturity_us'][w['roles']=='TRAIN']<model['fit_at_us']).all()
    for day in json.loads(protocol)['purged_decisions']:assert utc(day) not in w['decision_us']
    base,unused=public_targets(close,t,w['decision_us'],SYMBOLS,SYMBOLS)
    candidate=[];scales=[];forecasts=[];sigma=[];native_sigma=[]
    for k,i in enumerate(ids):
        forecasts_i,cov,simple=forecast(close,c,int(i),model)
        target,s,q,receipt=size(base[k],cov,simple)
        candidate.append(target);scales.append(s);sigma.append(q)
        forecasts.append([forecasts_i[n] for n in NAMES])
        native_sigma.append(float(np.sqrt(max(0,365*float(base[k]@np.cov(simple,rowvar=False,ddof=1)@base[k])))))
    candidate=np.asarray(candidate);predicted=np.asarray(forecasts);scales=np.asarray(scales)
    controls,control_receipt=proportional_controls(base,candidate,scales,w['roles']=='TRAIN',c[ids+1])
    assert control_receipt==json.loads(from_git(commit,'result/CONTROL_CALIBRATION.json'))
    np.testing.assert_array_equal(controls,w['targets']);np.testing.assert_array_equal(scales,w['joint_scalar'])
    np.testing.assert_array_equal(sigma,w['candidate_BASE_annual_sigma'])
    np.testing.assert_array_equal(native_sigma,w['native_annual_sigma'])
    np.testing.assert_array_equal(predicted,f['predicted_correlation'])
    actual=np.asarray([c[i+1]/np.sqrt(np.diag(c[i+1]))[:,None]/np.sqrt(np.diag(c[i+1]))[None,:] for i in ids])
    np.testing.assert_array_equal(actual,f['actual_next_day_correlation'])
    for k,i in enumerate(ids):
        simple=np.diff(close[i-30:i+1],axis=0)/close[i-30:i]
        for j in range(4):
            checked,_=signed_risk_weights(controls[k,j],simple)
            np.testing.assert_allclose(checked,controls[k,j],rtol=1e-12,atol=1e-12)
    report,loss=prediction(predicted,actual,w['roles'])
    assert report==json.loads(from_git(commit,'result/PREDICTION.json'))
    np.testing.assert_array_equal(loss,f['loss'])
    assert not report['passed'] and json.loads(from_git(commit,'result/ECONOMICS.json'))['status']=='NOT_RUN_FAILED_PREDICTION_GATE'
    proof=dict(status='PASS_PUBLIC_COLD_MODEL_AND_PAIRED_DIAGNOSTIC_RESTORE',artifact_commit=commit,
        original_scientific_source_HEAD=result['source_HEAD'],source_commit=SOURCE,
        public_model_SHA256=digest(model_raw),public_result_SHA256=digest(result_raw),
        original_STATE_open_attempts=0,provider_downloads=0,new_scientific_attempts=0,fits=0,wallets=0,
        deterministic_forecast_vector_reconstructions=len(ids),targets_and_native_rechecks_exact=True,
        forecast_vectors_loss_and_statistics_exact=True,source_feature_vectors_exact=True,
        source_information637_exact=source_proof['source_information637_exact'],
        unknown_first_source_boundary_preserved=True,
        economic_scoring='NOT_RUN_FAILED_FROZEN_GATE',elapsed_seconds=time.monotonic()-start,
        code_SHA256=digest(Path(__file__).read_bytes()),
        scope='Public model parameters restored; deterministic arithmetic/CI outputs verified, no model optimization or new trial. Source raw-minute checks reuse prior public cold certificates.')
    assert proof['elapsed_seconds']<120
    save(output/'PUBLIC_RESTORE.json',proof);print(json.dumps(proof,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact-commit',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.artifact_commit,a.output)
