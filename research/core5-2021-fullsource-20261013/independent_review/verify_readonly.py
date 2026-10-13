"""Independent, cache-only source review. Does not regenerate source, targets or wallets."""
import os,resource
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):
    os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
if hasattr(os,'sched_setaffinity'): os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import csv,datetime,hashlib,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
BASE=Path(__file__).resolve().parent.parent
ROOT=BASE/'coin_2021_source_closure_20261013'
PREP=ROOT/'prepared_2021'
OUT=Path(__file__).resolve().parent
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
MINUTE=60_000_000;DAY=86_400_000_000;START=1609459200000000;END=1640995200000000

def fsha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def limits(m):
    def ts(y,m): return int(datetime.datetime(y,m,1,tzinfo=datetime.UTC).timestamp()*1000000)
    return ts(2021,m),ts(2021+(m==12),m%12+1)
def assert_bytes(a,b): assert np.asarray(a).tobytes()==np.asarray(b).tobytes()
def source_subset(body,wanted):
    """Independent stdlib CSV reader; inspect clocks/envelopes at requested actual rows."""
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        assert len(z.namelist())==1 and z.testzip() is None
        with z.open(z.namelist()[0]) as f:
            reader=csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig'))
            found={};count=0
            for row in reader:
                if row[0].lower() in ('open_time','open_timestamp'): continue
                assert len(row)==12
                t=int(row[0])*1000
                if t in wanted:
                    o,h,l,c=map(float,row[1:5]);assert int(row[6])*1000==t+59999000
                    assert 0<l<=min(o,c)<=max(o,c)<=h
                    found[t]=dict(open=o,high=h,low=l,close=c)
                count+=1
    assert set(found)==set(wanted)
    return found,count

