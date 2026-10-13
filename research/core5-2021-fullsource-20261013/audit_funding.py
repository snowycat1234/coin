"""Audit saved actual funding event unions. Never reuse their saved price fields."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import hashlib,io,json,time,zipfile
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from inspect_cached_prefix import prefix_members
from source_parser import S,START,END,MINUTE,utc
ROOT=Path(__file__).resolve().parent;FEATURES=Path(os.environ.get('COIN_FEATURES_PATH',str(ROOT.parent/'coin_native_half_mix_20261013/source/2023_FUND/features.zip')))
COLS=['calc_time_ms','last_funding_rate','funding_interval_hours']
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    begin=time.monotonic();past_members,prefix=prefix_members(max_parts=36);assert prefix['verified_contiguous_parts']==36
    raw=FEATURES.read_bytes();assert sha(raw)=='bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'
    proofs=[];events=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        for s in S:
            name='derived/economics/'+s+'_funding_events.parquet';old=past_members[name];name2='source_tables_not_model_inputs/economics/'+s+'_funding_events.parquet';new=z.read(name2);assert sha(new)==members[name2]['SHA256']
            past=pq.read_table(io.BytesIO(old),columns=COLS).to_pandas();recent=pq.read_table(io.BytesIO(new),columns=COLS).to_pandas();past=past[(past.calc_time_ms>=START//1000)&(past.calc_time_ms<END//1000)].sort_values('calc_time_ms');recent=recent[(recent.calc_time_ms>=START//1000)&(recent.calc_time_ms<END//1000)].sort_values('calc_time_ms')
            assert len(past)==1094 and len(recent)==1095 and not recent.calc_time_ms.duplicated().any() and np.isfinite(recent.to_numpy()).all()
            common=past.set_index('calc_time_ms');newcommon=recent.set_index('calc_time_ms').loc[common.index];assert np.array_equal(common.to_numpy(),newcommon.to_numpy()) and common.to_numpy().tobytes()==newcommon.to_numpy().tobytes(),'Conflicting actual-rate overlap'
            added=recent[~recent.calc_time_ms.isin(past.calc_time_ms)];assert len(added)==1 and int(added.calc_time_ms.iloc[0])==1640966400000
            times=recent.calc_time_ms.to_numpy(np.int64)*1000;hours=recent.funding_interval_hours.to_numpy(float);delta=np.diff(times);error=delta-hours[:-1]*3600000000
            assert len(times)==365*3 and (hours==8).all() and (np.abs(error)<=1_000_000).all();assert np.array_equal(times//(8*3600000000),np.arange(START//(8*3600000000),END//(8*3600000000)))
            jitter=times%(8*3600000000);first=int(times[0]);assert START<first<START+MINUTE+1
            for r in recent.itertuples(index=False):events.append(dict(symbol=s,event_us=int(r.calc_time_ms)*1000,calc_time_ms=int(r.calc_time_ms),raw_rate=float(r.last_funding_rate),reported_interval_hours=float(r.funding_interval_hours),raw_rate_unit='UNCONFIRMED',saved_mark_fields_not_used=True))
            proofs.append(dict(symbol=s,old_SHA_bound_member_SHA256=sha(old),actual2020plus_member_SHA256=sha(new),exact_overlap_rows=1094,restored_missing_event=dict(event_UTC=utc(int(added.calc_time_ms.iloc[0])*1000),raw_rate=float(added.last_funding_rate.iloc[0]),reported_interval_hours=float(added.funding_interval_hours.iloc[0])),events=1095,first_event_UTC=utc(first),last_event_UTC=utc(times[-1]),reported_interval_histogram={'8h':1095},actual_interval_min_us=int(delta.min()),actual_interval_max_us=int(delta.max()),actual_interval_error_from_reported_min_us=int(error.min()),actual_interval_error_from_reported_max_us=int(error.max()),event_timestamp_jitter_min_us=int(jitter.min()),event_timestamp_jitter_max_us=int(jitter.max()),first_event_before_fresh_CASH_execution=True,first_event_prior_mark_requires_unrestored_2020_12_31_tape=True,remaining_owned_eligible_event_count_after_first_execution=1094))
    events.sort(key=lambda r:(r['event_us'],r['symbol']));out=ROOT/'RAW_FUNDING_EVENTS.json';out.write_text(json.dumps(events,indent=2,sort_keys=True,allow_nan=False)+'\n')
    result=dict(status='PASS_REAL2021_RATE_INTERVAL_STREAMS_PRIOR_MARK_GATE_PENDING',calendar_us=[START,END],symbol_order=list(S),funding_events=len(events),event_streams=proofs,events_file=dict(path=out.name,bytes=out.stat().st_size,SHA256=sha(out.read_bytes())),first_fresh_CASH_execution_us=START+MINUTE+1,first_events_not_owned_under_fresh_CASH_contract=5,remaining_events_requiring_real_strict_prior_mark=5470,real_strict_prior_mark_values_certified_in_this_report=0,prior_mark_gate='PENDING_FULL_REAL_MINUTE_MARK_SOURCE',strict_prior_policy='Latest actual completed minute with available_us < raw event_us and age <= 60000000us. Preserve original millisecond jitter. At equality use the previous completed minute. No saved marks, ffill, trade substitute or fixed-clock coercion.',rate_unit='Original numeric rate values preserved, authoritative raw fraction/units not newly certified. Any raw-fraction economic calculation is conditional.',terminal_interval_warning='Rate streams and minute sources are assessed on [2021-01-01,2022-01-01). Do not use the prior 364-active-interval consumer to assert a new 365-interval wallet or invent beyond-calendar quotes.',targets_generated=0,wallets_created=0,historical_runs=0,provider_downloads=0,Library_calls=0,retained_2026_opened=0,elapsed_seconds=time.monotonic()-begin,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,CPU_affinity=list(os.sched_getaffinity(0)),AS_limit_bytes=2*1024**3)
    (ROOT/'FUNDING_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n');print(json.dumps({k:result[k] for k in ('status','funding_events','remaining_events_requiring_real_strict_prior_mark','peak_RSS_bytes','elapsed_seconds')}),flush=True)
if __name__=='__main__':main()
