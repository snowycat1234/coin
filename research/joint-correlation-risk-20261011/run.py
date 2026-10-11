"""Exactly one scalar fit and predeclared paired chronological diagnostics."""
import argparse
import io
import json
from pathlib import Path
import platform
import shutil
import time
import numpy as np
from joint import SYMBOLS,DAY,utc,fit,forecast,size
from inputs import HERE,ROOT,digest,git,save,recover
from diagnostics import NAMES,TARGET_NAMES,prediction,proportional_controls,economy
from scripts.research.public_cross_section_momentum import public_targets,ANCHOR_US
from scripts.investment.public_sma_perpetual import signed_risk_weights


def run(prepared,output):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists()
    assert not git('status','--porcelain').strip(), 'Publish complete frozen implementation before historical fit'
    assert shutil.disk_usage('/workspace').free>=16106127360
    frozen=(HERE/'PROTOCOL.json').read_bytes();protocol=json.loads(frozen)
    for line in (HERE/'FROZEN_SOURCE_SHA256.txt').read_text().splitlines():
        sha,p=line.split(maxsplit=1);assert digest((ROOT/p).read_bytes())==sha
    source=(prepared/'SOURCE_INPUTS.npz').read_bytes();proof=json.loads((prepared/'SOURCE_INPUTS.json').read_bytes())
    assert digest(source)==proof['artifact_SHA256'] and proof['source_commit']==protocol['source_commit']
    output.mkdir();start=time.monotonic()
    source_head=git('rev-parse','HEAD').decode().strip()
    save(output/'STARTED.json',dict(scientific_attempt=1,planned_fits=1,seed=811132,source_HEAD=source_head,
        input_SHA256=digest(source),protocol_SHA256=digest(frozen),code_SHA256=digest(Path(__file__).read_bytes()),
        wallets=0,downloads=0))
    with np.load(io.BytesIO(source),allow_pickle=False) as a:
        assert tuple(a['symbol_order'])==SYMBOLS
        t=a['available_us'].copy();close=a['close'].copy();c=a['realized_covariance'].copy()
    model=fit(close,c,t,utc('2021-02-01'),utc('2021-12-30'),utc('2022-01-01'))
    assert model['training_joint_dates']==333
    model.update(protocol_SHA256=digest(frozen),input_SHA256=digest(source),source_HEAD=source_head,
        scientific_attempt=1,fits=1,seed=811132,
        fit_scope='One scalar training-only analytic fit; seen history, no Transformer/HAR/normalizer/optimizer/search')
    save(output/'MODEL.json',model) # Durable fitted parameters before diagnostics.
    ids=np.flatnonzero((t>=utc('2021-02-01'))&(t<=utc('2022-11-30')))
    ids=np.array([i for i in ids if t[i] not in [utc(d) for d in protocol['purged_decisions']]])
    clocks=t[ids];roles=np.full(len(ids),'TRAIN',dtype='U5')
    roles[(clocks>=utc('2022-01-02'))&(clocks<=utc('2022-06-30'))]='A'
    roles[(clocks>=utc('2022-07-02'))&(clocks<=utc('2022-11-30'))]='B'
    assert dict(zip(*np.unique(roles,return_counts=True)))=={'A':180,'B':152,'TRAIN':333}
    base,direction_receipts=public_targets(close,t,clocks,SYMBOLS,SYMBOLS)
    candidate=[];predicted=[];scale=[];candidate_sigma=[];native_sigma=[]
    for k,i in enumerate(ids):
        predictions,cov,simple=forecast(close,c,int(i),model)
        target,s,sigma,recheck=size(base[k],cov,simple)
        candidate.append(target);scale.append(s);candidate_sigma.append(sigma)
        predicted.append([predictions[n] for n in NAMES])
        native=np.cov(simple,rowvar=False,ddof=1)
        native_sigma.append(float(np.sqrt(max(0,365*float(base[k]@native@base[k])))))
        assert np.allclose(np.diag(cov),np.diag(native),rtol=2e-14,atol=1e-16)
    candidate=np.asarray(candidate);predicted=np.asarray(predicted);scale=np.asarray(scale)
    training=roles=='TRAIN';actual_cov=c[ids+1]
    targets,control_receipt=proportional_controls(base,candidate,scale,training,actual_cov)
    for k,i in enumerate(ids):
        simple=np.diff(close[i-30:i+1],axis=0)/close[i-30:i]
        for j in range(4):
            checked,_=signed_risk_weights(targets[k,j],simple)
            np.testing.assert_allclose(checked,targets[k,j],rtol=1e-12,atol=1e-12)
    assert np.abs(targets).max()<=.3+1e-12 and np.max(np.abs(targets).sum(axis=2))<=.6+1e-12
    assert np.max(native_sigma)<=.1+1e-12
    np.testing.assert_array_equal(np.sign(base),np.sign(candidate))
    np.savez_compressed(output/'TARGETS.npz',symbol_order=np.asarray(SYMBOLS),target_names=np.asarray(TARGET_NAMES),
        decision_us=clocks,label_maturity_us=t[ids+1],roles=roles,source_indices=ids,targets=targets,
        joint_scalar=scale,native_annual_sigma=np.asarray(native_sigma),candidate_BASE_annual_sigma=np.asarray(candidate_sigma),
        available_mask=np.ones_like(base,dtype=bool))
    save(output/'CONTROL_CALIBRATION.json',control_receipt)
    actual=np.asarray([c[i+1]/np.sqrt(np.diag(c[i+1]))[:,None]/np.sqrt(np.diag(c[i+1]))[None,:] for i in ids])
    forecast_report,loss=prediction(predicted,actual,roles)
    np.savez_compressed(output/'FORECASTS.npz',symbol_order=np.asarray(SYMBOLS),forecast_names=np.asarray(NAMES),
        decision_us=clocks,label_maturity_us=t[ids+1],roles=roles,predicted_correlation=predicted,
        actual_next_day_correlation=actual,loss=loss)
    save(output/'PREDICTION.json',forecast_report)
    if forecast_report['passed']:
        fresh,r,_=recover()
        np.testing.assert_array_equal(fresh['realized_covariance'],c)
        economic=economy(targets,roles,r[ids+1])
        save(output/'ECONOMICS.json',economic)
        economic_scope=economic['status']
    else:
        economic_scope='NOT_RUN_FAILED_PREDICTION_GATE'
        save(output/'ECONOMICS.json',dict(status=economic_scope,wallets=0,fits=0,
            reason='Frozen gate prohibits tail/turnover economic scoring after prediction failure',
            native_execution='BLOCKED_MARK_AND_FUNDING_CERTIFICATION'))
    artifacts={p.name:dict(bytes=p.stat().st_size,SHA256=digest(p.read_bytes())) for p in output.iterdir()}
    receipt=dict(status='PASS_SINGLE_FIT_AND_FROZEN_PAIRED_DIAGNOSTIC_EXECUTION',
        conclusion=forecast_report['status'] if not forecast_report['passed'] else economic_scope,
        source_HEAD=source_head,freeze_commit='aabdce8ec5058df0dfda5b8ecefbc4256a0223e0',
        protocol_SHA256=digest(frozen),source_SHA256=digest(source),source_commit=protocol['source_commit'],
        code_SHA256=digest(Path(__file__).read_bytes()),environment=dict(Python=platform.python_version(),NumPy=np.__version__),
        scientific_attempts=1,fits=1,parameters=1,seed=811132,downloads=0,wallets=0,
        joint_dates=dict(TRAIN=333,A=180,B=152),latest_train_label_maturity_us=model['latest_label_maturity_us'],
        theta=model['theta'],original_direction_API='REUSED_UNCHANGED public_targets with fullpast context',
        original_anchor_us=ANCHOR_US,availability='Complete actual trade mask; mark/funding execution availability UNKNOWN',
        same_native_variance_diagonal=True,no_relever=True,native_risk_recheck_all_targets=True,
        static_controls_train_only=control_receipt,artifacts=artifacts,elapsed_seconds=time.monotonic()-start,
        domain='Seen-development predictive diagnostic. Native netPnL/liquidation/paid terminal close/trading readiness NOT_RUN_BLOCKED. OldSTOPs unchanged.')
    assert receipt['elapsed_seconds']<120 and sum(p.stat().st_size for p in output.iterdir())<100000000
    save(output/'RESULT.json',receipt)
    print(json.dumps(dict(status=receipt['status'],conclusion=receipt['conclusion'],theta=model['theta'],
        joint_dates=receipt['joint_dates'],prediction=forecast_report['blocks'],elapsed_seconds=receipt['elapsed_seconds']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.prepared,a.output)
