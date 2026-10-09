"""Inspect recovered causal daily observations; no labels, training or wallets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
START, END, DAY = 1714521600000000, 1719792000000000, 86400000000
SYMBOLS = ('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6_000_000_000,6_000_000_000))
    sys.path[:0]=[str(REPO),str(REPO/'src')]
    expected_sources={
        'modules/collector_research/pipeline/make_labels.py':'28a416779f50f17d73e9a7375328fb0e127e99702f88cce48f20b6ff4f8e05d8',
        'modules/collector_research/pipeline/train.py':'b43020d7a7c6357ee71d645042e10695c3d4030fee049323d27cb5fb93d03ab8'}
    for path,digest in expected_sources.items():
        assert sha(REPO/path)==digest,'Original public V3 feature source differs'
    import numpy as np
    import pandas as pd
    from modules.collector_research.pipeline.make_labels import feature_frame,BASE_FEATURES
    from modules.collector_research.pipeline.train import market_features
    root=a.state/'h1_validation/original/h1_market/data/normalized'
    sources,frames,features={},{},{}
    for s in SYMBOLS:
        path=root/(s+'_daily.parquet');d=pd.read_parquet(path)
        # Exclude all later history before computing the causal transforms.
        d=d.loc[d.available_us<END].reset_index(drop=True)
        assert np.array_equal(d.available_us.to_numpy(),pd.DatetimeIndex(d.dt).as_unit('us').asi8+DAY)
        sources[s]=dict(sha256=sha(path),calendar_rows=len(d),first_observation=d.dt.iloc[0].isoformat(),last_observation=d.dt.iloc[-1].isoformat())
        frames[s]=d;features[s]=feature_frame(d,64)
    market=market_features(features).reset_index(drop=True)
    names=BASE_FEATURES+list(market.columns);assert len(names)==24
    x=np.stack([pd.concat([features[s][BASE_FEATURES],market],axis=1).to_numpy(float) for s in SYMBOLS],1)
    finite=np.isfinite(x);dates=frames[SYMBOLS[0]].available_us.to_numpy(np.int64)
    assert all(np.array_equal(frames[s].available_us.to_numpy(),dates) for s in SYMBOLS)
    assert np.all(np.diff(dates)==DAY)
    pre=dates<START;valid=np.array([np.flatnonzero(dates==t)[0] for t in np.arange(START,END,DAY)])
    rows={};all_ready=[];all_feature_ready=[]
    def iso(t):return pd.Timestamp(int(t),unit='us',tz='UTC').isoformat()
    def ranges(indices):
        if not len(indices):return []
        boundaries=np.flatnonzero(np.diff(indices)!=1)+1
        return [dict(first_decision=iso(dates[g[0]]),last_decision=iso(dates[g[-1]]),days=len(g)) for g in np.split(indices,boundaries)]
    for j,s in enumerate(SYMBOLS):
        d=frames[s];actual=d.complete_kline.astype(bool).to_numpy()&np.isfinite(d.close.to_numpy())&(d.close.to_numpy()>0)
        seq=pd.Series(actual).rolling(64,min_periods=64).sum().eq(64).to_numpy()
        all_ready.append(seq)
        feature_seq=pd.Series(finite[:,j].all(1)).rolling(64,min_periods=64).sum().eq(64).to_numpy()
        all_feature_ready.append(feature_seq)
        training=np.flatnonzero(pre&seq)
        windows=np.array([np.arange(i-63,i+1) for i in valid])
        assert windows.min()>=0 and np.all(dates[windows]<=dates[valid,None])
        warmup=windows[0]
        long_warmup=np.arange(valid[0]-263,valid[0]+1)
        rows[s]=dict(actual_pre_May_close_rows=int((pre&actual).sum()),first_actual_observation=d.dt.iloc[np.flatnonzero(actual)[0]].isoformat(),
            causal64_price_ready_pre_May_decisions=len(training),causal64_price_ready_pre_May_date_ranges=ranges(training),
            feature_valid_counts_pre_May={name:int(finite[pre,j,k].sum()) for k,name in enumerate(names)},
            May1_window=dict(observation_start=d.dt.iloc[warmup[0]].isoformat(),observation_end=d.dt.iloc[warmup[-1]].isoformat(),
                actual_price_days=int(actual[warmup].sum()),days=64,valid_feature_cells=int(finite[warmup,j].sum()),total_feature_cells=64*24,
                latest_feature_available_us=int(dates[warmup[-1]]),decision_us=START),
            validation_price64_complete_days=int(seq[valid].sum()),validation_decisions=61,
            fully_finite_feature64_pre_May_decisions=int((pre&feature_seq).sum()),
            validation_all24_feature64_complete_days=int(feature_seq[valid].sum()),
            May1_mom200_all64_steps_price_provenance=dict(required_actual_completed_closes=264,
                observation_start=d.dt.iloc[long_warmup[0]].isoformat(),observation_end=d.dt.iloc[long_warmup[-1]].isoformat(),
                actual_price_days=int(actual[long_warmup].sum()),latest_available_us=int(dates[long_warmup[-1]])),
            missing_premium_pre_May=int((pre&~d.complete_premium.astype(bool).to_numpy()).sum()),
            missing_funding_pre_May=int((pre&~d.complete_funding.astype(bool).to_numpy()).sum()))
    common=np.all(all_ready,axis=0)
    report=dict(schema='ACTUAL_RECOVERED_DAILY_CAUSAL64_COVERAGE_V1',status='PASS_TRUTHFUL_CORE5_COVERAGE_WITH_EXPLICIT_MASKS',
        original_daily_source=sources,feature_order=names,symbol_order=list(SYMBOLS),feature_count=24,mask_count=24,window_days=64,
        features='EXISTING_V2_V3_FEATURE_FRAME_FORMULAS_PLUS_SAME_MARKET_FORMULAS_ON_CORE5',
        original10asset_feature_bundle_recovered=False,original10asset_feature_equivalence_claimed=False,
        panel_role='DERIVED_CAUSAL_CORE5_RECONSTRUCTION_FROM_PUBLIC_H1_DAILY_PREFIXES_NOT_ORIGINAL_V2_V3_FULL_FEATURE_BYTES',
        pre_May_calendar_decisions=int(pre.sum()),first_pre_May_decision=iso(dates[0]),last_pre_May_decision=iso(dates[pre][-1]),
        common5asset_price64_ready_pre_May_decisions=int((pre&common).sum()),common5asset_price64_ready_date_ranges=ranges(np.flatnonzero(pre&common)),
        common5asset_all24_feature64_ready_pre_May_decisions=int((pre&np.all(all_feature_ready,axis=0)).sum()),
        assets=rows,training_labels='NOT_CREATED_OR_CERTIFIED_WALLET_PATH_MATURITY_REMAINS_REQUIRED',
        feature_coverage_is_continuous_wallet_coverage=False,development_seen=True,new_unseen_OOS=False,
        labels_read=False,fits=0,wallet_runs=0,hourly_synthesis=False,
        source_functions_sha256={str(q.relative_to(REPO)):sha(q) for q in [REPO/'modules/collector_research/pipeline/make_labels.py',REPO/'modules/collector_research/pipeline/train.py']})
    a.output.mkdir(exist_ok=False)
    producer=dict(schema='VERIFIED_CAUSAL_CORE5_DAILY_FEATURE_PRODUCER_V1',
        original_public_commit='d69e9ac94478c5be54cb46c622afec7aaf3c61f7',
        original_public_H1_archive_sha256='a998b786d781a5dd314c6efb44dc55702972977b9bdf2fea315426b7c4362deb',
        original_data_manifest_sha256=sha(a.state/'h1_validation/original/h1_market/reports/DATASET_MANIFEST.json'),
        source_daily_files=sources,source_functions_sha256=report['source_functions_sha256'],
        producer_script_sha256=sha(Path(__file__)),symbol_order=list(SYMBOLS),feature_order=names,
        completed_bar_clock='ORIGINAL_DAILY_AVAILABLE_US_EQUAL_UTC_BAR_COMPLETION',
        derived_feature_availability='AT_COMPLETED_BAR_BOUNDARY_FROM_CAUSAL_FORMULAS_HISTORICAL_PUBLICATION_UNCERTIFIED',
        unavailable_features='PRESERVED_NAN_WITH_FALSE_VALIDITY_NO_INTERPOLATION',
        model_input_contract_commit='f90d798f5dc3d26310c87f940c8da9b2c0031ee1',
        wallet_label_maturity='NOT_CREATED_OR_CERTIFIED',seen_development=True,original10asset_panel_equivalence=False)
    (a.output/'FEATURE_PRODUCER_MANIFEST.json').write_text(json.dumps(producer,indent=2)+'\n')
    producer_sha=sha(a.output/'FEATURE_PRODUCER_MANIFEST.json')
    step_valid=np.stack([frames[s].complete_kline.astype(bool).to_numpy()&np.isfinite(frames[s].close.to_numpy())&(frames[s].close.to_numpy()>0) for s in SYMBOLS],1)
    availability=np.broadcast_to(dates[:,None,None],x.shape).copy()
    np.savez_compressed(a.output/'CAUSAL_CORE5_24_FEATURE_PANEL.npz',completed_us=dates,symbol_order=np.asarray(SYMBOLS),feature_names=np.asarray(names),
        values=x,valid=finite,step_valid=step_valid,available_us=availability,source_sha256=np.asarray(producer_sha))
    report['derived_panel_sha256']=sha(a.output/'CAUSAL_CORE5_24_FEATURE_PANEL.npz')
    report['producer_manifest_sha256']=producer_sha
    report['NPZ_schema_matches_temporal_input_contract_commit']='f90d798f5dc3d26310c87f940c8da9b2c0031ee1'
    (a.output/'DAILY_FEATURE_COVERAGE.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','feature_count','mask_count','pre_May_calendar_decisions','common5asset_price64_ready_pre_May_decisions','common5asset_price64_ready_date_ranges']}|dict(warmup={s:rows[s]['May1_window'] for s in SYMBOLS})),flush=True)


if __name__=='__main__':main()
