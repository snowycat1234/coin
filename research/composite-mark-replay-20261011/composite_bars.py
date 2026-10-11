"""Checksum-bound union of originals, with per-minute owner and support sources."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from types import MappingProxyType
import numpy as np
import pandas as pd

NATIVE=Path(__file__).resolve().parents[1]/'native-mark-inputs-20261011'
sys.path.insert(0,str(NATIVE))
from mark_bars import DomainBars,source_identity,price_arrays,frozen,need,MINUTE


def manifest_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def descriptor(row):
    result={k:row[k] for k in ('symbol','family','month','source_period','frequency','ZIP_SHA256','ZIP_bytes','official_URL')}
    result['CHECKSUM_member_SHA256']=hashlib.sha256(row['official_checksum_text'].encode()).hexdigest()
    need(row.get('CHECKSUM_member_SHA256') in (None,result['CHECKSUM_member_SHA256']),'Bound original checksum text identity')
    return result


def source_rows(row,companions):
    if row.get('kind')=='DAILY_UNION':
        rows=list(row['daily_sources'])
    else:rows=[row]
    rows += list(companions)+row.get('new_daily_repairs',[])
    seen=set();result=[];duplicates=0
    for r in rows:
        key=manifest_sha(descriptor(r))
        if key in seen:duplicates+=1;continue
        seen.add(key);result.append(r)
    need(0<len(result)<=63,'Bounded original source collection')
    return result,duplicates


def decode_original(reader,row,left,right):
    from modules.collector_research.pipeline.download import check_zip,parse_checksum
    from modules.collector_research.pipeline.normalize import numeric_csv,validate_price
    raw,check=reader.read(row)
    stem=row['official_URL'].split('/')[-1]
    need(len(raw)==row['ZIP_bytes'] and hashlib.sha256(raw).hexdigest()==row['ZIP_SHA256']==parse_checksum(check.decode(),stem),
         'Original ZIP/checksum identity')
    need(hashlib.sha256(check).hexdigest()==descriptor(row)['CHECKSUM_member_SHA256'],'Independent original checksum body identity')
    p=reader.state/stem
    with p.open('xb') as f:f.write(raw)
    try:
        check_zip(p)
        return validate_price(numeric_csv(p),row['family'],left,right)
    finally:p.unlink()


def exact_union(frame,other,family,left,right):
    from modules.collector_research.pipeline.normalize import validate_price
    need(list(frame.columns)==list(other.columns),'Exact numeric source schema')
    common=frame[frame.timestamp_ms.isin(other.timestamp_ms)].reset_index(drop=True)
    matched=other[other.timestamp_ms.isin(common.timestamp_ms)].reset_index(drop=True)
    need(np.array_equal(common.to_numpy(),matched.to_numpy()),'Conflicting original numeric source overlap; hard stop')
    merged,dups=validate_price(pd.concat([frame,other],ignore_index=True),family,left,right)
    need(dups==len(common),'Exact identical-row deduplication')
    return merged,dict(common_rows=len(common),added_actual_rows=len(other)-len(common),all_numeric_fields_exact=True)


def composite_bars(reader,row,left,right,companions=(),decode=decode_original):
    family,symbol=row['family'],row['symbol'];rows,duplicate_sources=source_rows(row,companions)
    frames=[];receipts=[];result=None
    for r in rows:
        source_identity(r,family)
        need(r['symbol']==symbol and r['month']==row['month'],'Single domain/asset/month composite')
        if r['frequency']=='daily':
            stamp=datetime.strptime(r['source_period'],'%Y-%m-%d').replace(tzinfo=timezone.utc)
            a=int(stamp.timestamp())*1000;b=a+86400000
            need(left<=a<b<=right,'Daily original inside declared month')
        else:a,b=left,right
        frame,dups=decode(reader,r,a,b);frames.append(frame)
        if result is None:result=frame;overlap=dict(common_rows=0,added_actual_rows=len(frame),all_numeric_fields_exact=True)
        else:result,overlap=exact_union(result,frame,family,left,right)
        receipts.append(dict(source=descriptor(r),observed_rows=len(frame),identical_duplicates_in_original=dups,**overlap))
    clock=result.timestamp_ms.to_numpy(dtype=np.int64);owners=np.full(len(result),-1,dtype=np.int16);support=np.zeros(len(result),dtype=np.uint64)
    for index,frame in enumerate(frames):
        pos=np.searchsorted(clock,frame.timestamp_ms.to_numpy(dtype=np.int64))
        need(np.array_equal(clock[pos],frame.timestamp_ms.to_numpy()),'All observed originals represented')
        owners[pos[owners[pos]<0]]=index
        support[pos] |= np.uint64(1)<<np.uint64(index)
    need(np.all(owners>=0) and np.all(support>0),'Every observed minute has source proof')
    missing=np.setdiff1d(np.arange(left,right,60000,dtype=np.int64),clock)
    manifest=dict(kind='COMPOSITE_ORIGINAL_PRICE_SOURCES',symbol=symbol,family=family,month=row['month'],
        interval_open_ms=[left,right],originals=[descriptor(r) for r in rows],union_rule='ALL_NUMERIC_FIELDS_EXACT_DEDUP_NO_IMPUTATION')
    identity=manifest_sha(manifest)
    provenance=MappingProxyType(dict(kind=manifest['kind'],manifest_json=json.dumps(manifest,sort_keys=True,separators=(',',':')),manifest_SHA256=identity,
        minute_owner_index=frozen(owners),minute_support_bits=frozen(support),missing_open_ms=frozen(missing),
        receipts=tuple(receipts),identical_source_references_removed=duplicate_sources))
    bars=DomainBars(symbol,family,identity,None,*price_arrays(result,family),provenance)
    return bars,result


def minute_observation(bars,open_us,known_at_us):
    need(type(open_us) is int and open_us%MINUTE==0,'Explicit expected minute clock')
    completion=open_us+MINUTE
    if known_at_us<completion:return dict(status='NOT_YET_KNOWN',known_at_us=known_at_us)
    i=int(np.searchsorted(bars.open_us,open_us))
    if i==len(bars.open_us) or bars.open_us[i]!=open_us:
        return dict(status='SOURCE_MISSING_AT_COMPLETION',available_us=completion,
            price=None,source_owner=None,path_certifiable=False,action='STOP_OR_UNCERTIFIABLE; retain prior holdings and ledger')
    return dict(status='OBSERVED_COMPLETED_MINUTE',available_us=int(bars.available_us[i]),
        price=float(bars.values['close'][i]),source_owner=int(bars.provenance['minute_owner_index'][i]),
        support_bits=int(bars.provenance['minute_support_bits'][i]))
