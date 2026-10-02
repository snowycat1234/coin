"""One July-only metadata and small archive check; no model or execution adapter."""
import csv,datetime,hashlib,io,json,sys,time,urllib.error,urllib.request,zipfile
from pathlib import Path
from quant import disk,resources
from quant.paths import ROOT,STATE
sys.path.insert(0,str(ROOT/'scripts/research_v7'))
from oracle_flow_ceiling import Progress

OUT=STATE/'v7-venue-economic-metadata-20261002-v1'
OUT.mkdir(exist_ok=False)
MONTH='2025-07';START=1751328000000;END=1754006400000
progress=Progress();receipts=[];downloaded=0
def sha(body):return hashlib.sha256(body).hexdigest()
def get(url,name,limit=4_000_000):
    global downloaded
    begin=time.monotonic()
    record={'url':url,'name':name,'requested_utc':datetime.datetime.now(datetime.UTC).isoformat(),'request_method':'GET','credentials_used':False}
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'coin-v7-personal-research-public-metadata/1.0'})
        with urllib.request.urlopen(request,timeout=20) as response:
            body=response.read(limit+1)
            assert len(body)<=limit,'bounded response budget'
            record.update(http_status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'),content_length=response.headers.get('Content-Length'),etag=response.headers.get('ETag'))
    except urllib.error.HTTPError as error:
        body=error.read(min(limit,4096));record.update(http_status=error.code,error='HTTPError')
    except (urllib.error.URLError,TimeoutError,OSError) as error:
        body=str(error).encode();record.update(http_status=None,error=type(error).__name__)
    path=OUT/name;path.write_bytes(body);downloaded+=len(body)
    assert downloaded<=100_000_000
    record.update(saved_path=str(path),sha256=sha(body),bytes=len(body),elapsed_seconds=time.monotonic()-begin)
    receipts.append(record)
    progress.update('官方 venue metadata / 小月档核验',len(receipts),22,'HTTP 请求',实际下载字节=downloaded)
    return record,body

try:
    ledger=disk.check(reserve=1_100_000_000)
    ledger['measured_utc']=datetime.datetime.now(datetime.UTC).isoformat()
    (OUT/'DISK_LEDGER.json').write_text(json.dumps(ledger,indent=2))
    archives=[]
    for symbol in ['BTCUSDT','ETHUSDT']:
        for data_type in ['fundingRate','markPriceKlines','indexPriceKlines']:
            interval='' if data_type=='fundingRate' else '1m'
            name=f'{symbol}-{data_type}-'+(interval+'-' if interval else '')+MONTH+'.zip'
            url=f'https://data.binance.vision/data/futures/um/monthly/{data_type}/{symbol}/'+(interval+'/' if interval else '')+name
            check,body=get(url+'.CHECKSUM',name+'.CHECKSUM',4096)
            item={'symbol':symbol,'data_type':data_type,'interval':interval or None,'month':MONTH,'checksum_http_status':check['http_status'],'checksum_url':url+'.CHECKSUM','zip_url':url}
            if check['http_status']==200:
                words=body.decode().strip().split()
                assert len(words)==2 and words[1].lstrip('*')==name and len(words[0])==64
                zrec,zbytes=get(url,name,4_000_000)
                item.update(zip_http_status=zrec['http_status'],checksum_declared_zip_sha256=words[0])
                if zrec['http_status']==200:
                    assert sha(zbytes)==words[0]
                    with zipfile.ZipFile(io.BytesIO(zbytes)) as archive:
                        assert archive.namelist()==[name[:-4]+'.csv']
                        member=archive.infolist()[0]
                        assert member.file_size<15_000_000
                        with archive.open(member) as stream:
                            rows=csv.reader(io.TextIOWrapper(stream,encoding='utf-8-sig',newline=''))
                            first=next(rows)
                            header=first if not first[0].replace('.','',1).isdigit() else None
                            times=[];funding=[];intervals=[]
                            values=rows if header else iter([first,*rows])
                            for row in values:
                                stamp=int(float(row[0]));assert START<=stamp<END
                                times.append(stamp)
                                if data_type=='fundingRate':
                                    assert header and header==['calc_time','funding_interval_hours','last_funding_rate']
                                    intervals.append(int(row[1]));funding.append(float(row[2]))
                            assert times and times==sorted(set(times))
                            if interval:assert len(times)==44640 and times[0]==START and times[-1]==END-60_000 and all(b-a==60000 for a,b in zip(times,times[1:]))
                    item.update(checksum_verified=True,zip_sha256=sha(zbytes),zip_bytes=len(zbytes),csv_uncompressed_bytes=member.file_size,csv_header=header,csv_columns=len(first),rows=len(times),timestamp_unit='milliseconds',first_timestamp_ms=times[0],last_timestamp_ms=times[-1])
                    if funding:
                        item.update(funding_interval_hours=sorted(set(intervals)),funding_rate_bps_min=min(funding)*10000,funding_rate_bps_max=max(funding)*10000,positive_events=sum(v>0 for v in funding),negative_events=sum(v<0 for v in funding),zero_events=sum(v==0 for v in funding),archive_funding_values=[{'fundingTime':t,'fundingRate':f} for t,f in zip(times,funding)])
            archives.append(item)
    api=[]
    for symbol in ['BTCUSDT','ETHUSDT']:
        url=f'https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&startTime={START}&endTime={END-1}&limit=1000'
        rec,body=get(url,f'{symbol}-REST-July-funding.json',200_000)
        item={'symbol':symbol,'kind':'fundingRate','http_status':rec['http_status'],'url':url}
        if rec['http_status']==200:
            rows=json.loads(body);assert isinstance(rows,list) and rows and len(rows)<=1000
            assert all(v['symbol']==symbol and START<=int(v['fundingTime'])<END for v in rows)
            values=[{'fundingTime':int(v['fundingTime']),'fundingRate':float(v['fundingRate'])} for v in rows]
            previous=next(a for a in archives if a['symbol']==symbol and a['data_type']=='fundingRate')
            item.update(rows=len(rows),response_fields=sorted(rows[0]),archive_rest_values_equal=values==previous.get('archive_funding_values'),mark_price_at_funding_in_response=all('markPrice' in v for v in rows))
        api.append(item)
    for endpoint in ['fundingInfo','exchangeInfo']:
        url='https://fapi.binance.com/fapi/v1/'+endpoint
        rec,body=get(url,'REST-'+endpoint+'.json',2_000_000)
        item={'kind':endpoint,'http_status':rec['http_status'],'url':url}
        if rec['http_status']==200:
            value=json.loads(body);entries=value if endpoint=='fundingInfo' else value['symbols']
            item['BTC_ETH_metadata']=[v for v in entries if v.get('symbol') in ['BTCUSDT','ETHUSDT']]
            item['scope']='current public metadata; not historical margins or fees'
        api.append(item)
    for name,url in [('spot-fee-public.html','https://www.binance.com/en/fee/trading'),('usdm-fee-public.html','https://www.binance.com/en/fee/futureFee'),('usdm-fee-FAQ.html','https://www.binance.com/en/support/faq/detail/360033544231'),('funding-FAQ.html','https://www.binance.com/en/support/faq/detail/360033525031'),('liquidation-FAQ.html','https://www.binance.com/en/support/faq/detail/360033525271'),('official-pinned-README.md','https://raw.githubusercontent.com/binance/binance-public-data/f446ce3812bd4e5521f21faecd4ae3c6460e49fc/README.md')]:
        get(url,name,2_000_000)
    for item in archives:item.pop('archive_funding_values',None)
    report={'status':'V7_JULY_VENUE_METADATA_AND_SMALL_ARCHIVE_AVAILABILITY_CHECK_COMPLETE','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'run_dir':str(OUT),'script_sha256':sha(Path(__file__).read_bytes()),'registry_sha256':sha((ROOT/'docs/OPEN_SOURCE_REGISTRY.md').read_bytes()),'official_repo':'https://github.com/binance/binance-public-data','registered_commit':'f446ce3812bd4e5521f21faecd4ae3c6460e49fc','disk':ledger,'archives':archives,'public_api':api,'http_receipts':receipts,'actual_downloaded_response_bytes':downloaded,'bound_download_bytes':100_000_000,'bound_individual_response_bytes':4_000_000,'shared_resources':resources.status(),'market_sample_scope':'Only July 2025 already-inspected development; metadata and funding/mark/index availability only','unseen_or_locked_labels_read':False,'models_fitted':0,'account_keys_used':False,'orders_sent':0,'original_sources_or_evidence_modified':False,'gpu_used':False,'fee_rate_table_current_usdm_applicability_verified':False,'historical_2025_account_fees_verified':False,'funding_api_may_be_unavailable':True,'executable_BBO_or_liquidation_simulator_available':False}
    target=ROOT/'reports/fast_research/V7_VENUE_METADATA_AVAILABILITY_20261002_V1.json'
    with target.open('x') as f:json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
    print(json.dumps({'status':report['status'],'report':str(target),'downloaded_bytes':downloaded,'archives_verified':sum(a.get('checksum_verified',False) for a in archives)},ensure_ascii=False),flush=True)
finally:
    progress.stop.set();progress.thread.join(timeout=3)
