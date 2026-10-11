"""Training-prefix source covariance and dependence; no future labels or fits."""
import argparse
import io
import json
from pathlib import Path
import time
import numpy as np
from prepare import HERE,SYMBOLS,PHASES,SourceReader,digest,git,old_five,save
from join import assemble

PREFIX='research/core5-continuous-risk600-20261011/'


def dependence(x):
    x=np.asarray(x,dtype=float);z=x-x.mean();den=float(z@z)
    assert len(x)>60 and den>0 and np.isfinite(x).all()
    rho=np.asarray([float(z[k:]@z[:-k]/den) for k in range(1,31)])
    factor=float(1+2*np.sum((1-np.arange(1,31)/31)*rho))
    return dict(observations=len(x),lag1=float(rho[0]),lag7=float(rho[6]),lag30=float(rho[29]),
        Bartlett30_integrated_variance_factor=factor,conditional_stationary_mean_information_equivalent=len(x)/max(1,factor),
        limitation='Not forecast-testESS, independent marketregimes or MCMCconvergence certification')


def run(commit,output):
    assert not output.exists();output.mkdir();start=time.monotonic()
    full,coverage=assemble(commit);assert coverage['valid_continuous_joint_dates']>=600
    t,year,yearsha=old_five();panels=[year];clocks=[t];sources=[dict(commit='b4756ec8fb59457cfd8db74a79ca6a859f07f331',member_SHA256=yearsha)]
    for phase in list(PHASES)[1:]:
        raw=git('show',commit+':'+PREFIX+'phases/'+phase+'/SOURCE_INDEX.json');index=json.loads(raw)
        row=index['artifacts']['FIVE_MIN.npz'];b=b''.join(SourceReader.part(commit,p) for p in row['parts'])
        assert digest(b)==row['SHA256'] and len(b)==row['bytes']
        with np.load(io.BytesIO(b),allow_pickle=False) as a:
            assert tuple(a['symbol_order'])==SYMBOLS
            panels.append(a['close'].copy());clocks.append(a['available_us'].copy())
        sources.append(dict(phase=phase,index_SHA256=digest(raw),panel_SHA256=digest(b)))
    panel=np.concatenate(panels);clock=np.concatenate(clocks)
    np.testing.assert_array_equal(clock[287::288],full['available_us'])
    assert panel.shape==(699*288,5) and np.all(np.diff(clock)==300000000)
    returns=np.diff(np.log(np.vstack([np.full((1,5),np.nan),panel])),axis=0).reshape(699,288,5)
    selected=(full['available_us']>1609545600000000)&(full['available_us']<=1664582400000000)
    assert selected.sum()==637  # ActualcompletedfeatureJan2–Sep30, availableJan3–Oct1.
    r=returns[selected];cov=np.einsum('dti,dtj->dij',r,r)
    diagonal=np.diagonal(cov,axis1=1,axis2=2)
    np.testing.assert_allclose(diagonal,full['RV_5m'][selected],rtol=2e-14,atol=1e-18)
    scale=np.sqrt(diagonal);corr=cov/scale[:,:,None]/scale[:,None,:]
    np.testing.assert_allclose(np.diagonal(corr,axis1=1,axis2=2),1,rtol=2e-14,atol=1e-14)
    assert np.min(np.linalg.eigvalsh(cov))>-1e-12
    pairs=np.column_stack([corr[:,i,j] for i in range(5) for j in range(i+1,5)])
    breadth=25/np.square(corr).sum((1,2))
    ratios={}
    for name,w in (('FIXED_LONG_SOURCE_MEASUREMENT',np.full(5,.12)),('FIXED_SIGNED_SOURCE_MEASUREMENT',np.array([.12,.12,-.12,-.12,0]))):
        assert abs(w).sum()<=.6+1e-12 and abs(w).max()<=.3
        ratio=np.einsum('i,dij,j->d',w,cov,w)/np.sum(w*w*diagonal,axis=1)
        ratios[name]=dict(weights=w.tolist(),completed_day_covariance_to_diagonal_variance_quantiles=np.quantile(ratio,[.05,.5,.95]).tolist(),
            source_measurement_only=True,wallets=0,future_targets=0)
    np.savez_compressed(output/'TRAINING_SOURCE_COVARIANCE.npz',symbol_order=np.asarray(SYMBOLS),available_us=full['available_us'][selected],
        covariance=cov,correlation=corr)
    proof=dict(status='PASS_TRAINING_PREFIX_SOURCE_INFORMATION_AND_DEPENDENCE_ONLY',dataset_commit=commit,
        protocol_SHA256=digest((HERE/'INFORMATION_PROTOCOL.json').read_bytes()),code_SHA256=digest(Path(__file__).read_bytes()),
        source_panels=sources,training_completed_feature_days=637,excluded_OctNov_feature_days=61,
        eigenvalue_participation_breadth_quantiles=np.quantile(breadth,[.05,.5,.95]).tolist(),
        contemporaneous_pair_correlation_quantiles=np.quantile(pairs,[.05,.5,.95]).tolist(),
        pairwise_correlation_temporal_standard_deviations=np.std(pairs,axis=0,ddof=1).tolist(),
        source_quadratic_diagnostics=ratios,dependence={s:dependence(np.log(diagonal[:,i])) for i,s in enumerate(SYMBOLS)},
        mean_pair_correlation_dependence=dependence(pairs.mean(1)),
        logRV_cross_asset_correlation=np.corrcoef(np.log(diagonal).T).tolist(),
        artifact_SHA256=digest((output/'TRAINING_SOURCE_COVARIANCE.npz').read_bytes()),
        scientific_fits=0,wallets=0,future_labels=0,diagnostic_attempt=1,elapsed_seconds=time.monotonic()-start,
        conclusion_scope='Crosscovariance is source information omitted by diagonal/scalar RV. Its variability and these retrospective source ratios do not establish future predictability, incrementalPnL, mark/liquidationprotection or nativeexecution. Mean-information estimates assume stationarity; these are seen marketregimes. No nextmodel selection from test outcomes.')
    assert time.monotonic()-start<120
    save(output/'INFORMATION.json',proof);print(json.dumps({k:v for k,v in proof.items() if k not in ('source_panels','logRV_cross_asset_correlation')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.commit,a.output)