def main():
    begun=time.monotonic();summary={}
    y=json.loads((ROOT/'evidence/Y2021_INDEX.json').read_text())
    d=json.loads((ROOT/'evidence/DEC2021_RECOVERY.json').read_text())
    ix=json.loads((PREP/'SOURCE_INDEX.json').read_text())
    restore=json.loads((ROOT/'PUBLIC_GIT_RESTORE_RECEIPT.json').read_text())
    pinned=[]
    for p in y['parts']: pinned.append((ROOT/'source/Y2021_parts'/p['name'],p))
    for r in d['sources']:
        for p in r['source']['parts']: pinned.append((ROOT/'source/DEC2021_parts'/r['source']['symbol']/Path(p['path']).name,p))
    assert len(pinned)==222 and sum(r['bytes'] for _,r in pinned)==171932044
    for p,r in pinned: assert p.stat().st_size==r['bytes'] and fsha(p)==r['SHA256']
    assemblies=[]
    part_groups=[([(ROOT/'source/Y2021_parts'/p['name'],p) for p in y['parts']],ROOT/'source/Y2021.zip',y['package_bytes'],y['package_SHA256'])]
    for r in d['sources']:
        a=r['source'];part_groups.append(([(ROOT/'source/DEC2021_parts'/a['symbol']/Path(p['path']).name,p) for p in a['parts']],ROOT/'source/DEC2021'/a['symbol']/(a['symbol']+'-1m-2021-12.zip'),a['ZIP_bytes'],a['ZIP_SHA256']))
    for group,path,n,digest in part_groups:
        h=hashlib.sha256()
        for p,_ in group:
            with p.open('rb') as f:
                for b in iter(lambda:f.read(1048576),b''): h.update(b)
        assert h.hexdigest()==digest==fsha(path) and path.stat().st_size==n
        assemblies.append(dict(path=str(path.relative_to(BASE)),SHA256=digest,bytes=n,independent_part_concatenation_SHA=True))
    summary['all222_parts_and_six_assemblies_hash_verified']=True
    summary['assemblies']=assemblies
    hashfiles=['source_parser.py','test_source_parser.py','prepare_full_2021.py','audit_funding.py','audit_warmup.py','assemble_offline.py','restore_public_sources.py','PUBLIC_GIT_RESTORE_RECEIPT.json','CONNECTOR_RESTORE_LEDGER.json','PUBLIC_GIT_RESTORE_LEDGER.json','WARMUP_DIAGNOSTIC.json','FUNDING_DIAGNOSTIC.json','RAW_FUNDING_EVENTS.json','CORE5_WARMUP_MASKS.npz','evidence/Y2021_INDEX.json','evidence/DEC2021_RECOVERY.json','prepared_2021/SOURCE_INDEX.json','prepared_2021/EVENTS.json','prepared_2021/DAILY_OHLC.npz']
    summary['hashes']={p:fsha(ROOT/p) for p in hashfiles}
    for name,r in ix['files'].items(): assert fsha(PREP/name)==r['SHA256'] and (PREP/name).stat().st_size==r['bytes']
    for key,file in [('warmup_proof_SHA256','WARMUP_DIAGNOSTIC.json'),('funding_raw_union_proof_SHA256','FUNDING_DIAGNOSTIC.json'),('public_restore_proof_SHA256','PUBLIC_GIT_RESTORE_RECEIPT.json')]: assert ix[key]==fsha(ROOT/file)
    sys.path.insert(0,str(ROOT))
    import test_source_parser
    test_source_parser.main()
    summary['reexecuted_worker_synthetic_checks']=13
    # Small direct saved-source funding table comparison. Saved funding marks are never read.
    raw=json.loads((ROOT/'RAW_FUNDING_EVENTS.json').read_text());events=json.loads((PREP/'EVENTS.json').read_text())
    assert len(raw)==len(events)==5475
    assert len({(r['symbol'],r['event_us']) for r in raw})==5475
    srcfeatures=BASE/'coin_native_half_mix_20261013/source/2023_FUND/features.zip'
    assert fsha(srcfeatures)=='bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'
    cube=BASE/'coin_cs_sma_recovery_20261013/inputs/Y2023.npz'
    assert fsha(cube)=='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f'
    summary['hashes'][str(srcfeatures.relative_to(BASE))]=fsha(srcfeatures)
    summary['hashes'][str(cube.relative_to(BASE))]=fsha(cube)
    member_ix={r['name']:r for r in y['members']}
    with zipfile.ZipFile(ROOT/'source/Y2021.zip') as z,zipfile.ZipFile(srcfeatures) as fz:
        features_manifest=json.loads(fz.read('MEMBERS.json'))['files']
        for s in S:
            oldname='derived/economics/'+s+'_funding_events.parquet';newname='source_tables_not_model_inputs/economics/'+s+'_funding_events.parquet'
            oldbody=z.read(oldname);newbody=fz.read(newname)
            assert hashlib.sha256(oldbody).hexdigest()==member_ix[oldname]['SHA256']
            assert hashlib.sha256(newbody).hexdigest()==features_manifest[newname]['SHA256']
            cols=['calc_time_ms','last_funding_rate','funding_interval_hours']
            old=pq.read_table(io.BytesIO(oldbody),columns=cols).to_pandas();new=pq.read_table(io.BytesIO(newbody),columns=cols).to_pandas()
            old=old[(old.calc_time_ms>=START//1000)&(old.calc_time_ms<END//1000)].sort_values('calc_time_ms')
            new=new[(new.calc_time_ms>=START//1000)&(new.calc_time_ms<END//1000)].sort_values('calc_time_ms')
            assert len(old)==1094 and len(new)==1095
            assert_bytes(old.to_numpy(),new[new.calc_time_ms.isin(old.calc_time_ms)].to_numpy())
            added=new[~new.calc_time_ms.isin(old.calc_time_ms)]
            assert len(added)==1 and int(added.calc_time_ms.iloc[0])==1640966400000
            rr=[r for r in raw if r['symbol']==s]
            assert [r['calc_time_ms'] for r in rr]==new.calc_time_ms.astype('int64').tolist()
            assert_bytes(np.array([r['raw_rate'] for r in rr]),new.last_funding_rate.to_numpy(float))
            assert_bytes(np.array([r['reported_interval_hours'] for r in rr]),new.funding_interval_hours.to_numpy(float))
    summary['direct_saved_raw_funding_union_parity_rows']=5475
    for r,e in zip(raw,events):
        assert all(e[k]==v for k,v in r.items()) and r['calc_time_ms']*1000==r['event_us']
        assert r['raw_rate_unit']=='UNCONFIRMED' and r['saved_mark_fields_not_used'] is True
        t=r['event_us'];a=((t-1)//MINUTE)*MINUTE;o=a-MINUTE;q=e['strict_prior_mark']
        if o<START:
            assert q is None and e['strict_prior_mark_status']=='UNKNOWN_PRE2021_BOUNDARY' and e['not_owned_under_fresh_CASH_start'] is True
        else:
            assert q['mark_open_us']==o and q['mark_available_us']==a and q['strict_prior_age_us']==t-a and 0<t-a<=MINUTE
            assert e['strict_prior_mark_status']=='PASS_REAL_MINUTE' and e['not_owned_under_fresh_CASH_start'] is False
    unknown=[e for e in events if e['strict_prior_mark'] is None]
    assert len(unknown)==5 and {r['symbol'] for r in unknown}==set(S) and {r['event_us'] for r in unknown}=={START+2000}
    jitter=[]
    for s in S:
        tt=np.array([r['event_us'] for r in raw if r['symbol']==s]);assert len(tt)==1095
        assert np.array_equal(tt//(8*3600*1000000),np.arange(START//(8*3600*1000000),END//(8*3600*1000000)))
        jj=tt%(8*3600*1000000);jitter.extend(jj.tolist());assert tt[-1]==1640966400000000
    summary['funding_clock_independent_integer_formula_checks']=5475
    summary['jitter_us_range']=[min(jitter),max(jitter)]
    summary['unknown_before_first_CASH_execution_events']=5
    summary['last_funding_allfive_event_us']=1640966400000000
    with np.load(cube,allow_pickle=False) as z:
        assert tuple(z['symbol_order'])==S;cube_t=z['close_available_us'].copy();cube_c=z['close'].copy()
    with np.load(PREP/'DAILY_OHLC.npz',allow_pickle=False) as z:
        assert tuple(z['symbol_order'])==S and z['ready'].all();daily={k:z[k].copy() for k in z.files}
    expect_dt=np.arange(START+DAY,END+DAY,DAY,dtype=np.int64)
    assert np.array_equal(daily['available_us'],expect_dt)
    loc=np.searchsorted(cube_t,expect_dt);assert np.array_equal(cube_t[loc],expect_dt);assert_bytes(daily['close'],cube_c[loc])
    previous={};cached_quotes={};total_rows=0;boundary_checks=0;repair_count=0;repair_added=0;month_hashes={}
    for m,mi in enumerate(ix['months'],1):
        left,right=limits(m);times=np.arange(left,right,MINUTE,dtype=np.int64);path=PREP/'months'/f'2021-{m:02}.npz'
        assert mi['month']==f'2021-{m:02}' and mi['minutes']==len(times) and len(mi['sources'])==10
        assert fsha(path)==mi['source_NPZ_SHA256'] and path.stat().st_size==mi['source_NPZ_bytes'];month_hashes[path.name]=fsha(path)
        sources={(r['symbol'],r['family']):r for r in mi['sources']};assert len(sources)==10
        with np.load(path,allow_pickle=False) as z:
            assert np.array_equal(z['times'],times) and np.array_equal(z['available_us'],times+MINUTE)
            days=(right-left)//DAY;ii=np.searchsorted(expect_dt,np.arange(left+DAY,right+DAY,DAY,dtype=np.int64))
            for j,s in enumerate(S):
                for family,key in [('klines',s+'_close'),('markPriceKlines',s+'_mark')]:
                    closes=z[key];r=sources[s,family];assert len(closes)==len(times) and np.isfinite(closes).all() and (closes>0).all();total_rows+=len(closes)
                    assert (r['first_open_us'],r['last_open_us'],r['first_available_us'],r['last_available_us'])==(left,right-MINUTE,left+MINUTE,right)
                    pb=r['past_boundary']
                    if m==1: assert pb['status']=='UNKNOWN_NOT_FILLED' and pb['close'] is None and pb['open_us'] is None
                    else: assert pb['status']=='REAL_PREVIOUS_MONTH_LAST_MINUTE' and pb['available_us']==left and pb['open_us']==left-MINUTE and pb['close']==previous[s,family]
                    previous[s,family]=float(closes[-1]);boundary_checks+=1
                    repair_count+=len(r['repair_sources']);repair_added+=sum(a['actual_daily_new_rows_added'] for a in r['repair_sources'])
                    if family=='markPriceKlines':
                        for e in events:
                            q=e['strict_prior_mark']
                            if e['symbol']==s and q is not None and left<=q['mark_open_us']<right:
                                v=float(closes[(q['mark_open_us']-left)//MINUTE]);assert_bytes(np.array(v),np.array(q['mark_close']));cached_quotes[s,q['mark_open_us']]=v
                        cached_quotes[s,left]=float(closes[0]);cached_quotes[s,right-MINUTE]=float(closes[-1])
                    else:
                        assert_bytes(closes[1439::1440],daily['close'][ii,j])
                for k in ('open','high','low','volume','quote_volume'):
                    a=z[s+'_'+k]
                    if k=='open': agg=a[::1440]
                    elif k=='high': agg=a.reshape(days,1440).max(axis=1)
                    elif k=='low': agg=a.reshape(days,1440).min(axis=1)
                    else: agg=a.reshape(days,1440).sum(axis=1)
                    assert_bytes(agg,daily[k][ii,j])
    assert total_rows==5256000 and boundary_checks==120 and repair_count==15 and repair_added==21600
    assert len(cached_quotes)>=5470
    summary.update(month_NPZ_hashes=month_hashes,cache_minute_rows_shape_clock_checked=total_rows,monthly_boundary_metadata_checks=boundary_checks,daily_OHLC_cache_aggregation_parity_cells=1825,daily_close_bitwise_cube_parity_cells=1825,all5470_funding_quotes_bitwise_cached_mark_parity=True,actual_repair_source_counts=[repair_count,repair_added])
    # Direct raw inspection: all five December mark archives at first/last/final-funding rows,
    # and July repair actual first/last rows. This is explicitly not a full raw-history reparse.
    inspected=[]
    for dr in d['sources']:
        r=dr['source'];s=r['symbol'];body=(ROOT/'source/DEC2021'/s/(s+'-1m-2021-12.zip')).read_bytes()
        final=next(e for e in events if e['symbol']==s and e['event_us']==1640966400000000)['strict_prior_mark']
        wanted={limits(12)[0],END-MINUTE,final['mark_open_us']}
        got,n=source_subset(body,wanted);assert n==44640
        for t,v in got.items(): assert_bytes(np.array(v['close']),np.array(cached_quotes[s,t]))
        inspected.append(dict(symbol=s,month='2021-12',family='markPriceKlines',raw_rows_selected=len(wanted),CSV_total_rows_observed=n,ZIP_SHA256=hashlib.sha256(body).hexdigest()))
    with zipfile.ZipFile(ROOT/'source/Y2021.zip') as z:
        for r in ix['months'][6]['sources']:
            for rr in r['repair_sources']:
                body=z.read(rr['member']);check=z.read(rr['member']+'.CHECKSUM');assert hashlib.sha256(body).hexdigest()==rr['ZIP_SHA256']==check.decode().split()[0]
                date=rr['member'][-14:-4];dt=datetime.datetime.strptime(date,'%Y-%m-%d').replace(tzinfo=datetime.UTC);left=int(dt.timestamp()*1000000)
                got,n=source_subset(body,{left,left+DAY-MINUTE});assert n==1440
                with np.load(PREP/'months'/'2021-07.npz',allow_pickle=False) as mz:
                    c=mz[r['symbol']+'_mark'];ml=limits(7)[0]
                    for t,v in got.items(): assert_bytes(np.array(v['close']),np.array(c[(t-ml)//MINUTE]))
                inspected.append(dict(symbol=r['symbol'],member=rr['member'],raw_rows_selected=2,CSV_total_rows_observed=n))
    summary['direct_raw_subset_checks']=inspected
    with np.load(ROOT/'CORE5_WARMUP_MASKS.npz',allow_pickle=False) as z:
        decisions=z['decision_us'];assert np.array_equal(decisions,np.arange(START,END,DAY,dtype=np.int64));warm={}
        for n in (21,31,200):
            masks=[]
            for j,s in enumerate(S):
                pos=np.searchsorted(cube_t,decisions);valid=np.isfinite(cube_c[:,j])&(cube_c[:,j]>0)
                expected=np.array([p>=n-1 and cube_t[p]==t and valid[p-n+1:p+1].all() for p,t in zip(pos,decisions)])
                assert np.array_equal(z[s+'_'+str(n)+'close'],expected);masks.append(expected)
            joint=np.logical_and.reduce(masks);assert np.array_equal(z['CORE5_'+str(n)+'close'],joint)
            warm[str(n)]=dict(ready_decisions=int(joint.sum()),first_ready_us=int(decisions[np.flatnonzero(joint)[0]]))
        assert warm['21']['ready_decisions']==warm['31']['ready_decisions']==365 and warm['200']==dict(ready_decisions=274,first_ready_us=1617321600000000)
    summary['warmup_masks_independent_cube_rolling_checks']=warm
    summary['status']='PASS_INDEPENDENT_CACHE_ONLY_SOURCE_REVIEW_WITH_EXPLICIT_LIMITS'
    summary['limits']=['All 222 raw public parts and six concatenation SHA256s independently checked. All 12 prepared NPZ hashes independently checked. Not a full 135-original-ZIP market-history reparse or independent historical arrival-time certificate.','Independent funding-unit certification absent; raw-fraction economics remain conditional.','Fresh CASH starts after first actual quote at 2021-01-01 00:01:00.000001 UTC. Pre2021 minute boundary remains UNKNOWN.','Target and wallet admission remain separate; dynamic warmup masks and terminal quote contract are required.']
    accounting_path=ROOT/'TRANSPORT_ACCOUNTING.json'
    accounting=json.loads(accounting_path.read_text())
    assert accounting['initial_shell_verified_parts']+accounting['connector_probe_parts']+accounting['connector_batch_parts']==222
    assert accounting['initial_shell_verified_bytes']+accounting['connector_probe_part']['bytes']+accounting['connector_batch_bytes']==171932044
    assert accounting['connector_probe_part']['name']=='originals.zip.part0036'
    assert accounting['connector_probe_part']['SHA256']==fsha(ROOT/'source/Y2021_parts/originals.zip.part0036')
    summary['hashes']['TRANSPORT_ACCOUNTING.json']=fsha(accounting_path)
    summary['provenance_accounting_note']='Supplemental TRANSPORT_ACCOUNTING.json independently read and arithmetically checked: original shell36 + connector probe1(part0036) + connector batch185 =222; shell28311552 + probe786432 + batch142834060 =171932044 bytes. Original prepared output and bound receipt are unchanged.'
    summary['elapsed_seconds']=time.monotonic()-begun;summary['peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;summary['CPU_affinity']=list(os.sched_getaffinity(0));summary['AS_limit_bytes']=2*1024**3
    (OUT/'INDEPENDENT_REVIEW.json').write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({k:summary[k] for k in ['status','cache_minute_rows_shape_clock_checked','daily_close_bitwise_cube_parity_cells','all5470_funding_quotes_bitwise_cached_mark_parity','elapsed_seconds','peak_RSS_bytes']}))
if __name__=='__main__': main()
