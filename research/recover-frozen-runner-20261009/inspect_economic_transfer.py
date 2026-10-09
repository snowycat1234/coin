"""Verify published transfer bytes and whitelist economic outcomes; never fit."""
import argparse
from datetime import datetime, UTC
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
COMMIT='d901f130993b6f00ad6479dcc6a04b77627192b8'
PUBLIC_PATH='research/temporal-feature-data-20261009'
ARCHIVE_SHA='bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY=86_400_000_000
MINUTE=60_000_000
OFFSET=60_000_001
CUTOFF=1714521600000000
NORMALIZER_SHA='ee394086066c96bc23e83b45bf0bc2777264ab4eb57128886394fee47fecd4ff'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def require(ok,msg):
    if not ok:raise ValueError(msg)
def iso(t):return datetime.fromtimestamp(int(t)/1e6,UTC).isoformat()


def recover(state):
    """Read existing verified bytes first; fetch missing pinned GitHub parts once."""
    root=state/'temporal-feature-transfer';root.mkdir(exist_ok=True)
    base=f'https://raw.githubusercontent.com/snowycat1234/coin/{COMMIT}/{PUBLIC_PATH}/'
    index=root/'INDEX.json'
    if not index.exists():index.write_bytes(urllib.request.urlopen(base+'INDEX.json',timeout=60).read())
    m=read(index);bodies=[]
    require(m['bytes']==2246454 and m['SHA256']==ARCHIVE_SHA and m['members']==26,'Pinned transfer index differs')
    for i,r in enumerate(m['parts']):
        require(i==r['index'] and len(PurePosixPath(r['file']).parts)==1,'Ordered relative part required')
        p=root/r['file']
        if not p.exists():p.write_bytes(urllib.request.urlopen(base+r['file'],timeout=60).read())
        require(p.stat().st_size==r['bytes'] and sha(p)==r['SHA256'],'Pinned public part differs')
        bodies.append(p.read_bytes())
    body=b''.join(bodies);require(len(body)==2246454 and hashlib.sha256(body).hexdigest()==ARCHIVE_SHA,'Whole transfer differs')
    archive=root/m['archive_file']
    if not archive.exists():archive.write_bytes(body)
    require(sha(archive)==ARCHIVE_SHA,'Retained original archive differs')
    out=root/'original';out.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None and len(z.namelist())==26,'Transfer CRC/member count differs')
        for n in z.namelist():
            p=PurePosixPath(n);require(not p.is_absolute() and '..' not in p.parts,'Relative safe archive member required')
            dest=out.joinpath(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():dest.write_bytes(z.read(n))
            require(dest.read_bytes()==z.read(n),'Preserved original member differs')
    members=read(out/'MEMBERS.json')['files']
    require(len(members)==25,'All members except self-manifest required')
    for n,r in members.items():require((out/n).stat().st_size==r['bytes'] and sha(out/n)==r['SHA256'],'Member hash differs: '+n)
    return out,m


def inspect(state,output):
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    import polars as pl
    out,index=recover(state)
    sys.path.insert(0,str(REPO))
    require(sha(REPO/'modules/collector_research/pipeline/normalize.py')==NORMALIZER_SHA,'Original normalization source differs')
    from modules.collector_research.pipeline.normalize import funding_windows
    with np.load(out/'features/CORE5_PRE_MAY2024.npz',allow_pickle=False) as z:
        require(set(z.files)=={'raw_observation_us','completed_day_available_us','x','feature_observed_mask','close','close_observed_mask','original_price_ready256','symbol_order','feature_order','aggregate_context_asset_order'},'Feature-only transfer schema required')
        observations=z['raw_observation_us'].copy();decisions=z['completed_day_available_us'].copy()
        require(z['symbol_order'].tolist()==list(SYMBOLS),'Ordered CORE5 required')
        require(np.array_equal(decisions,observations+DAY) and np.all(np.diff(decisions)==DAY) and np.all(decisions<CUTOFF),'Exact causal pre-May clock required')
        aggregate_order=z['aggregate_context_asset_order'].tolist()
    manifest=read(out/'FEATURE_MANIFEST.json')
    require(manifest['aggregates']['asset_order']==aggregate_order and not manifest['aggregates']['recomputed_as_CORE5_only'],'Original ten-asset aggregate identity required')
    tables=out/'source_tables_not_model_inputs/economics'
    frames, reports = {}, []
    fields=['dt','symbol','complete_kline','open','high','low','close','quote_volume','rows','unique_minutes','first_ms','last_ms','exec_price','available_us','funding','funding_events','funding_hours','funding_rate_sum_interval','mark_funding_per_unit','complete_funding','funding_interval_complete']
    h1=state/'h1_validation/original/h1_market'
    require(sha(h1/'reports/DATASET_MANIFEST.json')=='8facb75645001306c8179284a057c70ed6c01fc7439b84ffc6f3cb532042cebd','Pinned retained H1 market manifest differs')
    identity=read(h1/'reports/DATASET_MANIFEST.json')
    registered={r['relative_path']:r for r in identity['artifacts']}
    candidate_price=[];candidate_end=[];candidate_funding=[];candidate_valid=[];candidate_reasons=[]
    for s in SYMBOLS:
        d=pq.read_table(tables/(s+'_daily.parquet'),columns=fields).to_pandas()
        e=pq.read_table(tables/(s+'_funding_events.parquet')).to_pandas()
        dates=pd.DatetimeIndex(d.dt);times=dates.as_unit('us').asi8
        require(np.all(np.diff(times)==DAY) and not dates.has_duplicates and (d.symbol==s).all(),'Complete economic calendar and symbol required')
        require(np.array_equal(d.available_us.to_numpy(np.int64),times+DAY),'Original completed-day economic clock differs')
        event=e.calc_time_ms.to_numpy(np.int64)*1000;rates=e.last_funding_rate.to_numpy(float);hours=e.funding_interval_hours.to_numpy(float)
        require(np.all(np.diff(event)>0) and np.isfinite(rates).all() and np.isfinite(hours).all() and (hours>0).all() and (hours<=24).all(),'Actual unique signed funding event clocks/rates required')
        marks=e.past_mark_price.to_numpy(float);mark_times=e.past_mark_available_us.to_numpy(float);held_mark=np.isfinite(marks)
        require(np.array_equal(held_mark,np.isfinite(mark_times)) and (marks[held_mark]>0).all(),'Missing past-mark values and clocks must remain paired')
        require(np.all(mark_times[held_mark]==np.floor((event[held_mark]-1)/MINUTE)*MINUTE),'Latest strictly prior completed mark grid required')
        require(np.all((event[held_mark]-mark_times[held_mark]>0)&(event[held_mark]-mark_times[held_mark]<=MINUTE)),'Original strictly past one-minute mark guard differs')
        recomputed=funding_windows(e,dates)
        for k in recomputed:
            a=d[k].to_numpy();b=recomputed[k].to_numpy()
            require(np.all((a==b)|(pd.isna(a)&pd.isna(b))),'Fresh funding numerical/chronology mismatch: '+s+'/'+k)
        full=d.complete_kline.fillna(False).to_numpy(bool)
        metadata=(d['rows'].to_numpy()==1440)&(d.unique_minutes.to_numpy()==1440)&(d.first_ms.to_numpy()==times/1000)&(d.last_ms.to_numpy()==times/1000+1439*60000)
        # Later H1 rows were copied from official daily sources, so their
        # minute-count fields are absent. Bind them to retained actual H1
        # minute Parquets instead of inventing a count.
        need_actual=np.flatnonzero(full & ~metadata & (times+OFFSET<CUTOFF))
        checked=0
        for month in sorted({dates[i].strftime('%Y-%m') for i in need_actual}):
            name=f'data/normalized/minute/{s}/klines/{month}.parquet';r=registered[name];p=h1/name
            require(p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],'Retained H1 actual minute identity differs')
            minute=pl.read_parquet(p).select('open_us','open','high','low','close').to_pandas()
            for i in need_actual:
                if dates[i].strftime('%Y-%m')!=month:continue
                rows=minute[(minute.open_us>=times[i])&(minute.open_us<times[i]+DAY)].sort_values('open_us')
                require(np.array_equal(rows.open_us.to_numpy(),np.arange(times[i],times[i]+DAY,MINUTE)),'Actual1440 H1 trade grid required')
                actual=[rows.open.iloc[0],rows.high.max(),rows.low.min(),rows.close.iloc[-1]]
                require(np.array_equal(actual,d.loc[i,['open','high','low','close']].to_numpy(float)),'Original economic vs actual H1 OHLC differs')
                require(rows.open.iloc[1]==d.exec_price.iloc[i],'Actual00:01 execution open differs')
                metadata[i]=True;checked+=1
        # Only pre-cutoff outcomes enter readiness. Later table rows remain
        # evidence, never model inputs or fitting candidates.
        relevant=times+OFFSET<CUTOFF
        require(np.all(~full[relevant]|metadata[relevant]),'Pre-May completed trade day lacks actual metadata or retained minute proof')
        prices=d[['open','high','low','close']].to_numpy(float)
        require(np.isfinite(prices[full&relevant]).all() and (prices[full&relevant]>0).all(),'Completed actual OHLC must be positive finite')
        require(np.all(prices[full&relevant,1]>=prices[full&relevant].max(1)) and np.all(prices[full&relevant,2]<=prices[full&relevant].min(1)),'Actual OHLC range differs')
        require(np.all(d.quote_volume.to_numpy(float)[full&relevant]>=0),'Nonnegative quote-USDT volume required')
        good,p0,p1,fp,reasons=[],[],[],[],[]
        for obs,t in zip(observations,decisions,strict=True):
            i=int(np.searchsorted(times,obs));why=[]
            a,b,f=np.nan,np.nan,np.nan
            if i>=len(times) or times[i]!=obs or i+2>=len(times):why.append('NO_ORIGINAL_ECONOMIC_OBSERVATION_ROW')
            else:
                a,b,f=d.exec_price.iloc[i+1],d.exec_price.iloc[i+2],d.mark_funding_per_unit.iloc[i+1]
                if not np.isfinite(a) or a<=0:why.append('MISSING_ACTUAL_00_01_START_OPEN')
                if not np.isfinite(b) or b<=0:why.append('MISSING_ACTUAL_00_01_EXIT_OPEN')
                if not full[i+1]:why.append('INCOMPLETE_1440_TRADE_EXECUTION_DAY')
                if not bool(d.funding_interval_complete.iloc[i+1]) or not np.isfinite(f):why.append('INCOMPLETE_FUNDING_CHRONOLOGY_OR_PRIOR_MARK')
            if t+DAY+OFFSET>=CUTOFF:why.append('OUTCOME_NOT_STRICTLY_MATURE_BEFORE_MAY1')
            good.append(not why);p0.append(a);p1.append(b);fp.append(f);reasons.append(why)
        candidate_valid.append(good);candidate_price.append(p0);candidate_end.append(p1);candidate_funding.append(fp);candidate_reasons.append(reasons)
        reports.append(dict(symbol=s,economic_rows=len(d),funding_event_rows=len(e),funding_fields_recomputed=len(recomputed.columns),funding_daily_rows_recomputed=len(recomputed),funding_exact_mismatches=0,
            strict_past_mark_events=int(held_mark.sum()),missing_past_mark_events_retained=int((~held_mark).sum()),
            actual_H1_trade_days_rechecked=checked,eligible_mature_one_day_outcomes=int(np.sum(good))))
        frames[s]=d
    valid=np.asarray(candidate_valid,bool).T
    common=valid.all(1);selected=np.flatnonzero(common);episode_ids=[];episodes=[]
    for i in selected:
        if not episodes or int(decisions[i])!=episodes[-1]['last_decision_us']+DAY:
            episodes.append(dict(id=len(episodes),first_decision_us=int(decisions[i]),last_decision_us=int(decisions[i]),decisions=1))
        else:
            episodes[-1]['last_decision_us']=int(decisions[i]);episodes[-1]['decisions']+=1
        episode_ids.append(episodes[-1]['id'])
    for r in episodes:
        r.update(first_decision_UTC=iso(r['first_decision_us']),last_decision_UTC=iso(r['last_decision_us']),
            first_execution_us=r['first_decision_us']+OFFSET,last_outcome_boundary_us=r['last_decision_us']+DAY+OFFSET)
    output.mkdir(parents=True,exist_ok=True)
    npz=output/'PRE_MAY_ECONOMIC_OUTCOMES.npz'
    np.savez_compressed(npz,decision_us=decisions[selected],raw_observation_us=observations[selected],episode_id=np.asarray(episode_ids,np.int64),
        start_execution_us=decisions[selected]+OFFSET,end_execution_us=decisions[selected]+DAY+OFFSET,
        start_price=np.asarray(candidate_price,float).T[selected],end_price=np.asarray(candidate_end,float).T[selected],
        funding_per_unit=np.asarray(candidate_funding,float).T[selected],symbol_order=np.array(SYMBOLS),mature_before_us=np.array(CUTOFF,np.int64))
    report=dict(schema='FRESH_PARQUET_ECONOMIC_READINESS_V1',status='PASS_CONDITIONAL_DAILY_PROXY_ECONOMICS_NOT_NATIVE_ACCOUNT_CERTIFICATION',
        public_transfer=dict(commit=COMMIT,index=PUBLIC_PATH+'/INDEX.json',bytes=index['bytes'],sha256=ARCHIVE_SHA,members=26,verified_member_hashes=25,CRC='PASS'),
        feature_npz_sha256=sha(out/'features/CORE5_PRE_MAY2024.npz'),source_normalizer_sha256=NORMALIZER_SHA,
        training_cutoff_us=CUTOFF,input_decision_rows=len(decisions),common_mature_economic_decisions=len(selected),episodes=episodes,asset_checks=reports,
        economic_outcomes=dict(path=npz.name,bytes=npz.stat().st_size,sha256=sha(npz),role='SEPARATE_OUTCOMES_NEVER_FEATURES_OR_FEATURE_MASKS'),
        clock_contract=dict(observation='UTC daily bar start',decision_available='observation+1day historical completed-bar proxy',
            start_execution='decision00:01:00.000001',end_execution='following day00:01:00.000001',
            funding_ownership='actual event_us > start_execution AND event_us <= end_execution',
            funding_boundary_priority='settlement before rebalance fills; fresh first funding has no prior held position',
            funding_rate_scale=1,funding_per_unit='sum actual signed rate * strictly prior completed mark',
            chronology_guard='actual raw millisecond timestamps retained; adjacent interval clock tolerates <=1second jitter exactly as original normalizer',
            maturity='end execution strictly before May1; complete funding also requires event brackets on both sides'),
        aggregate_semantics='PRESERVE_ORIGINAL_10_ASSET_CONTEXT_NO_RECOMPUTATION',feature_windows='OWNED_BY_SEPARATE_TEMPORAL_WORKER_NOT_BUILT_HERE',
        episode_contract='Economic-only candidate intervals; independent gap-separated intervals; do not bridge gaps or stitch fresh wallets; intersect these dates with independent causal input and past covariance readiness before freezing fitting plan',
        originals_overwritten=False,provider_downloads=0,raw_official_ZIPs_in_new_transfer=False,fresh_raw_official_ZIP_SHA_CRC_audit=False,
        retained_raw_receipts_role='HISTORICAL_PRODUCER_CLAIMS; new outer transport CRC and numerical Parquet audit are distinct',
        funding_publication_contract_account_rules_certified=False,native_minute_wallets_certified_for_these_training_episodes=False,models_fit=0)
    (output/'ECONOMIC_READINESS.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    inspect(a.state,a.output)


if __name__=='__main__':main()
