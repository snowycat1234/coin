import datetime, hashlib, json
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.preprocessing import StandardScaler
from quant.paths import ROOT, STATE
from quant.resources import status

OUT=STATE/'v7-oof-semantic-review-20261002-v1'
OUT.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ash(x):return hashlib.sha256(np.asarray(x).tobytes()).hexdigest()
report_path=ROOT/'reports/fast_research/V7_OOF_FLOW_IMPACT_20261002_V2.json'
r=json.loads(report_path.read_text());run=Path(r['run_dir'])
assert json.loads((run/'COMPLETE.json').read_text())['report_sha256']==sha(report_path)
oracle_path=ROOT/'reports/fast_research/V7_ORACLE_FLOW_HORIZON_20261002_V1.json'
oracle=json.loads(oracle_path.read_text());common=Path(oracle['run_dir'])/'oracle_common_endpoints.parquet'
assert sha(common)==r['binding']['prior_common_endpoints_sha256']
assert sha(oracle_path)==r['binding']['prior_oracle_report_sha256']
frame=pl.read_parquet(common)
d=np.load(run/'decision_us.npy',allow_pickle=False)
x=np.load(run/'past_features210.npy',allow_pickle=False)
assert np.array_equal(d,frame['decision_us'].to_numpy()) and np.all(np.diff(d)>0)
first=1751328000000000;day=86_400_000_000;lag=3_610_000_000;embargo=3_600_000_000
train=np.flatnonzero(d<first+12*day-embargo-lag)
val=np.flatnonzero((d>=first+12*day)&(d+lag<=first+14*day-embargo))
test=np.flatnonzero((d>=first+14*day)&(d+lag<=first+21*day))
for name,a in [('train_indices',train),('validation_indices',val),('test_indices',test)]:
    assert np.array_equal(a,np.load(run/(name+'.npy'),allow_pickle=False))
assert d.min()>=first and d.max()<first+30*day
blocks=[]
for block,(lower_day,upper_day) in enumerate([(3,6),(6,9),(9,12)]):
    lower,upper=first+lower_day*day,first+upper_day*day
    fit=train[d[train]+lag<=lower-embargo]
    forecast=train[(d[train]>=lower)&(d[train]<upper)]
    assert np.max(d[fit]+lag)+embargo<=np.min(d[forecast])
    blocks.append((fit,forecast,lower-embargo))
oof=np.sort(np.concatenate([b[1] for b in blocks]))
assert len(oof)==len(np.unique(oof)) and np.array_equal(oof,np.load(run/'OOF_indices.npy',allow_pickle=False))
sources={}
for name,expected in r['binding']['source_hashes'].items():
    assert sha(ROOT/name)==expected
    sources[name]=expected
    target=OUT/name.replace('/','__');target.write_bytes((ROOT/name).read_bytes())
verifier=ROOT/'scripts/research_v7/verify_oof_flow_impact.py'
(OUT/'verifier-current-snapshot.py').write_bytes(verifier.read_bytes())
def scale_check(values,receipt):
    scaler=StandardScaler().fit(values)
    assert int(scaler.n_samples_seen_)==receipt['n_samples_seen']
    diffs={}
    for name in ['mean','scale','var']:
        actual=getattr(scaler,name+'_');saved=np.asarray(receipt[name])
        assert np.array_equal(actual,saved),name
        diffs[name]=float(np.max(np.abs(actual-saved)))
    return {'rows':len(values),'columns':values.shape[1],'all_official_scaler_parameters_exact':True,'max_absolute_parameter_differences':diffs}
