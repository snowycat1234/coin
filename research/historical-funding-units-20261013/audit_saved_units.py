"""Read-only saved-source identity and fixed-tape funding arithmetic audit.

Never import execution/financial kernels or generate targets, wallets, or fits.
No network calls. Read only named already-seen 2021/23/24/25 sources.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
if hasattr(os,'sched_setaffinity'):
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import argparse, csv, hashlib, io, json, struct, time, zipfile
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
D=Decimal
YEAR_EVENTS={
 2021:'coin_2021_source_closure_20261013/prepared_2021/EVENTS.json',
 2023:'coin_native_half_mix_20261013/prepared_2023/EVENTS.json',
 2024:'coin_expanded_coverage_20261013/prepared_2024/EVENTS.json',
 2025:'coin_native_half_mix_20261013/prepared_2025/EVENTS.json',
}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def record(path):
    p=ROOT/path
    return dict(path=str(path),bytes=p.stat().st_size,SHA256=file_sha(p))
def write(name,obj):
    p=OUT/name
    with p.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def key(r):return r['symbol'],int(r['event_us'])
def value(r,k):return D(r.get('decimal_strings',{}).get(k,str(r[k])))
def main():
    start=time.monotonic();events={};source_match={};inputs=[]
    for year,path in YEAR_EVENTS.items():
        rows=json.loads((ROOT/path).read_bytes());assert len({key(r) for r in rows})==len(rows)
        events[year]={key(r):r for r in rows};inputs.append(record(path))
        stream=[]
        for s in S:
            e=[r for r in rows if r['symbol']==s];ts=np.array([r['event_us'] for r in e],dtype=np.int64);h=np.array([r['reported_interval_hours'] for r in e])
            rate=np.array([r['raw_rate'] for r in e],dtype=float);delta=np.diff(ts);assert (h==8).all()
            assert len(e)==(366 if year==2024 else 365)*3
            assert (np.abs(delta-8*3600000000)<=1000000).all()
            stream.append(dict(symbol=s,events=len(e),reported_hours=dict(Counter(map(str,h))),actual_gap_min_us=int(delta.min()),actual_gap_max_us=int(delta.max()),jitter_min_us=int((ts%(8*3600000000)).min()),jitter_max_us=int((ts%(8*3600000000)).max()),min_rate=float(rate.min()),max_rate=float(rate.max()),sum_rate=float(rate.sum())))
        source_match[str(year)]=dict(events=len(rows),unique_events=True,streams=stream)
    # Original e0 member bytes; check all rows relevant to named historical years.
    path='coin_native_half_mix_20261013/source/2023_FUND/features.zip';inputs.append(record(path))
    original=[]
    with zipfile.ZipFile(ROOT/path) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        provenance=json.loads(z.read('provenance/PRIOR_PUBLIC_SOURCE_RECEIPTS.json'))
        for s in S:
            name=f'source_tables_not_model_inputs/economics/{s}_funding_events.parquet';raw=z.read(name)
            assert sha(raw)==members[name]['SHA256']
            table=pq.read_table(io.BytesIO(raw),columns=['calc_time_ms','last_funding_rate','funding_interval_hours'])
            matches=Counter();seen=Counter();mismatch=[]
            for r in table.to_pylist():
                e=(s,int(r['calc_time_ms'])*1000)
                for year in (2021,2023,2024):
                    if e not in events[year]:continue
                    q=events[year][e];seen[year]+=1
                    good=float(q['raw_rate'])==float(r['last_funding_rate']) and float(q['reported_interval_hours'])==float(r['funding_interval_hours'])
                    matches[year]+=int(good)
                    if not good:mismatch.append(dict(year=year,event=e,source=r,prepared=q))
            assert not mismatch
            original.append(dict(symbol=s,member=name,member_SHA256=sha(raw),bytes=len(raw),rows=table.num_rows,matched_prepared_events=dict(matches),seen_prepared_events=dict(seen),schema=str(table.schema)))
        priors=[r for r in provenance['objects'] if r.get('family')=='fundingRate' and r.get('symbol') in S and any(r.get('month','').startswith(str(y)) for y in (2021,2023,2024))]
    source_match['e0_parquet']=dict(wrapper_SHA256=inputs[-1]['SHA256'],members=original,prior_receipt_count=len(priors),prior_receipts_status=provenance['status'],original_raw_bodies_present=False,unit_not_certified_by_receipts=True)
    # H1-2024 saved normalized stream is an independent exact-byte saved source.
    path='coin_expanded_coverage_20261013/H1.zip';inputs.append(record(path));h1=[]
    with zipfile.ZipFile(ROOT/path) as z:
        manifest=json.loads(z.read('h1_market/reports/DATASET_MANIFEST.json'))
        for s in S:
            name=f'h1_market/data/normalized/{s}_funding_events.parquet';raw=z.read(name)
            table=pq.read_table(io.BytesIO(raw),columns=['calc_time_ms','last_funding_rate','funding_interval_hours'])
            total=0
            for r in table.to_pylist():
                e=(s,int(r['calc_time_ms'])*1000)
                if e not in events[2024]:continue
                q=events[2024][e];assert q['raw_rate']==r['last_funding_rate'];assert q['reported_interval_hours']==r['funding_interval_hours'];total+=1
            h1.append(dict(symbol=s,member=name,SHA256=sha(raw),matched_prepared_events=total))
        raw_names=[n for n in z.namelist() if '/raw/fundingRate/' in n and n.endswith('.zip')]
    source_match['2024_H1_saved_parquet']=dict(members=h1,raw_funding_bodies_present=len(raw_names),producer_unit=manifest.get('funding_rate_unit'),producer_time=manifest.get('funding_time_semantics'))
    # Original official funding archive bodies already retained in local storage.
    proofs=[]
    configs=[(2024,'coin_expanded_coverage_20261013/coin_public_tail_archives_20261008_part01.zip','tail_data/data/raw/fundingRate/',range(7,13)),(2025,'coin_native_half_mix_20261013/source/2025_FUND/PRIMITIVES.zip','archives/',range(1,13))]
    for year,path,prefix,months in configs:
        inputs.append(record(path))
        if year==2025:
            primitive_manifest_path='coin_native_half_mix_20261013/source/2025_FUND/MANIFEST.json'
            outer_manifest=json.loads((ROOT/primitive_manifest_path).read_text())
            assert inputs[-1]['SHA256']==outer_manifest['SHA256']
            inputs.append(record(primitive_manifest_path))
            consumer_path='coin_native_half_mix_20261013/source/2025_CONSUMER/CONSUMER.zip'
            consumer_manifest_path='coin_native_half_mix_20261013/source/2025_CONSUMER/MANIFEST.json'
            consumer_manifest=json.loads((ROOT/consumer_manifest_path).read_text())
            consumer_members={r['path']:r for r in consumer_manifest['members']}
            inputs.extend([record(consumer_path),record(consumer_manifest_path)])
            assert inputs[-2]['SHA256']==consumer_manifest['archive_SHA256'] and inputs[-2]['bytes']==consumer_manifest['archive_bytes']
            consumer=zipfile.ZipFile(ROOT/consumer_path)
        with zipfile.ZipFile(ROOT/path) as outer:
            if year==2024:producer=json.loads(outer.read('tail_data/reports/download_manifest.json'));producer_rows=producer['archives']
            for s in S:
                parquet=None
                if year==2025:
                    pname=f'economics2025/{s}_funding_events.parquet';praw=consumer.read(pname)
                    assert sha(praw)==consumer_members[pname]['SHA256'] and len(praw)==consumer_members[pname]['bytes']
                    parquet={int(r['calc_time_ms']):r for r in pq.read_table(io.BytesIO(praw),columns=['calc_time_ms','last_funding_rate','funding_interval_hours']).to_pylist()}
                for month in months:
                    m=f'{year}-{month:02d}';base=f'{s}-fundingRate-{m}.zip'
                    name=(prefix+f'{s}/'+base) if year==2024 else (prefix+f'{s}_fundingRate_'+base)
                    raw=outer.read(name)
                    if year==2024:
                        checksum=outer.read(name+'.CHECKSUM');assert sha(raw)==checksum.decode().split()[0]
                        pr=next(r for r in producer_rows if r.get('symbol')==s and r.get('family')=='fundingRate' and r.get('year')==year and r.get('month')==month)
                        assert sha(raw)==pr['sha256'];receipt_sha=None
                    else:
                        rn='receipts/'+name.removeprefix(prefix)+'.json';rb=outer.read(rn);pr=json.loads(rb);assert sha(raw)==pr['SHA256'];receipt_sha=sha(rb)
                        assert sha(raw)==outer_manifest['members'][name]['SHA256']
                    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
                        assert len(inner.namelist())==1 and inner.testzip() is None
                        csvraw=inner.read(inner.namelist()[0]);reader=csv.DictReader(io.StringIO(csvraw.decode()))
                        assert reader.fieldnames==['calc_time','funding_interval_hours','last_funding_rate'];rows=list(reader)
                    sourceids=[];floatmatch=0;decimalmatch=0;parquetmatch=0;examples=[]
                    for r in rows:
                        t=int(r['calc_time']);k=(s,t*1000);q=events[year][k]
                        assert float(q['reported_interval_hours'])==float(r['funding_interval_hours'])
                        assert float(q['raw_rate'])==float(r['last_funding_rate'])
                        floatmatch+=1;decimalmatch+=int(D(str(q['raw_rate']))==D(r['last_funding_rate']))
                        assert decimalmatch==floatmatch
                        if parquet is not None:
                            p=parquet[t];assert float(p['last_funding_rate'])==float(r['last_funding_rate']);assert float(p['funding_interval_hours'])==float(r['funding_interval_hours']);parquetmatch+=1
                        sourceids.append(k)
                        if len(examples)<2:examples.append(dict(symbol=s,calc_time_source=r['calc_time'],event_us=q['event_us'],last_funding_rate_source=r['last_funding_rate'],prepared_raw_rate=q['raw_rate'],funding_interval_hours_source=r['funding_interval_hours']))
                    assert len(sourceids)==len(set(sourceids))
                    proofs.append(dict(year=year,month=m,symbol=s,wrapper=path,member=name,ZIP_SHA256=sha(raw),CSV_SHA256=sha(csvraw),CHECKSUM_SHA256=sha(checksum) if year==2024 else None,receipt_SHA256=receipt_sha,official_URL=pr['url'],raw_rows=len(rows),prepared_float_exact_matches=floatmatch,prepared_decimal_exact_matches=decimalmatch,consumer_parquet_float_exact_matches=parquetmatch,examples=examples,semantic_unit_declaration_in_csv=None))
        if year==2025:consumer.close()
    source_match['official_raw_matches']=dict(archives=len(proofs),events=sum(x['raw_rows'] for x in proofs),years={str(y):dict(archives=sum(x['year']==y for x in proofs),events=sum(x['raw_rows'] for x in proofs if x['year']==y)) for y in (2024,2025)},source_rate_scale_transformation=1,source_time_transformation='int(calc_time_ms)*1000; millisecond jitter retained',interval_transformation='none; reported nominal hours retained; no hourly-rate proration',economic_rate_unit_certified=False)
    write('SOURCE_IDENTITIES.json',dict(inputs=inputs,source_matches=source_match,official_raw_members=proofs))
    # Pure arithmetic on existing exact recorded funding quantities and marks.
    cases=[
      (2021,'STATIC50','coin_2021_strategy_comparison_20261013/state_first_authorized_run/Y2021_STATIC50_FINE_ORIGINAL'),
      (2021,'EXACTHALF','coin_2021_strategy_comparison_20261013/state_first_authorized_run/Y2021_EXACTHALF_FINE_ORIGINAL'),
      (2023,'STATIC50_FINE_ORIGINAL','coin_quantity_resolution_20261013/state_20261013/Y2023_STATIC50_FINE_ORIGINAL'),
      (2023,'COMBINED_FINE_ORIGINAL','coin_quantity_resolution_20261013/state_20261013/Y2023_COMBINED_FINE_ORIGINAL'),
      (2024,'EXACTHALF_FINE_ORIGINAL','coin_quantity_resolution_20261013/state_20261013/Y2024_EXACTHALF_FINE_ORIGINAL'),
      (2024,'STATIC50_FINE_GUARD50','coin_quantity_resolution_20261013/state_20261013/Y2024_STATIC50_FINE_GUARD50'),
      (2025,'STATIC50_FINE_ORIGINAL','coin_quantity_resolution_20261013/state_20261013/Y2025_STATIC50_FINE_ORIGINAL'),
      (2025,'COMBINED_FINE_ORIGINAL','coin_quantity_resolution_20261013/state_20261013/Y2025_COMBINED_FINE_ORIGINAL'),
    ]
    funding=[]
    with localcontext() as context:
        context.prec=60
        for year,arm,path in cases:
            account=json.loads((ROOT/path/'ACCOUNT.json').read_bytes());result=json.loads((ROOT/path/'RESULT.json').read_bytes());fs=account['funding']
            expected=events[year];assert len(fs)==len(expected)
            assert len({key(r) for r in fs})==len(fs) and len({r['event_id'] for r in fs})==len(fs)
            amounts=[];rawmatches=0;maxerr=D(0);sum_by_symbol={s:D(0) for s in S};nonowned=0;owned=0;rate_transform=set()
            for r in fs:
                assert key(r) in expected;q=expected[key(r)];assert r['raw_rate']==q['raw_rate'];assert r['reported_interval_hours']==q['reported_interval_hours'];rawmatches+=1
                amount=value(r,'signed_funding_USDT');amounts.append(amount);sum_by_symbol[r['symbol']]+=amount
                if r.get('owned'):
                    owned+=1;rate=value(r,'rate_fraction');assert rate==D(str(r['raw_rate']))
                    calc=-value(r,'quantity')*value(r,'mark_price')*rate;maxerr=max(maxerr,abs(calc-amount));assert abs(calc-amount)<D('1e-30')
                    assert int(r['mark_close_us'])<r['event_us'];assert float(r['conditional_rate_scale'])==1
                    rate_transform.add(str(r['conditional_rate_scale']))
                else:
                    nonowned+=1;assert amount==0
            total=sum(amounts,D(0));absolute=sum(map(abs,amounts),D(0));cum=D(0);cummin=D(0);cummax=D(0)
            for amount in amounts:cum+=amount;cummin=min(cummin,cum);cummax=max(cummax,cum)
            bridge=result['independent_decimal_NAV_bridge'];assert abs(total-D(bridge['funding_cash_USDT']))<D('1e-30')
            net=D(bridge['NAV'])-D(10000);g=D(bridge['gross_price_USDT']);execution=D(bridge['execution_USDT']);fees=D(bridge['fees_USDT']);assert abs(net-(g-execution-fees+total))<D('1e-28')
            delta=(D('.01')-1)*total
            funding.append(dict(year=year,arm=arm,inputs=[record(path+'/ACCOUNT.json'),record(path+'/RESULT.json')],events=len(fs),owned_events=owned,zero_owned_events=nonowned,duplicate_event_ids=0,source_rate_exact_matches=rawmatches,all_owned_rate_fraction_equals_raw_numeric=True,all_owned_interval_hours_preserved=True,maximum_signed_amount_equation_error_USDT=str(maxerr),recorded_signed_funding_cash_USDT=str(total),recorded_absolute_funding_USDT=str(absolute),signed_funding_by_symbol={s:str(v) for s,v in sum_by_symbol.items()},recorded_net_USDT=str(net),recorded_net_return_percentage=str(net/100),recorded_funding_drag_percentage_points=str(-total/100),fixed_tape_scale_point01_minus_scale1_cash_USDT=str(delta),fixed_tape_same_quantities_scale_point01_net_USDT=str(net+delta),fixed_tape_cash_difference_uniform_scale_in_point01_to1_interval_USDT=[str(min(D(0),delta)),str(max(D(0),delta))],fixed_tape_cumulative_funding_cash_min_USDT=str(cummin),fixed_tape_cumulative_funding_cash_max_USDT=str(cummax),eventwise_unit_independent_conservative_cash_difference_abs_bound_USDT=str(D('.99')*absolute),paid_flat=result.get('paid_flat'),full_calendar=result.get('full_calendar',False),status=result['status'],actual_strategy_counterfactual_return='NOT_COMPUTED_OR_BOUNDED_BY_THIS_FIXED_TAPE_ARITHMETIC; NAV cash-risk feedback, sizing, fills, costs, halts and terminal outcomes can change'))
            del account,result
    write('FIXED_TAPE_FUNDING_AUDIT.json',dict(cases=funding,formula='signed_cash=-recorded_owned_quantity*recorded_strict_prior_mark*raw_rate*scale; no hour factor',uniform_sensitivity_formula='fixed_tape_net(s)=recorded_net+(s-1)*recorded_signed_funding_cash',scope='Recorded tape identity and fee sensitivity only; no new wallet/targets/fits, no claim of counterfactual strategy returns or native venue certification'))
    write('RUN_RECEIPT.json',dict(status='PASS_READ_ONLY_SOURCE_IDENTITIES_AND_FIXED_TAPE_ARITHMETIC',seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,AS_limit_bytes=2*1024**3,CPU_affinity=list(os.sched_getaffinity(0)),new_provider_requests=0,new_wallets=0,new_fits=0,retained_2026_opened=0,Library_calls=0,old_files_mutated=0,outputs={n:record(str((OUT/n).relative_to(ROOT))) for n in ('SOURCE_IDENTITIES.json','FIXED_TAPE_FUNDING_AUDIT.json')}))
    print(json.dumps({'status':'PASS','official_archives':len(proofs),'official_raw_events':sum(x['raw_rows'] for x in proofs),'fee_tapes':len(funding),'seconds':time.monotonic()-start}))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args();ROOT=args.workspace_root.resolve();OUT=args.output.resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    main()
