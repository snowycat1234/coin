"""Qualify clocks, saved source windows and endpoint quotes; never accounts."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):os.environ[k]='1'
import datetime,hashlib,json,resource
from pathlib import Path
import numpy as np
os.sched_setaffinity(0,{7})
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
ROOT=Path(__file__).resolve().parent;P=ROOT/'prepared_2021'
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY=86400000000;MINUTE=60000000;START=1617321600000000;END=1640995200000000
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc(t):return datetime.datetime.fromtimestamp(int(t)/1e6,datetime.UTC).isoformat()
def main():
    source=json.loads((P/'SOURCE_INDEX.json').read_text());warm=json.loads((ROOT/'WARMUP_DIAGNOSTIC.json').read_text())
    assert source['status']=='PASS_FULL2021_REAL_TRADE_MARK_SOURCE_ONLY'
    assert source['missing_minute_rows']==0 and source['monthly_streams']==120 and source['total_actual_minute_rows']==5256000
    decisions=np.arange(START,END,DAY,dtype=np.int64);assert len(decisions)==274
    with np.load(ROOT/'CORE5_WARMUP_MASKS.npz',allow_pickle=False) as m:
        assert tuple(m['symbol_order'])==S
        d=m['decision_us'];idx=np.searchsorted(d,decisions);assert np.array_equal(d[idx],decisions) and m['CORE5_200close'][idx].all()
        first=d[np.flatnonzero(m['CORE5_200close'])[0]];assert int(first)==START and int(m['CORE5_200close'].sum())==274
    with np.load(ROOT/'small_inputs/Y2023.npz',allow_pickle=False) as z:
        assert tuple(z['symbol_order'])==S;t=z['close_available_us'];close=z['close'];windows=[]
        for at in decisions:
            ix=int(np.searchsorted(t,at));assert ix>=199 and int(t[ix])==at
            tt=t[ix-199:ix+1];cc=close[ix-199:ix+1];assert len(tt)==200 and np.all(np.diff(tt)==DAY) and np.isfinite(cc).all() and (cc>0).all()
            windows.append(dict(decision_us=int(at),first_available_us=int(tt[0]),last_available_us=int(tt[-1]),rows=200,cells=1000,clock_SHA256=hashlib.sha256(tt.tobytes()).hexdigest(),close_C_order_SHA256=hashlib.sha256(cc.tobytes()).hexdigest()))
    endpoints=[]
    with np.load(P/'months/2021-04.npz',allow_pickle=False) as a,np.load(P/'months/2021-12.npz',allow_pickle=False) as d:
        for label,at,z in [('fresh_start',START,a),('terminal_flat_quote',END,d)]:
            ix=int(np.searchsorted(z['available_us'],at,side='right')-1);assert ix>=0 and int(z['available_us'][ix])==at and int(z['times'][ix])==at-MINUTE
            for s in S:
                close=float(z[s+'_close'][ix]);mark=float(z[s+'_mark'][ix]);assert close>0 and mark>0
                endpoints.append(dict(kind=label,symbol=s,open_us=int(z['times'][ix]),available_us=int(z['available_us'][ix]),actual_trade_close=close,actual_mark_close=mark,execution_clock_if_later_admitted_us=at+1,available_before_proposed_execution=True))
    events=json.loads((P/'EVENTS.json').read_text());selected=[e for e in events if START<=e['event_us']<END];assert len(selected)==274*3*5==4110
    for e in selected:
        q=e['strict_prior_mark'];assert q is not None and q['mark_available_us']<e['event_us'] and 0<q['strict_prior_age_us']<=MINUTE and q['strict_prior_age_us']==e['event_us']-q['mark_available_us']
    originals=json.loads((ROOT/'original/SOURCE_INDEX.json').read_text());stream_checks=[]
    for actual,expected in zip(source['months'],originals['months'],strict=True):
        assert actual['month']==expected['month'] and actual['minutes']==expected['minutes']
        assert actual['sources']==expected['sources'],'Exact published raw stream provenance differs'
        stream_checks.append(dict(month=actual['month'],source_records_exact=True,normalized_NPZ_container_exact=actual['source_NPZ_SHA256']==expected['source_NPZ_SHA256'] and actual['source_NPZ_bytes']==expected['source_NPZ_bytes']))
    result=dict(schema='CORE5_2021_APR_DEC_SOURCE_QUALIFICATION_V1',status='PASS_SOURCE_ONLY_274_DATE_CANDIDATE_FINANCIAL_GO_NOT_GRANTED',calendar_UTC=[utc(START),utc(END)],decision_dates=274,symbol_order=list(S),unchanged_all_five_200close=True,full_Jan1_200close_admitted=False,source_streams=120,total_actual_minute_rows=5256000,actual_daily_repairs=15,actual_repair_minutes=21600,selected_funding_events=4110,selected_funding_events_with_real_strict_prior_mark=4110,initial_Jan1_unknown_events_preserved=5,all_274_200close_windows=windows,actual_endpoint_quotes=endpoints,published_source_stream_parity=stream_checks,source_index_SHA256=sha(P/'SOURCE_INDEX.json'),warmup_diagnostic_SHA256=sha(ROOT/'WARMUP_DIAGNOSTIC.json'),postsource_QA_SHA256=sha(ROOT/'POSTSOURCE_QA.json'),limitations=['Pre2021 warmup uses exact saved daily provenance; no pre2021 minute reconstruction.','Historic publication and arrival timestamps remain assumptions.','Original numeric funding rates and intervals are preserved; authoritative raw-fraction rate units remain unconfirmed.','Historical listing eligibility, tick/lot/notional filters, maintenance brackets and cross-venue execution semantics are not certified.','Fees, slippage, funding cash ownership and paid terminal-flat accounting require separate native-engine admission and review.','Actual terminal quote exists at 2022-01-01T00:00:00Z; terminal execution ordering and paid flat are not simulated here.'],next_required_gates=['Freeze exact target and decision/eligible masks for this274-date candidate without changing strategy logic.','Bind source-only arrays to the existing native window interface and review clock/funding/endpoint semantics.','Review declared cost/funding unit/native filter/maintenance assumptions and independent terminal-flat tests.','Obtain separate financial execution GO before any historical accounts or results.'],targets=0,wallets=0,historical_runs=0,provider_downloads=0,holdout_reads=0,CPU_affinity=list(os.sched_getaffinity(0)),all_helper_thread_affinities=[sorted(os.sched_getaffinity(int(t))) for t in os.listdir('/proc/self/task')],peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    assert all(x==[7] for x in result['all_helper_thread_affinities'])
    (ROOT/'SOURCE_QUALIFICATION_2021_APR_DEC.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(result['status'],len(selected),len(endpoints),flush=True)
if __name__=='__main__':main()