models=[];flow_scalers=[]
streams=('spot_BTCUSDT','spot_ETHUSDT','perp_BTCUSDT','perp_ETHUSDT')
for h in [5,15,30,60]:
    flow=frame.select([f'{s}__flow_{h}m' for s in streams]).to_numpy()
    ret=frame.select([f'spot_{s}__return_{h}m_proxy' for s in ['BTCUSDT','ETHUSDT']]).to_numpy()
    entire=np.load(run/f'horizon-{h}m'/'OOF-predicted-flow.npy',allow_pickle=False)
    fitted=np.load(run/f'horizon-{h}m'/'M2-train-predicted-flow.npy',allow_pickle=False)
    assert np.array_equal(entire[oof],fitted)
    assert np.isnan(entire[np.setdiff1d(np.arange(len(d)),oof)]).all()
    predicted_scale=json.loads((run/f'horizon-{h}m'/'PREDICTED_FLOW_SCALER.json').read_text())
    flow_scalers.append({'horizon_minutes':h,**scale_check(fitted,predicted_scale)})
    paired={}
    for rec in [m for m in r['model_receipts'] if m['horizon_minutes']==h]:
        path=run/rec['path'];saved=json.loads((path/'FIT_RECEIPT.json').read_text())
        fit=np.load(path/'fit_indices.npy',allow_pickle=False)
        forecast=np.load(path/'forecast_indices.npy',allow_pickle=False)
        role=rec['role']
        if role.startswith('M1-OOF-'):
            idx=int(role.rsplit('-',1)[1]);expected_fit,expected_forecast,deadline=blocks[idx]
            assert np.array_equal(fit,expected_fit) and np.array_equal(forecast,expected_forecast)
            assert np.array_equal(entire[forecast],np.load(path/'forecast_original_units.npy',allow_pickle=False))
        else:
            expected_fit=train if role=='M1-final' else oof
            assert np.array_equal(fit,expected_fit) and np.array_equal(forecast,np.r_[val,test])
            deadline=first+12*day-embargo
        assert saved['label_deadline_us']==deadline and np.max(d[fit]+lag)<=deadline
        assert ash(fit)==saved['fit_indices_sha256'] and ash(forecast)==saved['forecast_indices_sha256']
        input_check=scale_check(x[fit],saved['input_scaler'])
        target_check=scale_check((flow if role.startswith('M1') else ret)[fit],saved['target_scaler'])
        models.append({'horizon_minutes':h,'role':role,'fit_rows':len(fit),'forecast_rows':len(forecast),'maturity_plus_embargo_respected':True,'input_scaler':input_check,'target_scaler':target_check})
        if role in ['DIRECT-past-only','M2-OOF-flow-impact']:paired[role]=saved
    for field in ['fit_indices_sha256','forecast_indices_sha256','input_scaler','target_scaler']:
        assert paired['DIRECT-past-only'][field]==paired['M2-OOF-flow-impact'][field]
settlement=[];economic_comparison=[];ambiguous=[]
for horizon in r['horizons']:
    h=horizon['horizon_minutes']
    for key in ['M1_test_flow','M1_OOF_flow']:
        for stream,metric in horizon[key].items():
            ambiguous.append({'horizon_minutes':h,'section':key,'stream':stream,'historical_ambiguous_signed_return_mean_bps':metric['signed_return_mean_bps'],'correct_signed_flow_imbalance_mean':metric['signed_return_mean_bps']/10000,'monetary_return_or_bps':False})
    for branch in horizon['direct_two_stage_comparison']:
        for spread,summary in branch['economics'].items():
            prefix=run/f'horizon-{h}m'/f"{branch['policy']}-{h}m-spread{spread}"
            ledger=pl.read_parquet(prefix.with_name(prefix.name+'-trades.parquet'))
            daily=pl.read_parquet(prefix.with_name(prefix.name+'-daily.parquet'))
            assert len(daily)==7 and daily['valuation_us'][-1]==first+21*day
            assert daily['BTC_quantity'][-1]==0 and daily['ETH_quantity'][-1]==0
            assert daily['cash'][-1]==daily['nav'][-1]==summary['final_nav']
            if len(ledger):assert ledger['event_us'].max()<first+21*day
            assert summary['roundtrip_fee_bps']==20 and summary['roundtrip_extra_slippage_bps']==8 and summary['roundtrip_assumed_spread_bps']==int(spread)
            assert summary['prediction_threshold_bps']==35 and summary['long_term_net_apr_proven'] is False
            settlement.append({'horizon_minutes':h,'policy':branch['policy'],'spread_bps':int(spread),'actual_7d_terminal_cash_and_flat_positions_verified':True})
        s=branch['economics']['2']
        economic_comparison.append({'horizon_minutes':h,'policy':branch['policy'],'net_7d_return':s['net_proxy_return'],'gross_7d_return':s['gross_proxy_return'],'cost_fraction':s['estimated_cost'],'roundtrips':s['closed_roundtrips'],'break_even_roundtrip_cost_bps':s['break_even_roundtrip_cost_bps'],'BTC_return_rank_IC':branch['return_metrics']['test']['BTCUSDT']['spearman'],'ETH_return_rank_IC':branch['return_metrics']['test']['ETHUSDT']['spearman']})
