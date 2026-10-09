"""Bind separate input/economic clocks to unchanged original VOL/CS contexts."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen

INPUT_COMMIT='256f6fd8206b1616d59eb3129145bfa74ebde924'
INDEX_SHA='8de3c148daecc2f93844d4ebc41d81c4a8698025ec5f89f31608bff9cdb06153'
RECIPE_SHA='9c6658cd7682b6c5470585cbe927c20893e98a3e071cd52e56c5de280e86f207'
DIAGNOSTICS_SHA='9fed06d21231ea81419396e5a786511ad59286540ce3741349f480ae5e7340c0'
DAY=86_400_000_000
CUTOFF=1714521600000000


def bind(state,output):
    import numpy as np
    frozen.modules(state)
    base=state/'temporal-input-ready';base.mkdir(exist_ok=True)
    url=f'https://raw.githubusercontent.com/snowycat1234/coin/{INPUT_COMMIT}/research/temporal-input-windows-20261009/'
    for n in ('INPUT_READY.json','WINDOW_INDEX.npz'):
        p=base/n
        if not p.exists():p.write_bytes(urllib.request.urlopen(url+n,timeout=30).read())
    ready=frozen.read(base/'INPUT_READY.json')
    frozen.require(frozen.sha(base/'WINDOW_INDEX.npz')==ready['window_index_SHA256']==INDEX_SHA,'Pinned temporal window index differs')
    with np.load(base/'WINDOW_INDEX.npz',allow_pickle=False) as z:
        inputs=z['decision_us'].copy()
        frozen.require(len(inputs)==1518 and z['input_identity'].item()==ready['input_identity'],'Exact1518 causal input windows required')
        frozen.require(z['lookback'].item()==64 and z['symbol_order'].tolist()==list(frozen.SYMBOLS),'Exact window/symbol identity required')
    recipe=state/'context-source/conditional_selector_inputs.py'
    archive=state/'native-diagnostics.zip'
    if not archive.exists():
        archive.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/d69e9ac94478c5be54cb46c622afec7aaf3c61f7/research_artifacts/native_20261008/coin_native_history_diagnostics_20261008.zip',timeout=60).read())
    frozen.require(frozen.sha(archive)==DIAGNOSTICS_SHA,'Retained public source archive differs')
    with zipfile.ZipFile(state/'native-diagnostics.zip') as z:
        body=z.read('source/scripts/research/conditional_selector_inputs.py')
    frozen.require(hashlib.sha256(body).hexdigest()==RECIPE_SHA,'Original expert recipe source differs')
    recipe.parent.mkdir(exist_ok=True)
    if not recipe.exists():recipe.write_bytes(body)
    frozen.require(frozen.sha(recipe)==RECIPE_SHA,'Original expert recipe bytes differ')
    original=frozen.load('recovered_original_context_recipe',recipe)
    manifest=frozen.read(HERE/'NATIVE61_PLAN.json')
    for n in ('scripts/investment/public_sma_perpetual.py','scripts/investment/vol_managed_perpetual_target.py','scripts/research/public_cross_section_momentum.py','modules/transformer_v2/portfolio.py'):
        frozen.require(frozen.sha(frozen.REPO/n)==manifest['source_sha256'][n],'Frozen signal/risk source differs: '+n)
    feature=state/'temporal-feature-transfer/original/features/CORE5_PRE_MAY2024.npz'
    frozen.require(frozen.sha(feature)==ready['binding']['feature_npz_SHA256'],'Shared feature/close source identity differs')
    with np.load(feature,allow_pickle=False) as z:
        close=z['close'].copy();available=z['completed_day_available_us'].copy();symbols=tuple(z['symbol_order'].tolist())
    # Call only unchanged original bar/target functions. No teacher labels,
    # feedback utilities, scaler admission or model code is executed.
    bars=original.bar_frame(feature.parents[1]/'source_tables_not_model_inputs',symbols)
    lookup={(r['available_us'],r['symbol']):r['close'] for r in bars.iter_rows(named=True)}
    source_close=np.array([[lookup.get((int(t),s),np.nan) for s in symbols] for t in available])
    frozen.require(np.array_equal(source_close,close,equal_nan=True),'Fresh original price NPZ vs actual source OHLC close differs')
    outcome_path=HERE/'temporal-economics/PRE_MAY_ECONOMIC_OUTCOMES.npz'
    economics=frozen.read(HERE/'temporal-economics/ECONOMIC_READINESS.json')
    frozen.require(frozen.sha(outcome_path)==economics['economic_outcomes']['sha256'],'Fresh audited economic outcome identity differs')
    with np.load(outcome_path,allow_pickle=False) as z:outcomes={k:z[k].copy() for k in z.files}
    econ=outcomes['decision_us']
    tt=np.arange(int(econ[0]),CUTOFF,DAY,dtype=np.int64)
    vol=original.existing_targets(dict(recipe='VOL_MANAGED_HOLD'),bars,tt,close,available,symbols)
    cs=original.existing_targets(dict(recipe='CSMOM21'),bars,tt,close,available,symbols)
    targets=np.stack([np.zeros_like(vol[0]),vol[0],cs[0]],1)
    raw=np.stack([np.zeros_like(vol[1]),vol[1],cs[1]],1)
    eligible=np.stack([np.ones(len(tt),bool),vol[2],cs[2]],1)
    asset_eligible=np.stack([np.ones_like(vol[3]),vol[3],cs[3]],1)
    parity=[]
    def compare(a,label):
        own=a['decision_us'];inside=(own>=tt[0])&(own<tt[-1]+DAY);ix=np.searchsorted(tt,own[inside])
        frozen.require(np.array_equal(tt[ix],own[inside]),'Saved parity calendar differs')
        for slot,prior_slot in ((1,1),(2,4)):
            for k,b in [('expert_targets',targets),('expert_raw_targets',raw),('expert_eligible',eligible),('expert_asset_eligible',asset_eligible)]:
                frozen.require(np.array_equal(b[ix,slot],a[k][inside,prior_slot]),'Original context parity differs: '+label+'/'+k)
        parity.append(dict(source=label,dates=int(inside.sum()),expert_targets_raw_and_eligibility='EXACT',maximum_target_error=0.))
    h1=state/'h1_validation/original/h1_market/inputs/H1_E5_INPUTS.npz'
    frozen.require(frozen.sha(h1)=='9290615ff090e1560d5fe5823e2b721a93f3079c2f060ebff96a07df548e81e9','Original H1 parity source differs')
    with np.load(h1,allow_pickle=False) as z:compare(z,'PUBLIC_H1_ORIGINAL_E5')
    bear=state/'e5-bear-original/coin_e5_bear_recovery_native_increment_20261008_v2.zip'
    frozen.require(frozen.sha(bear)=='98e38bc3f0e6a16fd51a63be880371882d4e2b52df1d8ec5a39963721d2d2bb8','Original older context archive differs')
    with zipfile.ZipFile(bear) as z:
        for n in ('bear_recovery_data/inputs/BEAR2022NOV_INPUTS.npz','bear_recovery_data/inputs/RECOVERY2023JAN_INPUTS.npz'):
            with np.load(io.BytesIO(z.read(n)),allow_pickle=False) as a:compare(a,n)
    past=np.full((len(tt),30,5),np.nan);completed_price=np.full((len(tt),5),np.nan)
    for i,t in enumerate(tt):
        j=int(np.searchsorted(available,t));history=close[j-30:j+1]
        if history.shape==(31,5) and available[j]==t and np.all(np.diff(available[j-30:j+1])==DAY) and np.isfinite(history).all() and (history>0).all():
            past[i]=np.diff(history,axis=0)/history[:-1];completed_price[i]=history[-1]
    intersect=np.isin(tt,econ)&np.isin(tt,inputs)
    context=intersect & np.isfinite(past).all((1,2)) & eligible.all(1)
    ix=np.flatnonzero(context);selected=tt[ix];ei=np.searchsorted(econ,selected)
    frozen.require(np.isfinite(targets[ix]).all() and (abs(targets[ix])<=.3+1e-12).all() and (abs(targets[ix]).sum(2)<=.6+1e-12).all(),'Original target caps/finite contexts differ')
    for i in ix:
        covariance=np.cov(past[i],rowvar=False,ddof=1)*365
        for slot in (1,2):frozen.require(float(targets[i,slot]@covariance@targets[i,slot])<=.1**2+1e-12,'Original10percent covariance cap differs')
    runs=np.split(selected,np.flatnonzero(np.diff(selected)!=DAY)+1);episodes=[];ids=[]
    for k,r in enumerate(runs):
        episodes.append(dict(id=k,first_decision_us=int(r[0]),last_decision_us=int(r[-1]),first_decision_UTC=frozen.datetime.fromtimestamp(int(r[0])/1e6,frozen.UTC).isoformat(),last_decision_UTC=frozen.datetime.fromtimestamp(int(r[-1])/1e6,frozen.UTC).isoformat(),decisions=len(r),first_execution_us=int(r[0])+60_000_001,last_outcome_boundary_us=int(r[-1])+DAY+60_000_001));ids.extend([k]*len(r))
    output.mkdir(exist_ok=True,parents=True);p=output/'PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz'
    np.savez_compressed(p,decision_us=selected,episode_id=np.asarray(ids,np.int64),symbol_order=np.array(symbols),expert_order=np.array(['CASH','VOL_MANAGED_HOLD','CSMOM21']),original_E5_indices=np.array([0,1,4],np.int64),
        expert_targets=targets[ix],expert_raw_targets=raw[ix],expert_eligible=eligible[ix],expert_asset_eligible=asset_eligible[ix],target_available_us=np.broadcast_to(selected[:,None],eligible[ix].shape),
        past_returns30=past[ix],completed_decision_daily_close=completed_price[ix],start_execution_us=outcomes['start_execution_us'][ei],end_execution_us=outcomes['end_execution_us'][ei],start_price=outcomes['start_price'][ei],end_price=outcomes['end_price'][ei],funding_per_unit=outcomes['funding_per_unit'][ei])
    r=dict(schema='PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXT_READY_V1',status='READY_FOR_FROZEN_TRAINING_PLAN_NOT_TRAINED',input_commit=INPUT_COMMIT,input_index_sha256=INDEX_SHA,input_identity=ready['input_identity'],
        feature_npz_sha256=frozen.sha(feature),economic_readiness_sha256=frozen.sha(HERE/'temporal-economics/ECONOMIC_READINESS.json'),economic_payload_sha256=frozen.sha(outcome_path),
        original_recipe_source_sha256=RECIPE_SHA,original_recipe_archive_sha256=DIAGNOSTICS_SHA,original_recipe_public_commit='d69e9ac94478c5be54cb46c622afec7aaf3c61f7',original_recipe_archive_path='research_artifacts/native_20261008/coin_native_history_diagnostics_20261008.zip',original_recipe_member='source/scripts/research/conditional_selector_inputs.py',binder_sha256=frozen.sha(Path(__file__)),recipe_functions_called=['bar_frame','existing_targets; VOL_MANAGED_HOLD and CSMOM21 only'],
        expert_order=['CASH','VOL_MANAGED_HOLD','CSMOM21'],original_E5_indices=[0,1,4],weekly_rank_anchor_us=1704067200000000,original_signal_risk_sha256={n:manifest['source_sha256'][n] for n in ('scripts/investment/public_sma_perpetual.py','scripts/investment/vol_managed_perpetual_target.py','scripts/research/public_cross_section_momentum.py','modules/transformer_v2/portfolio.py')},
        original_saved_context_parity=parity,original_saved_context_parity_dates=sum(v['dates'] for v in parity),price_matrix_numerical_check='EXACT_WITH_NANS_ORIGINAL_NPZ_VS_REAL_OHLC_SOURCE',
        input_windows=1518,economic_dates=839,input_economic_intersection=int(intersect.sum()),finite_real_30_return_context_dates=len(selected),excluded_incomplete_past_covariance_dates=int(intersect.sum()-context.sum()),episodes=episodes,
        context_payload=dict(path=p.name,bytes=p.stat().st_size,sha256=frozen.sha(p)),training_cutoff_us=CUTOFF,
        clock_contract=economics['clock_contract'],missingness='Per-feature/time masks remain separate original input masks; expert per-asset eligibility retained; no ready256 or all64 prices gate introduced',
        adapter_contract='Named3-slot CASH/VOL/CS context; original E5 slot mapping0/1/4 explicit; no other expert is padded or admitted; fresh CASH budget ramp and paid episode terminal closure must be frozen in training plan',
        role='Conditional daily economic proxy dependencies; does not certify native minute execution or historical publication/contract/account rules',
        future_labels=False,scalers_fit=0,models_fit=0,wallets_run=0,provider_downloads=0,pool_expansion=False)
    (output/'TRAIN_CONTEXT_READY.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    bind(a.state,a.output)


if __name__=='__main__':main()
