"""Independent raw-CSV point checks; does not reuse the normalizer or target code."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile
import numpy as np
import pyarrow.parquet as pq

def rows(path):
    with zipfile.ZipFile(path) as z:
        with z.open(z.namelist()[0]) as f:
            for row in csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig')):
                if row[0] in ('open_time','open_timestamp'):continue
                yield row

def main(root,feature):
    folder=root/'Y2021';raw=json.loads((folder/'RAW_MANIFEST.json').read_text())
    validation=json.loads((folder/'VALIDATION.json').read_text())
    original_missing=sum(r['original_source_missing_minutes'] for r in validation['source_receipts'] if r['source_frequency']=='monthly')
    added=sum(r.get('actual_missing_source_rows_added',0) for r in validation['source_receipts'])
    counts={};errors={}
    with np.load(folder/'ECONOMICS.npz',allow_pickle=False) as e,zipfile.ZipFile(feature) as cached:
        assert e['prices'].shape==(365,5) and e['funding_coeff'].shape==(364,5)
        assert np.array_equal(e['execution_us'],e['decision_us']+60000001)
        for j,symbol in enumerate(e['symbol_order']):
            trade_open={};quote={}
            records=[r for r in raw['records'] if r['symbol']==symbol]
            for r in records:
                if r['family']!='klines':continue
                for row in rows(folder/r['relative_raw_path']):
                    t=int(row[0]);offset=t%86400000
                    if offset==60000:trade_open[t*1000]=float(row[1])
                    elif offset==0:quote[t*1000]=float(row[7])
            p=np.asarray([trade_open.get(int(t)+60000000,np.nan) for t in e['decision_us']])
            q=np.asarray([quote.get(int(t),np.nan) for t in e['decision_us']])
            assert np.array_equal(p,e['prices'][:,j],equal_nan=True)
            assert np.array_equal(q,e['execution_previous_minute_quote_USDT'][:,j],equal_nan=True)
            f=pq.read_table(folder/f'derived/economics/{symbol}_funding_events.parquet',use_threads=False).to_pandas(use_threads=False)
            original=pq.read_table(io.BytesIO(cached.read(f'source_tables_not_model_inputs/economics/{symbol}_funding_events.parquet')),use_threads=False).to_pandas(use_threads=False)
            original=original.set_index('calc_time_ms').loc[f.calc_time_ms].reset_index()
            for key in ['calc_time_ms','funding_interval_hours','last_funding_rate']:
                assert np.array_equal(original[key],f[key]),'Changed original signed rate, nominal hours or event timestamp'
            t=f.calc_time_ms.to_numpy(np.int64)*1000
            owned=(t>e['execution_us'][0])&(t<=e['execution_us'][-1])
            required_open=((t[owned]-1)//60000000)*60000000-60000000
            needed=set(int(v//1000) for v in required_open if 1609459200000000<=v<1638316800000000)
            actual_marks={}
            for r in records:
                if r['family']!='markPriceKlines':continue
                for row in rows(folder/r['relative_raw_path']):
                    stamp=int(row[0])
                    if stamp in needed:
                        value=float(row[4])
                        if stamp in actual_marks:assert actual_marks[stamp]==value,'Conflicting actual raw marks'
                        actual_marks[stamp]=value
            assert len(actual_marks)==len(needed),'Required actual raw funding marks absent'
            owned_idx=np.flatnonzero(owned);raw_marks=0;cached_marks=0
            for i,required in zip(owned_idx,required_open):
                assert f.past_mark_available_us.iloc[i]==required+60000000
                if int(required//1000) in actual_marks:
                    assert f.past_mark_price.iloc[i]==actual_marks[int(required//1000)];raw_marks+=1
                else:
                    assert required>=1638316800000000
                    assert f.past_mark_price.iloc[i]==original.past_mark_price.iloc[i]
                    assert f.past_mark_available_us.iloc[i]==original.past_mark_available_us.iloc[i]
                    cached_marks+=1
            maxerr=0.0
            for i in np.flatnonzero(e['active_interval_ready']):
                selected=(t>e['funding_interval_start_us'][i])&(t<=e['funding_interval_end_us'][i])
                expected=math.fsum(float(rate)*float(mark) for rate,mark in zip(f.last_funding_rate[selected],f.past_mark_price[selected]))
                actual=e['funding_coeff'][i,j];maxerr=max(maxerr,abs(actual-expected))
                assert math.isclose(actual,expected,rel_tol=2e-15,abs_tol=1e-10)
            counts[str(symbol)]=dict(raw_CSV_execution_points_checked=len(p),raw_CSV_previous_quote_points_checked=len(q),
                owned_marks_checked_against_actual_raw_CSV=raw_marks,owned_December_marks_checked_against_immutable_cached_values=cached_marks,
                original_signed_event_fields_unchanged=len(f),execution_previous_quote_zero_count=int((q==0).sum()))
            errors[str(symbol)]=maxerr
        with np.load(folder/'derived/CONTEXT_INPUTS.npz',allow_pickle=False) as c:
            assert c['original_E5_slots'].tolist()==[0,1,4]
            assert c['past_returns'].shape==(365,30,5) and np.isfinite(c['past_returns']).all()
            assert np.array_equal(c['decision_us'],e['decision_us'])
            assert c['fixed5_covariance_ready'].all() and c['expert_eligible'].all()
            for name,first in [('DOGEUSDT','2021-01-26'),('SOLUSDT','2021-04-02')]:
                j=c['symbol_order'].tolist().index(name)
                gate=np.datetime64(first).astype('datetime64[us]').astype(np.int64)
                assert np.array_equal(c['asset_eligible'][:,1,j],c['decision_us']>=gate)
        episodes=json.loads((folder/'EPISODES.json').read_text())
        actual_intervals=[]
        for episode in episodes['episodes']:
            left=episode['first_decision_index'];right=episode['last_paid_CASH_decision_index']
            assert episode['actual_active_intervals']==right-left and e['active_interval_ready'][left:right].all()
            actual_intervals.extend(range(left,right))
        assert len(actual_intervals)==len(set(actual_intervals))==int(e['active_interval_ready'].sum())
    receipt=dict(status='INDEPENDENT_RAW_CSV_POINTS_SIGNED_FUNDING_AND_DYNAMIC_MASKS_VERIFIED',
        normalizer_or_recipe_functions_called=False,counts=counts,maximum_independent_coefficient_errors=errors,
        original_monthly_source_missing_minutes=original_missing,actual_official_daily_missing_minutes_added=added,
        no_synthetic_prices_or_marks=True,actual_distinct_eligible_active_intervals=len(actual_intervals),
        paid_episode_count=len(episodes['episodes']),exclusions=episodes['exclusions'],
        model_fits=0,model_inferences=0,backtests=0,wallets=0)
    (root/'INDEPENDENT_PACKET_AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--feature-archive',type=Path,required=True)
    a=p.parse_args();main(a.root,a.feature_archive)