value={'status':'V7_OOF_CAUSALITY_SCALER_AND_SETTLEMENT_READ_ONLY_REVIEW_PASS_WITH_REPORTING_LIMITS','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'reviewed_report_sha256':sha(report_path),'review_script_sha256':sha(Path(__file__)),'source_hashes':sources,'reviewed_current_verifier_snapshot_sha256':sha(OUT/'verifier-current-snapshot.py'),'scope':'Only original registered July development artifacts; no unseen/locked reads, no model refits, no source/evidence modification','counts':{'train':len(train),'validation':len(val),'test':len(test),'OOF_M2_direct':len(oof)},'scaler_parameter_checks':models,'predicted_flow_scaler_checks':flow_scalers,'direct_M2_same_rows_scalers_and_targets':True,'actual_M2_training_input_lineage_is_exact_three_block_OOF_union':True,'actual_terminal_settlement_checks':settlement,'economic_summary':economic_comparison,'reporting_unit_findings':ambiguous,'findings':['No training label/scaler lookahead found under declared 3610s max maturity and 3600s embargo.','Past204 construction slices only bars before decision; six state fields use already-closed contemporaneous/preceding-hour inputs. No exact raw-feature reproduction repeated here.','Future-valid common filtering uses future four-stream quality/price-anchor validity at all four horizons, so every economic replay is conditional and cannot prove executable APR.','M1-final uses more and later data than three expanding OOF generators; predicted-flow distribution/calibration changes are a scientific limitation, not label leakage.','5m flow has modest predictive association, but actual-return predictions do not cross fixed cost threshold; zero trades proves no monetization for this recipe, not no market signal.','15m DIRECT +0.0335% at primary assumed costs uses only 3 roundtrips; one already-viewed regime and cost sensitivity make it insufficient as long-term candidate evidence.','OOF two-stage underperforms matched direct control at 15/30/60m; pause this implementation while preserving flow capability, reopen on unseen matched-row incremental-net-edge/residual evidence.','M1 signed_return_mean_bps fields have flow imbalance units scaled by10000, not return bps; never use these fields as monetary edge/APR.','Initial independent verifier manually normalized float32 with float64 parameters, differing from official sklearn dtype casting. Owner is repairing separately; this review does not claim saved-model numerical reproduction PASS.'],'long_term_net_APR_proven':False,'recommended_next_information_gain':'Predeclare three genuinely unseen OOS blocks with fixed fit/cost/risk/horizon rules; prioritize lower-turnover direct15m versus matched OOF increment while measuring calibration and residual independence, and preserve frontier allocation.','shared_resources':status()}
target=ROOT/'reports/fast_research/V7_OOF_SEMANTIC_READ_ONLY_REVIEW_20261002_V1.json'
with target.open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
print(json.dumps({'status':value['status'],'report':str(target),'sha256':sha(target),'model_refits':0,'model_scalers_checked':len(models)*2,'predicted_flow_scalers_checked':len(flow_scalers),'settlement_ledgers_checked':len(settlement)}),flush=True)
