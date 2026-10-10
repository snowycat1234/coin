"""Build 2021-only economics with pinned original normalizer and expert recipes."""
import argparse
import gc
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import time
import zipfile

DAY=86400000000
MINUTE=60000000
CORE5=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']
FEATURE_SHA='bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'
NPZ_SHA='f164dc8986727e12446f4a807aed72382e8fd665ad7eda9ba14590811ebc680c'
MANIFEST_SHA='99f07ef591581a51babb0b4a8b3079310f24a8bfe0e91b09103c4a68ffa82130'
RECIPE_SHA='9c6658cd7682b6c5470585cbe927c20893e98a3e071cd52e56c5de280e86f207'
CORE_SHA='c0a086ba583dfe4f059b8942988ec2209ac767e4cfe59699f06e804b94890533'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def load_source(name,path,expected):
    assert sha(path)==expected,(name,'source changed')
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve()==Path(path).resolve()
    return module

def main(root,source_root,feature_archive,core_source):
    began=time.monotonic()
    folder=root/'Y2021';protocol=root/'protocol'
    raw=json.loads((folder/'RAW_MANIFEST.json').read_text())
    primary=[r for r in raw['records'] if not r.get('gap_supplement')]
    assert len(primary)==115 and sum(r['size'] for r in primary)==164149016
    assert raw['new_original_download_bytes']<=180*2**20
    assert sha(protocol/'ORIGINAL_SOURCE_MANIFEST.json')==MANIFEST_SHA
    original_manifest=json.loads((protocol/'ORIGINAL_SOURCE_MANIFEST.json').read_text())
    bindings={}
    for name in ('normalize','common','download','storage'):
        relative=f'modules/collector_research/pipeline/{name}.py'
        expected=original_manifest['versioned_sources'][relative]
        assert sha(source_root/relative)==expected
        bindings[relative]=expected
    sys.path.insert(0,str(source_root))
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    from modules.collector_research.pipeline import normalize as original
    assert Path(original.__file__).resolve()==(source_root/'modules/collector_research/pipeline/normalize.py').resolve()
    assert sha(feature_archive)==FEATURE_SHA
    decisions=np.arange(1609459200000000,1640995200000000,DAY,dtype=np.int64)
    assert len(decisions)==365
    active_start=decisions[:-1]+MINUTE+1;active_end=decisions[1:]+MINUTE+1
    prices=[];coeff=[];quotes=[];price_ok=[];fund_ok=[]
    coverage={};receipts=[];artifacts=[];cached_bindings=[]
    destination=folder/'derived';destination.mkdir(exist_ok=True)
    def write(frame,name,role):
        frame=frame.reset_index(drop=True)
        path=destination/name;path.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(pa.Table.from_pandas(frame,preserve_index=False),path,compression='zstd')
        back=pq.read_table(path,use_threads=False).to_pandas(use_threads=False)
        assert frame.equals(back),'Parquet roundtrip changed values or types'
        artifacts.append(dict(path=str(path.relative_to(folder)),bytes=path.stat().st_size,SHA256=sha(path),rows=len(frame),role=role))
    with zipfile.ZipFile(feature_archive) as cached:
        for symbol in CORE5:
            frames={f:[] for f in ('klines','markPriceKlines')}
            gap_ms={f:[] for f in frames};zero_minutes=0
            for r in sorted((r for r in raw['records'] if r['symbol']==symbol),key=lambda r:bool(r.get('gap_supplement'))):
                path=folder/r['relative_raw_path']
                assert path.stat().st_size==r['size'] and sha(path)==r['SHA256']
                with zipfile.ZipFile(path) as z:assert z.testzip() is None
                y,m=map(int,r['month'].split('-'));lo,hi=original.month_limits(y,m)
                d,duplicates=original.validate_price(original.numeric_csv(path),r['family'],lo,hi)
                q=original.canonical(d,r['family'],symbol)
                stamps=q.timestamp_ms.to_numpy(np.int64)
                if r['source_frequency']=='daily':
                    lo=pd.Timestamp(r['source_period'],tz='UTC').value//1000000;hi=lo+86400000
                expected=np.arange(lo,hi,60000,dtype=np.int64)
                missing=np.setdiff1d(expected,stamps)
                if not r.get('gap_supplement'):gap_ms[r['family']].extend(missing.tolist())
                assert np.array_equal(q.available_us.to_numpy(),(stamps+60000)*1000)
                assert np.array_equal(q.quote_volume.to_numpy(),d.quote_volume.to_numpy())
                gap_path=None
                if len(missing):
                    gap_path=f'source_gaps/{symbol}/{r["family"]}/{r["source_period"]}.parquet'
                    write(pd.DataFrame(dict(timestamp_ms=missing)),gap_path,'actual_original_source_missing_minutes_no_imputation')
                receipts.append(dict(symbol=symbol,family=r['family'],source_period=r['source_period'],source_frequency=r['source_frequency'],original_SHA256=r['SHA256'],
                    rows=len(q),expected_rows=len(expected),original_source_missing_minutes=len(missing),missing_ms_artifact=gap_path,
                    missing_source_dates=sorted(set(str(t.date()) for t in pd.to_datetime(missing,unit='ms',utc=True))),identical_duplicates_removed=duplicates,
                    quote_volume_USDT_preserved=True,quote_volume_float64_SHA256=hashlib.sha256(np.asarray(q.quote_volume,dtype='<f8').tobytes()).hexdigest()))
                if r.get('gap_supplement'):
                    assert r['family']=='markPriceKlines' and '2021-01'<=r['month']<='2021-11'
                    monthly=next(a for a in primary if a['symbol']==symbol and a['family']==r['family'] and a['month']==r['month'])
                    left,right=original.month_limits(y,m)
                    d0,_=original.validate_price(original.numeric_csv(folder/monthly['relative_raw_path']),r['family'],left,right)
                    overlap=q[q.timestamp_ms.isin(d0.timestamp_ms)].set_index('timestamp_ms')
                    original_overlap=d0.set_index('timestamp_ms').loc[overlap.index]
                    columns=[c for c in original.PRICE_COLUMNS if c!='timestamp_ms']
                    assert np.array_equal(overlap[columns].to_numpy(),original_overlap[columns].to_numpy()),'Official daily and monthly observations conflict'
                    additions=q[~q.timestamp_ms.isin(d0.timestamp_ms)].copy()
                    gap_ms[r['family']]=np.setdiff1d(np.asarray(gap_ms[r['family']],dtype=np.int64),additions.timestamp_ms.to_numpy(np.int64)).tolist()
                    receipts[-1].update(gap_supplement=True,overlapping_source_rows_equal=len(overlap),actual_missing_source_rows_added=len(additions))
                    q=additions
                    del d0,overlap,original_overlap
                if r['family']=='klines':
                    zero_minutes+=int(q.quote_volume.eq(0).sum())
                    daily=original.aggregate_price(q,'klines').reset_index(names='dt')
                    daily['symbol']=symbol
                    frames['klines'].append(daily)
                    sparse=q[q.timestamp_ms%86400000<=60000].copy()
                    write(sparse,f'execution_minutes/{symbol}/{r["month"]}.parquet','actual_00_00_quote_and_00_01_execution_minutes')
                else:
                    frames['markPriceKlines'].append(q[['available_us','close']].copy())
                del d,q;gc.collect()
            daily=pd.concat(frames['klines'],ignore_index=True).set_index('dt').reindex(pd.to_datetime(decisions,unit='us',utc=True))
            # Actual execution OPEN remains observable even if another source minute is absent.
            p=daily.exec_price.to_numpy(float)
            pok=np.isfinite(p)&(p>0)
            capacity=[]
            for month in range(1,13):
                sparse=pq.read_table(destination/f'execution_minutes/{symbol}/2021-{month:02d}.parquet',use_threads=False).to_pandas()
                sparse=sparse[sparse.timestamp_ms%86400000==0]
                capacity.append(pd.Series(sparse.quote_volume.to_numpy(float),index=sparse.timestamp_ms.to_numpy(np.int64)*1000))
            quote=pd.concat(capacity).reindex(decisions).to_numpy(float)
            quote_ready=np.isfinite(quote)&(quote>=0)
            name=f'source_tables_not_model_inputs/economics/{symbol}_funding_events.parquet'
            body=cached.read(name)
            f=pq.read_table(io.BytesIO(body),use_threads=False).to_pandas(use_threads=False)
            cached_bindings.append(dict(member=name,SHA256=hashlib.sha256(body).hexdigest(),reuse='signed rates/timestamps and December actual event marks'))
            stamp=f.calc_time_ms.to_numpy(np.int64)*1000
            # Include only actual bracketing events, not supervised dates outside 2021.
            left=int(np.searchsorted(stamp,active_start[0],side='right')-1)
            right=int(np.searchsorted(stamp,active_end[-1],side='right'))
            events=f.iloc[left:right+1].copy().reset_index(drop=True)
            assert np.all(np.diff(events.calc_time_ms.to_numpy(np.int64))>0)
            assert np.isfinite(events.last_funding_rate).all()
            marks=pd.concat(frames['markPriceKlines'],ignore_index=True)
            marks,_=original.deduplicate(marks,'available_us')
            marked=original.mark_funding(events,marks)
            event_us=events.calc_time_ms.to_numpy(np.int64)*1000
            required=((event_us-1)//MINUTE)*MINUTE
            december=(event_us>=1638316800000000)&(event_us<1640995200000000)
            actual_cached=np.isfinite(events.past_mark_price)&(events.past_mark_price>0)&np.isfinite(events.past_mark_available_us)
            reused=december&actual_cached
            assert int(reused.sum())==91  # Only through the right bracket Dec31 08:00; Dec31 16:00 is unused.
            assert np.array_equal(events.past_mark_available_us[reused].to_numpy(),required[reused])
            assert not np.isfinite(marked.past_mark_price[reused]).any(),'Unexpected December mark tape acquisition'
            marked.loc[reused,['past_mark_price','past_mark_available_us']]=events.loc[reused,['past_mark_price','past_mark_available_us']]
            # Explicit sparse reuse leaves the first unowned Jan1 midnight mark UNKNOWN.
            valid=np.isfinite(marked.past_mark_price)&(marked.past_mark_price>0)&np.isfinite(marked.past_mark_available_us)
            valid&=(marked.past_mark_available_us==required)
            assert not valid.iloc[0] and event_us[0]<=active_start[0]
            observed_fresh=np.isfinite(marked.past_mark_price)&~reused
            expected_mark=pd.Series(marks.close.to_numpy(float),index=marks.available_us.to_numpy(np.int64)).reindex(required).to_numpy(float)
            assert np.array_equal(marked.past_mark_price[observed_fresh],expected_mark[observed_fresh])
            owned=(event_us>active_start[0])&(event_us<=active_end[-1])
            windows=original.funding_windows(marked,pd.to_datetime(decisions[:-1],unit='us',utc=True))
            fok=windows.funding_interval_complete.to_numpy(bool)
            coefficient=windows.mark_funding_per_unit.to_numpy(float)
            independent_error=0.0
            for i,(start,end) in enumerate(zip(active_start,active_end)):
                selected=(event_us>start)&(event_us<=end)
                before=int(np.searchsorted(event_us,start,side='right')-1)
                after=int(np.searchsorted(event_us,end,side='right'))
                independent_complete=before>=0 and after<len(events) and valid[selected].all()
                if independent_complete:
                    gaps=np.diff(event_us[before:after+1]);h=events.funding_interval_hours.to_numpy(float)[before:after+1]
                    independent_complete=bool(((abs(gaps-h[:-1]*3600000000)<=1000000)|(abs(gaps-h[1:]*3600000000)<=1000000)).all())
                assert fok[i]==independent_complete
                if fok[i]:
                    reference=math.fsum(float(r)*float(m) for r,m in zip(marked.last_funding_rate.to_numpy(float)[selected],marked.past_mark_price.to_numpy(float)[selected]))
                    error=abs(coefficient[i]-reference);independent_error=max(error,independent_error)
                    assert math.isclose(coefficient[i],reference,rel_tol=2e-15,abs_tol=1e-10)
            daily['open_us']=decisions;daily['close_us']=decisions+DAY;daily['available_us']=decisions+DAY
            daily['execution_us']=decisions+MINUTE+1;daily['execution_price_observed']=pok
            daily['execution_previous_minute_quote_USDT']=quote
            daily['execution_previous_minute_quote_ready']=quote_ready
            daily=daily.rename(columns={'complete':'complete_kline'}).reset_index(names='dt')
            write(daily,f'economics/{symbol}_daily.parquet','actual_execution_economics_not_model_feature_primitives')
            write(marked,f'economics/{symbol}_funding_events.parquet','original_actual_rates_and_owned_prior_marks_with_bracket_event')
            windows=windows.reset_index(names='dt');windows.insert(0,'symbol',symbol)
            windows['interval_start_us']=active_start;windows['interval_end_us']=active_end
            write(windows,f'economics/{symbol}_funding_intervals.parquet','364_unpadded_actual_held_funding_intervals')
            prices.append(p);price_ok.append(pok&quote_ready);quotes.append(quote);coeff.append(coefficient);fund_ok.append(fok)
            for family,missing in gap_ms.items():
                if missing:write(pd.DataFrame(dict(timestamp_ms=np.asarray(missing,np.int64))),f'remaining_gaps/{symbol}/{family}.parquet','actual_remaining_gaps_after_official_daily_sources')
            coverage[symbol]=dict(trade_minute_rows=525600-len(gap_ms['klines']),missing_trade_minutes=len(gap_ms['klines']),
                Jan_Nov_mark_minute_rows=480960-len(gap_ms['markPriceKlines']),missing_Jan_Nov_mark_minutes=len(gap_ms['markPriceKlines']),
                remaining_mark_gap_dates=sorted(set(str(t.date()) for t in pd.to_datetime(gap_ms['markPriceKlines'],unit='ms',utc=True))),
                December_mark_minute_grid_NOT_REACQUIRED=True,actual_cached_December_event_marks_reused=int(reused.sum()),
                observed_execution_prices=int(pok.sum()),execution_quote_capacity_ready=int(quote_ready.sum()),
                complete_held_funding_intervals=int(fok.sum()),owned_funding_events=int(owned.sum()),
                owned_funding_events_with_valid_actual_prior_marks=int(valid[owned].sum()),
                unowned_boundary_events_without_prior_mark=int((~valid&~owned).sum()),
                min_owned_mark_age_us=int((event_us-marked.past_mark_available_us)[owned].min()),
                max_owned_mark_age_us=int((event_us-marked.past_mark_available_us)[owned].max()),
                maximum_independent_coefficient_error=independent_error,actual_zero_quote_volume_minutes=zero_minutes,
                full_trade_daily_bars=int(daily.complete_kline.sum()))
            print(json.dumps(dict(symbol=symbol,**coverage[symbol])),flush=True)
            del frames,daily,marks,events,marked,windows;gc.collect()

        # Replay only original public expert target functions. No teacher, PnL, fit or wallet calls.
        daily_root=folder/'cached_sources/daily_features';daily_root.mkdir(parents=True,exist_ok=True)
        primitive_closes={}
        for symbol in CORE5:
            name=f'source_tables_not_model_inputs/daily_features/{symbol}.parquet';body=cached.read(name)
            (daily_root/(symbol+'.parquet')).write_bytes(body)
            cached_bindings.append(dict(member=name,SHA256=hashlib.sha256(body).hexdigest(),reuse='unchanged original daily feature primitives'))
            primitive=pq.read_table(io.BytesIO(body),use_threads=False).to_pandas().set_index('dt')
            primitive_closes[symbol]=primitive.close.where(primitive.complete_kline & np.isfinite(primitive.close)&(primitive.close>0))
        feature_body=cached.read('features/CORE5_PRE_MAY2024.npz')
        assert hashlib.sha256(feature_body).hexdigest()==NPZ_SHA
        with np.load(io.BytesIO(feature_body),allow_pickle=False) as a:
            assert a['symbol_order'].tolist()==CORE5
            completed=a['completed_day_available_us'];positions=np.searchsorted(completed,decisions)
            assert np.array_equal(completed[positions],decisions) and (positions>=63).all()
            observed=a['feature_observed_mask'];close_mask=a['close_observed_mask']
            # Preserve serialized original masks; missing premium is not an economic exclusion.
            masks=observed[positions];steps=close_mask[positions]
            assert np.array_equal(observed,np.isfinite(a['x'])&close_mask[...,None])
            feature_windows_ready=np.asarray([observed[i].any() and close_mask[i].any() for i in positions])
            np.savez_compressed(destination/'FEATURE_WINDOW_REFERENCES.npz',decision_us=decisions,end_row=positions,
                window_start_row=positions-63,feature_observed_mask=masks,close_observed_mask=steps,
                aggregate_context_asset_order=a['aggregate_context_asset_order'],symbol_order=a['symbol_order'],feature_order=a['feature_order'])
        expert_sources={
            'scripts/investment/public_sma_perpetual.py':'c9fe8a916f300e91396dba70948ab44348b947ec333d7c82b8429db36e064e18',
            'scripts/investment/vol_managed_perpetual_target.py':'6d6c563885accfe47258580a658a43054e94307bbec85b6dc0c06f96b88b9307',
            'scripts/research/public_cross_section_momentum.py':'7d6f1794c0ade6e2c2d951a325e4e68ca45be0e87c84c68f05061442fad8a38f',
            'modules/transformer_v2/portfolio.py':'e4e02b0204e2861bb44eb78c8069b13a09edf6ca9390f3c86490d6e6f8a5e68b'}
        for path,expected in expert_sources.items():assert sha(source_root/path)==expected,'Original expert dependency changed: '+path
        load_source('scripts.research.conditional_selector_core',core_source,CORE_SHA)
        recipe=load_source('_original2021_expert_recipe',protocol/'conditional_selector_inputs.py',RECIPE_SHA)
        bars=recipe.bar_frame(daily_root.parent,CORE5)
        closeframe=pd.DataFrame(primitive_closes)
        original_fixed5_ready=(closeframe.pct_change(fill_method=None).notna().rolling(30,min_periods=30).sum().eq(30).all(axis=1))
        first_fixed5_ready=str((closeframe.index[original_fixed5_ready][0]+pd.Timedelta(days=1)).date())
        assert first_fixed5_ready=='2020-10-15'
        available=closeframe.index.asi8//1000+DAY
        close=closeframe.to_numpy(float)
        generated=[recipe.existing_targets(dict(recipe='CASH',mechanism='CASH'),bars,decisions,close,available,CORE5),
            recipe.existing_targets(dict(recipe='VOL_MANAGED_HOLD'),bars,decisions,close,available,CORE5),
            recipe.existing_targets(dict(recipe='CSMOM21'),bars,decisions,close,available,CORE5)]
        targets=np.stack([v[0] for v in generated],axis=1);raw_targets=np.stack([v[1] for v in generated],axis=1)
        expert_eligible=np.stack([v[2] for v in generated],axis=1);asset_eligible=np.stack([v[3] for v in generated],axis=1)
        cov_ready=[];past_returns=[]
        for decision in decisions:
            index=int(np.searchsorted(available,decision,side='right')-1)
            history=close[index-30:index+1]
            returns=np.diff(history,axis=0)/history[:-1]
            ok=available[index]==decision and np.all(np.diff(available[index-30:index+1])==DAY) and history.shape==(31,5) and np.isfinite(returns).all() and (history>0).all()
            cov_ready.append(ok);past_returns.append(returns)
        cov_ready=np.asarray(cov_ready,bool)
        # Dates below are assertions of independently invoked original gates, not invented masks.
        gates={}
        for j,symbol in enumerate(CORE5):
            actual=str(pd.to_datetime(decisions[np.flatnonzero(asset_eligible[:,1,j])[0]],unit='us',utc=True).date())
            gates[symbol]=dict(first_VOL_eligible_in_2021=actual,CS_ready_2021_dates=int(asset_eligible[:,2,j].sum()))
        assert gates['DOGEUSDT']['first_VOL_eligible_in_2021']=='2021-01-26'
        assert gates['SOLUSDT']['first_VOL_eligible_in_2021']=='2021-04-02'
        np.savez_compressed(destination/'CONTEXT_INPUTS.npz',decision_us=decisions,symbol_order=np.asarray(CORE5),
            original_E5_slots=np.array([0,1,4]),expert_names=np.asarray(['CASH','VOL_MANAGED_HOLD','CSMOM21']),
            expert_targets=targets,raw_targets=raw_targets,expert_eligible=expert_eligible,asset_eligible=asset_eligible,
            target_available_us=np.broadcast_to(decisions[:,None],expert_eligible.shape),fixed5_covariance_ready=cov_ready,
            past_returns=np.asarray(past_returns),feature_window_ready=feature_windows_ready)
    price_matrix=np.column_stack(prices);coefficient_matrix=np.column_stack(coeff)
    price_ready=np.column_stack(price_ok);fund_ready=np.column_stack(fund_ok)
    decision_ready=price_ready.all(1)&cov_ready&feature_windows_ready&expert_eligible.all(1)
    interval_ready=decision_ready[:-1]&decision_ready[1:]&fund_ready.all(1)&np.isfinite(coefficient_matrix).all(1)
    # A failed economic edge splits episodes and cannot be crossed, even with valid endpoints.
    episodes=[];start=None
    for i in range(364):
        if interval_ready[i] and start is None:start=i
        if start is not None and (not interval_ready[i] or i==363):
            end=i if not interval_ready[i] else i+1
            episodes.append(dict(episode=len(episodes),first_decision_index=start,last_paid_CASH_decision_index=end,
                first_UTC=str(pd.to_datetime(decisions[start],unit='us',utc=True).date()),
                paid_close_UTC=str(pd.to_datetime(decisions[end]+MINUTE+1,unit='us',utc=True)),
                actual_decisions=end-start+1,actual_active_intervals=end-start,fresh_CASH_start=True,charged_terminal_CASH_required=True))
            start=None
    exclusions=[]
    for i in range(365):
        reasons=[]
        if not price_ready[i].all():reasons.append('ACTUAL_EXECUTION_OR_PREVIOUS_QUOTE_MISSING')
        if not cov_ready[i]:reasons.append('ORIGINAL_FIXED5_30_RETURN_CONTEXT_MISSING')
        if not feature_windows_ready[i]:reasons.append('ORIGINAL_CAUSAL_FEATURE_WINDOW_MISSING')
        if not expert_eligible[i].all():reasons.append('ORIGINAL_EXPERT_NOT_AVAILABLE')
        if reasons:exclusions.append(dict(decision_index=i,UTC=str(pd.to_datetime(decisions[i],unit='us',utc=True).date()),reasons=reasons))
    for i in range(364):
        if not interval_ready[i]:exclusions.append(dict(interval_index=i,start_UTC=str(pd.to_datetime(decisions[i],unit='us',utc=True).date()),reason='INCOMPLETE_ENDPOINT_OR_ACTUAL_FUNDING_INTERVAL'))
    np.savez_compressed(folder/'ECONOMICS.npz',symbol_order=np.asarray(CORE5),decision_us=decisions,execution_us=decisions+MINUTE+1,
        prices=price_matrix,execution_previous_minute_quote_USDT=np.column_stack(quotes),execution_ready=price_ready,
        funding_interval_start_us=active_start,funding_interval_end_us=active_end,funding_coeff=coefficient_matrix,
        funding_interval_ready=fund_ready,decision_ready=decision_ready,active_interval_ready=interval_ready,
        interval_label_available_us=decisions[1:]+120000001)
    for path,role in [(folder/'ECONOMICS.npz','365_actual_prices_364_held_coefficients_no_padding'),
        (destination/'CONTEXT_INPUTS.npz','original_targets_masks_and_fixed5_past_returns_only'),
        (destination/'FEATURE_WINDOW_REFERENCES.npz','immutable_original_feature_window_references_no_fit')]:
        artifacts.append(dict(path=str(path.relative_to(folder)),bytes=path.stat().st_size,SHA256=sha(path),role=role))
    dump(folder/'EPISODES.json',dict(schema='ACTUAL2021_PAID_EPISODES_V1',episodes=episodes,exclusions=exclusions,
        distinct_eligible_active_intervals=int(interval_ready.sum()),terminal_CASH_decisions=len(episodes),
        no_stitching=True,no_N_plus_one_padding=True,no_2022_held_outcome=True))
    result=dict(schema='CORE5_FIXED2021_ACTUAL_ECONOMIC_PACKET_V1',status='VERIFIED2021_ECONOMIC_INPUTS_WITH_EXPLICIT_EPISODES',
        candidate_decisions=365,admitted_decisions=int(decision_ready.sum()),distinct_eligible_active_intervals=int(interval_ready.sum()),
        paid_episode_count=len(episodes),episodes=episodes,exclusions=exclusions,coverage=coverage,
        original_archive_count=raw['archive_count'],new_official_archive_body_bytes=raw['new_original_download_bytes'],new_official_archive_body_MiB=raw['new_original_download_bytes']/2**20,
        provider_archive_body_cap_bytes=180*2**20,trade_grid_missing_minutes=sum(r['missing_trade_minutes'] for r in coverage.values()),
        Jan_Nov_mark_grid_missing_minutes=sum(r['missing_Jan_Nov_mark_minutes'] for r in coverage.values()),
        December_native_mark_tape_NOT_REACQUIRED=True,execution_and_owned_held_funding_ready=bool(interval_ready.all()),
        original_dynamic_mask_gates=gates,fixed5_covariance_ready_dates=int(cov_ready.sum()),
        original_first_fixed5_covariance_ready_decision=first_fixed5_ready,
        original_E5_slot_mapping=dict(CASH=0,VOL_MANAGED_HOLD=1,CSMOM21=4),
        unchanged_normalizer_commit='b8299bc22321b9dadf707f14da83ac40a39b5491',unchanged_normalizer_source_SHA256=bindings,
        original_expert_recipe_archive_commit='d69e9ac94478c5be54cb46c622afec7aaf3c61f7',original_expert_recipe_member_SHA256=RECIPE_SHA,
        expert_dependency_SHA256={p:sha(source_root/p) for p in ['scripts/investment/public_sma_perpetual.py','scripts/investment/vol_managed_perpetual_target.py','scripts/research/public_cross_section_momentum.py','modules/transformer_v2/portfolio.py']},
        cached_feature_archive_SHA256=FEATURE_SHA,feature_NPZ_SHA256=NPZ_SHA,cached_source_bindings=cached_bindings,
        source_receipts=receipts,derived_artifacts=artifacts,protocol_SHA256=sha(protocol/'PROTOCOL.json'),
        original_daily_primitives_or_feature_values_rebuilt=False,original_feature_masks_preserved=True,
        source_units_and_historical_publication_time='Frozen conditional source-unit and cross-venue proxy contract retained; actual original publication times not certified.',
        terminal='Last admitted decision of each contiguous episode is paid CASH; prices N, held funding N-1; no invented padding.',
        no_date_selection_by_returns=True,no_synthetic_observations=True,no_new2020_decisions_or_archive_bodies=True,
        model_fits=0,model_inferences=0,backtests=0,wallets=0,elapsed_seconds=time.monotonic()-began)
    dump(folder/'VALIDATION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('coverage','source_receipts','derived_artifacts','cached_source_bindings')}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--feature-archive',type=Path,required=True);p.add_argument('--core-source',type=Path,required=True)
    a=p.parse_args();main(a.root,a.source_root,a.feature_archive,a.core_source)
