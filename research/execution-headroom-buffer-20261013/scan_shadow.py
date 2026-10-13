"""Bounded read-only old-ledger scan; no financial account imports/transitions."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, resource, shutil, sys, time
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import numpy as np
from headroom_buffer import *

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DERIVED=ROOT/'coin_expanded_coverage_20261013/derived_mark/DERIVED_MARK_OHLC.csv'
DEPENDENCIES=(
 'coin_native_half_mix_20261013/repo/src/quant/execution_contract.py',
 'coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py',
 'coin_native_half_mix_20261013/repo/scripts/investment/resumable_perpetual.py',
 'coin_quantity_resolution_20261013/FINE_PROFILE.json',
 'coin_quantity_resolution_20261013/fine_account.py',
 'coin_margin_protective_policy_20261013/protective_policy.py')

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def utc(t):return datetime.fromtimestamp(int(t)/1e6,timezone.utc).isoformat()

def case_descriptions():
    result=[]
    for year in (2021,2023,2024,2025):
        parent=ROOT/('coin_2021_strategy_comparison_20261013' if year==2021 else 'coin_quantity_resolution_20261013')
        case=next(c for c in read(parent/'CASE_BINDINGS.json')['cases'] if c['year']==year and c['arm']=='STATIC50')
        state=parent/('state_first_authorized_run' if year==2021 else 'state_20261013')/f'Y{year}_STATIC50_FINE_ORIGINAL'
        guard=None if year==2021 else parent/'state_20261013'/f'Y{year}_STATIC50_FINE_GUARD50'
        result.append({'year':year,'case':case,'state':str(state.relative_to(ROOT)),
                       'guard':str(guard.relative_to(ROOT)) if guard else None,
                       'source':str(Path(case['source_index_local_locator']).parent)})
    return result

def prepare_inputs():
    files={};cases=case_descriptions()
    for desc in cases:
        c=desc['case'];state=ROOT/desc['state'];binding=read(state/'BINDING.json');pointer=read(state/'recovery/POINTER.json')
        for key in ('calendar','source_index_SHA256','target_archive_SHA256','target_array_SHA256','arm','year'):
            if binding[key]!=c[key]:raise ValueError('Old wallet binding mismatch '+key)
        if pointer['binding']!=binding:raise ValueError('Genuine pointer binding mismatch')
        if binding['mode']!='ORIGINAL' or binding['fine_account_class']!='conditional_shared_default_fine_grid_sensitivity_v1':
            raise ValueError('Original fine path required')
        for local,key in [(c['source_index_local_locator'],'source_index_SHA256'),(c['target_archive_local_locator'],'target_archive_SHA256')]:
            if sha(ROOT/local)!=c[key]:raise ValueError('Input SHA differs '+local)
            files[local]=c[key]
        for name in ('ACCOUNT.json','RESULT.json','BINDING.json','MINUTE_NUMERIC.json','recovery/POINTER.json'):
            local=desc['state']+'/'+name;files[local]=sha(ROOT/local)
        if desc['guard']:
            for name in ('ACCOUNT.json','RESULT.json','BINDING.json'):
                local=desc['guard']+'/'+name;files[local]=sha(ROOT/local)
        columns=[x['name'] for x in read(state/'MINUTE_NUMERIC.json')['columns']]
        expected=['nav','free_cash','isolated_balance','gross_notional','net_signed_notional',
                  'cumulative_fees','cumulative_execution_costs','cumulative_funding','cumulative_turnover']
        expected += [s+'_'+field for field in ('quantity','signed_marked_notional','isolated_balance','isolated_equity','signed_weight') for s in SYMBOLS]
        expected+=['gross_weight','net_signed_weight','close_us']
        if columns!=expected:raise ValueError('Exact original numeric column order required')
        index=read(ROOT/c['source_index_local_locator'])
        if tuple(index.get('symbol_order',index.get('symbols')))!=SYMBOLS:raise ValueError('Source symbol order')
        desc['source_months']=[{k:rec[k] for k in ('month','source_NPZ_SHA256','source_NPZ_bytes')} for rec in index['months']]
        desc['original_successful_minutes']=pointer['completed_minutes']
    for local in DEPENDENCIES:files[local]=sha(ROOT/local)
    local=str(DERIVED.relative_to(ROOT));files[local]=sha(DERIVED)
    if files[local]!=read(ROOT/'coin_expanded_coverage_20261013/prepared_2024_cold/SOURCE_INDEX.json')['derived_mark_csv_SHA256']:
        raise ValueError('Derived mark identity changed')
    out={'status':'BOUND_EXISTING_ORIGINAL_FINE_CSH_INPUTS_NO_WALLET','cases':cases,'files_SHA256':files,
         'source_months_verified_during_scan':True,'original_daily_chunk_SHA_verified_during_scan':True,
         'account_imports':0,'historical_wallets':0,'new_fits':0,'source_requests':0}
    write(HERE/'INPUTS.json',out);print(json.dumps({'cases':len(cases),'files_bound':len(files),'INPUTS_SHA256':sha(HERE/'INPUTS.json')}))

def verify_gate():
    freeze=read(HERE/'FROZEN_CODE.json')
    for local,expected in freeze['SHA256'].items():
        if sha(HERE/local)!=expected:raise ValueError('Frozen code/input file changed '+local)
    review=read(HERE/'REVIEW_RECEIPT.json')
    if review.get('status')!='PASS_READ_ONLY_SHADOW_CONTRACT' or review.get('freeze_SHA256')!=sha(HERE/'FROZEN_CODE.json'):
        raise ValueError('Independent exact-freeze review required')
    inputs=read(HERE/'INPUTS.json')
    for local,expected in inputs['files_SHA256'].items():
        if sha(ROOT/local)!=expected:raise ValueError('Bound existing file changed '+local)
    if sys.flags.optimize or len(os.sched_getaffinity(0))!=1:raise ValueError('Assertions enabled and exactly one CPU required')
    if any(not 0<x<=4_000_000_000 for x in resource.getrlimit(resource.RLIMIT_AS)) or any(not 0<x<=600 for x in resource.getrlimit(resource.RLIMIT_CPU)):
        raise ValueError('Finite AS/CPU limits required')
    if shutil.disk_usage(HERE).free<16_106_127_360+50_000_000:raise ValueError('15GiB reserve plus output budget required')
    mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:','SwapTotal:'))}
    if mem['SwapTotal'] or mem['MemTotal']-mem['MemAvailable']+2_000_000_000>8_000_000_000:raise ValueError('Shared8GB/zero-swap memory gate')
    return inputs

def load_source(desc):
    pieces=[];counts=Counter()
    for rec in desc['source_months']:
        p=ROOT/desc['source']/'months'/(rec['month']+'.npz')
        if sha(p)!=rec['source_NPZ_SHA256'] or p.stat().st_size!=rec['source_NPZ_bytes']:raise ValueError('Monthly source SHA/size changed')
        with np.load(p,allow_pickle=False) as z:
            piece={'times':z['times'].copy()}
            for s in SYMBOLS:
                for k in ('mark','open','quote_volume'):piece[s+'_'+k]=z[s+'_'+k].copy()
        pieces.append(piece);counts['monthly_source_hashes']+=1
    source={k:np.concatenate([p[k] for p in pieces]) for k in pieces[0]}
    start,end=desc['case']['calendar']
    # Existing source identity promises full grid. A corrupt structural input is
    # retained as SCAN_FAILED, never silently aligned to a different calendar.
    np.testing.assert_array_equal(source['times'],np.arange(start,end,MINUTE,dtype=np.int64))
    derived={s:np.zeros(len(source['times']),dtype=bool) for s in SYMBOLS}
    if desc['year']==2024:
        with DERIVED.open() as f:
            rows=list(csv.DictReader(f))
        if len(rows)!=10:raise ValueError('Exact ten derived original cells')
        for row in rows:
            t=int(row['open_time_ms'])*1000;k=int(np.searchsorted(source['times'],t))
            if source['times'][k]!=t or row['source_missing']!='True':raise ValueError('Derived source coordinates')
            derived[row['symbol']][k]=True
    return source,derived,dict(counts)

def numeric_chunks(desc):
    state=ROOT/desc['state'];ptr=read(state/'recovery/POINTER.json');at=0
    for rec in ptr['chunks']:
        p=state/'recovery'/rec['path']
        if sha(p)!=rec['SHA256']:raise ValueError('Original daily chunk SHA changed')
        with np.load(p,allow_pickle=False) as z:a=z['minute_chunk'].copy()
        if a.shape!=(rec['rows'],36) or not np.isfinite(a).all():raise ValueError('Numeric old ledger shape/finite')
        yield at,a;at+=len(a)
    if at!=ptr['completed_minutes']:raise ValueError('Original prefix count mismatch')

def intervals(mask, times, values=None):
    indices=np.flatnonzero(mask)
    out=[]
    if not len(indices):return out
    start=prev=int(indices[0]);value=None if values is None else str(values[start])
    for raw in indices[1:]:
        i=int(raw);new=None if values is None else str(values[i])
        if i!=prev+1 or new!=value:
            out.append({'start_close_us':int(times[start]),'end_close_us':int(times[prev]),'start_UTC':utc(times[start]),'end_UTC':utc(times[prev]),'minutes':prev-start+1,'reason':value})
            start=i;value=new
        prev=i
    out.append({'start_close_us':int(times[start]),'end_close_us':int(times[prev]),'start_UTC':utc(times[start]),'end_UTC':utc(times[prev]),'minutes':prev-start+1,'reason':value})
    return out

def fixed_inventory_reference(q, equity, mark, signal, source, symbol, completion, derived):
    times=source['times']+MINUTE
    left=int(np.searchsorted(times,signal,side='right'));right=int(np.searchsorted(times,signal+5*MINUTE,side='right'))
    ps=source[symbol+'_mark'][left:right];ts=times[left:right]
    expected=np.arange(signal+MINUTE,signal+6*MINUTE,MINUTE,dtype=np.int64)
    reason=('MISSING_OR_DUPLICATE_REAL_MARK_CLOSE' if not np.array_equal(ts,expected) else
            'INVALID_REAL_MARK' if not (np.isfinite(ps).all() and (ps>0).all()) else
            'DERIVED_OR_UNKNOWN_FUTURE_MARK' if np.any(derived[left:right]) else None)
    if reason is not None:
        return {'scope':'POSTERIOR_FIXED_INVENTORY_REFERENCE_ONLY_NOT_SAFETY_CERTIFICATION',
                'status':'NOT_READY_REFERENCE','reason':reason,'first_maintenance_cross_close_us':None,
                'first_maintenance_cross_UTC':None,'cross_before_capacity_completion':None,
                'observed_source_mark_closes':len(ts),'checked_real_mark_closes':0,'minimum_price_only_headroom_USDT':None}
    es=equity+q*(ps-mark);mm=np.abs(q)*ps*MMR
    bad=np.flatnonzero(es<=mm)
    cross=int(ts[bad[0]]) if len(bad) else None
    return {'status':'READY_REFERENCE','reason':None,'scope':'FIXED_TRIGGER_Q_PRICE_ONLY_REFERENCE_IGNORES_SHADOW_CLOSES_FUTURE_FUNDING_AND_OLD_FILLS_NOT_SAFETY_CERTIFICATION',
            'first_maintenance_cross_close_us':cross,'first_maintenance_cross_UTC':utc(cross) if cross else None,
            'cross_before_capacity_completion':bool(cross is not None and (completion is None or cross<=completion)),
            'checked_real_mark_closes':len(ts),'minimum_price_only_headroom_USDT':float(np.min(es-mm)) if len(ps) else None}

def scan_case(desc, outdir):
    begun=time.monotonic();source,derived,hashes=load_source(desc)
    n=desc['original_successful_minutes'];times=source['times'][:n]+MINUTE
    q=np.empty((n,5));E=q.copy();B=q.copy();N=q.copy()
    hashes['original_daily_chunk_hashes']=0
    for at,a in numeric_chunks(desc):
        q[at:at+len(a)]=a[:,9:14];N[at:at+len(a)]=a[:,14:19];B[at:at+len(a)]=a[:,19:24];E[at:at+len(a)]=a[:,24:29]
        hashes['original_daily_chunk_hashes']+=1
    state=ROOT/desc['state'];original=read(state/'RESULT.json');halt=original.get('stop_us')
    pointer=read(state/'recovery/POINTER.json')
    if original['completed_minutes']!=n or original['genuine_state_hash']!=pointer['state_hash']:
        raise ValueError('Genuine original RESULT/POINTER prefix identity')
    if halt is not None and (not len(times) or int(times[-1])>=int(halt)):
        raise ValueError('Only successful common prefix strictly before original halt')
    if desc['year']==2024 and n!=461448:raise ValueError('Frozen 2024 successful common-prefix limit')
    result={'year':desc['year'],'case_id':original['case_id'],'observed_original_successful_minutes':n,
            'required_original_minutes':(desc['case']['calendar'][1]-desc['case']['calendar'][0])//MINUTE,
            'original_halt_us':halt,'original_halt_UTC':utc(halt) if halt else None,
            'original_account_status':original['account_status'],'genuine_original_state_hash':original['genuine_state_hash'],
            'source_and_chunk_hashes':hashes,'symbols':{},'new_wallets':0,'new_fits':0,'account_transitions':0,'hypothetical_PnL':None}
    stats=Counter();episodes=[];old_events=[]
    if desc['guard']:
        old_events=read(ROOT/desc['guard']/'ACCOUNT.json')['protective_policy']['events']
        old_events=[x for x in old_events if x['kind']=='FULL_EXIT_SIGNAL']
    for j,s in enumerate(SYMBOLS):
        f=features(source['times'],source[s+'_mark'],source[s+'_open'],derived[s])
        f={k:v[:n] for k,v in f.items()};P=source[s+'_mark'][:n]
        # Validate source mark against original own signed marked notional.
        np.testing.assert_allclose(N[:,j],q[:,j]*P,rtol=2e-15,atol=1e-10)
        a=assess(q[:,j],E[:,j],P,f['a_down'],f['a_up'],f['g_down'],f['g_up'])
        flag=a['trigger']&f['ready'];old=(q[:,j]!=0)&(B[:,j]>0)&(E[:,j]<=.5*B[:,j])
        invested=q[:,j]!=0;ready=f['ready'];rows=np.flatnonzero(flag)
        summary={'ready_minutes':int(ready.sum()),'not_ready_minutes':int((~ready).sum()),
            'not_ready_hours':float((~ready).sum()/60),'not_ready_reasons':dict(Counter(f['reason'][~ready])),
            'invested_not_ready_minutes':int((invested&~ready).sum()),'trigger_minutes':len(rows),
            'trigger_long_minutes':int((flag&(q[:,j]>0)).sum()),'trigger_short_minutes':int((flag&(q[:,j]<0)).sum()),
            'original_old_guard50_condition_minutes':int(old.sum()),
            'ready_comparison':{'both':int((flag&old).sum()),'buffer_only':int((flag&~old).sum()),
                'guard50_only':int((~flag&old&ready).sum()),'neither':int((~flag&~old&ready).sum())},
            'old_condition_not_ready_minutes':int((old&~ready).sum()),
            'trigger_months':dict(Counter(utc(times[i])[:7] for i in rows)),
            'near_float_boundary_minutes':int((invested&ready&(np.abs(a['buffered_headroom'])<=1e-8)).sum()),
            'minimum_ready_buffered_headroom_USDT':float(np.min(a['buffered_headroom'][invested&ready])) if (invested&ready).any() else None,
            'not_ready_intervals':intervals(~ready,times,f['reason']),
            'old_guard_observed_exit_signals':[]}
        costs=Counter();prior=-2;prior_sign=0;active=None
        with (outdir/(s+'_TRIGGERS.csv')).open('x',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=['signal_us','signal_UTC','direction','quantity','original_equity','original_collateral','current_mark','a_adverse_log','g_adverse_log','stressed_mark','stressed_equity','maintenance','closecost_reserve','buffered_headroom','guard50_condition','capacity_complete','capacity_completion_event_us','fixed_q_reference_cross_close_us','capacity_complete_before_original_halt'])
            writer.writeheader()
            for i0 in rows:
                i=int(i0);signal=int(times[i]);quantity=float(q[i,j]);sign=1 if quantity>0 else -1
                w=exit_witness(quantity,signal,source['times'],source[s+'_open'],source[s+'_quote_volume'])
                ref=fixed_inventory_reference(quantity,float(E[i,j]),float(P[i]),signal,source,s,w['completion_event_us'],derived[s])
                before=bool(w['capacity_complete'] and (halt is None or w['completion_event_us']<halt))
                costs['capacity_covered_trigger_minutes']+=int(w['capacity_complete']);costs['capacity_insufficient_trigger_minutes']+=int(not w['capacity_complete'])
                costs['covered_before_original_halt_minutes']+=int(before)
                costs['fixed_q_reference_not_ready_trigger_minutes']+=int(ref['status']=='NOT_READY_REFERENCE')
                costs['fixed_q_reference_cross_before_capacity_completion_minutes']+=int(ref['cross_before_capacity_completion'] is True)
                row=dict(signal_us=signal,signal_UTC=utc(signal),direction='LONG' if sign>0 else 'SHORT',quantity=quantity,original_equity=float(E[i,j]),original_collateral=float(B[i,j]),current_mark=float(P[i]),a_adverse_log=float(f['a_down' if sign>0 else 'a_up'][i]),g_adverse_log=float(f['g_down' if sign>0 else 'g_up'][i]),guard50_condition=bool(old[i]),capacity_complete=w['capacity_complete'],capacity_completion_event_us=w['completion_event_us'],fixed_q_reference_cross_close_us=ref['first_maintenance_cross_close_us'],capacity_complete_before_original_halt=before)
                for k in ('stressed_mark','stressed_equity','maintenance','closecost_reserve','buffered_headroom'):row[k]=float(a[k][i])
                writer.writerow(row)
                if i!=prior+1 or sign!=prior_sign:
                    active={'symbol':s,'direction':row['direction'],'first_trigger':row,'first_trigger_capacity_witness':w,'first_trigger_fixed_q_reference':ref,
                            'first_trigger_minutes_before_original_halt':(halt-signal)/MINUTE if halt else None,'trigger_minutes':1,'last_signal_us':signal}
                    episodes.append(active)
                else:active['trigger_minutes']+=1;active['last_signal_us']=signal
                # Latest observed trigger's witness is important next to halt.
                active['last_trigger']=row;active['last_trigger_capacity_witness']=w;active['last_trigger_fixed_q_reference']=ref
                prior=i;prior_sign=sign
        summary['capacity_and_fixed_inventory_reference_counts']=dict(costs)
        summary['trigger_episodes']=sum(x['symbol']==s for x in episodes)
        for event in old_events:
            if event['symbol']!=s:continue
            i=int((event['event_us']-desc['case']['calendar'][0])//MINUTE-1)
            summary['old_guard_observed_exit_signals'].append({'signal_us':event['event_us'],'signal_UTC':utc(event['event_us']),
                'guard_path_quantity':event['quantity'],'original_prefix_available':0<=i<n,
                'buffer_on_original_path':bool(flag[i]) if 0<=i<n else None,
                'buffer_ready_on_original_path':bool(ready[i]) if 0<=i<n else None,
                'original_path_guard50_condition':bool(old[i]) if 0<=i<n else None,
                'scope':'CHANGED_GUARD_PATH_EVENT_COMPARED_TO_ORIGINAL_AT_SAME_CLOCK_NOT_IDENTICAL_PATH_AFTER_FIRST_EXIT'})
        result['symbols'][s]=summary;stats['trigger_minutes']+=len(rows);stats['trigger_episodes']+=summary['trigger_episodes'];stats.update(costs)
    result['total_asset_minute_counts']=dict(stats);result['episodes']=episodes
    result['old_guard_comparison_scope']='Mechanical guard50 condition evaluated on original q/E/B path; observed old guard events are changed-path evidence. Shadow never updates later q/E.'
    result['witness_scope']='Five-open coverage is a posterior optimistic protected-priority capacity/price/fee reference. Actual executable paid-flat cash/equity acceptability, future funding and new-strategy PnL NOT_RUN.'
    result['elapsed_seconds']=time.monotonic()-begun;result['maxRSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    write(outdir/'RESULT.json',result)
    print(json.dumps({'year':desc['year'],'elapsed_seconds':result['elapsed_seconds'],'trigger_asset_minutes':stats['trigger_minutes'],'trigger_episodes':stats['trigger_episodes'],'maxRSS_bytes':result['maxRSS_bytes']}),flush=True)
    return result

def scan():
    inputs=verify_gate();out=HERE/'scan';out.mkdir();begun=time.monotonic();results=[]
    for desc in inputs['cases']:
        caseout=out/str(desc['year']);caseout.mkdir()
        try:result=scan_case(desc,caseout);results.append(result)
        except BaseException as e:
            write(caseout/'FAILURE.json',{'status':'SCAN_FAILED_RETAINED','exception_type':type(e).__name__,'message':str(e),'new_wallets':0});raise
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>2_000_000_000:raise RuntimeError('2GBRSS observer cap')
        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>50_000_000:raise RuntimeError('50MBoutput cap')
        if time.monotonic()-begun>900:raise RuntimeError('900sec wall cap')
    write(out/'SUMMARY.json',{'status':'COMPLETE_BOUNDED_READ_ONLY_SHADOW','freeze_SHA256':sha(HERE/'FROZEN_CODE.json'),'review_SHA256':sha(HERE/'REVIEW_RECEIPT.json'),
        'elapsed_seconds':time.monotonic()-begun,'maxRSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'historical_wallets':0,'fits':0,'financial_account_imports':0,'financial_transitions':0,'new_source_requests':0,
        'year_results':[{'year':r['year'],'original_successful_minutes':r['observed_original_successful_minutes'],'original_halt_us':r['original_halt_us'],'totals':r['total_asset_minute_counts']} for r in results]})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare-inputs','scan']);args=parser.parse_args()
    prepare_inputs() if args.action=='prepare-inputs' else scan()
