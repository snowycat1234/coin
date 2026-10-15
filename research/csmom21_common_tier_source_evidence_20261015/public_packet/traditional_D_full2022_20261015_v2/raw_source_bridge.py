"""Future source-stage-only raw ZIP normalizer. No network and no body I/O at import.

Raw index/QA/pins are the final source worker's declared metadata contract.
Only exact original monthly/daily CSVs may contribute genuine observations.
"""
from datetime import datetime,timezone
from io import BytesIO,StringIO
import csv,json,math,stat,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
import full_source as s

DAILY_PATH='full2022_source_metadata_plan_20261015/source_only_projections/DAILY_CLOSE_SOURCE_ONLY.npz'
DAILY_SHA='ae81b8c2ec4f40d889ae82757bdd72f5b4c04afadd72467366e1f10371801887'
FUNDING_PATH='full2022_source_metadata_plan_20261015/source_only_projections/RAW_RATE_INTERVAL_EVENTS.json'
FUNDING_SHA='4a6d644c0339facf4cc4e8607fc1379acb06c1f52c162af6cab739b4670b7c99'


def source_path(name):
    if type(name) is not str:raise ValueError('EXACT_WORKSPACE_RELATIVE_SOURCE_PATH_REQUIRED')
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or str(p)!=name or '\\' in name:raise ValueError('EXACT_WORKSPACE_RELATIVE_SOURCE_PATH_REQUIRED')
    return s.ROOT/name


def parse_original_zip(raw,*,symbol,period,family):
    """Pure parser used by fake ZIP tests and the independently gated bridge."""
    if symbol not in s.S or family not in ('klines','markPriceKlines'):raise ValueError('EXACT_CORE5_SOURCE_FAMILY_REQUIRED')
    start=datetime.fromisoformat(period+('-01' if len(period)==7 else '')).replace(tzinfo=timezone.utc)
    if start.year!=2022:raise ValueError('ONLY2022_NATIVE_SOURCE_ALLOWED')
    if len(period)==7:end=start.replace(year=2023,month=1) if start.month==12 else start.replace(month=start.month+1)
    else:
        from datetime import timedelta
        end=start+timedelta(days=1)
    left,right=int(start.timestamp()*1e6),int(end.timestamp()*1e6)
    with zipfile.ZipFile(BytesIO(raw)) as z:
        infos=z.infolist();expected=f'{symbol}-1m-{period}.csv'
        if len(infos)!=1 or infos[0].filename!=expected or infos[0].flag_bits&1 or stat.S_ISLNK(infos[0].external_attr>>16):raise ValueError('EXACT_SINGLE_ORIGINAL_CSV_MEMBER_REQUIRED')
        text=z.read(infos[0]).decode('utf-8-sig')
    rows={};header=False
    for index,row in enumerate(csv.reader(StringIO(text))):
        if len(row)!=12:raise ValueError('EXACT_ORIGINAL_TWELVE_SOURCE_COLUMNS_REQUIRED')
        if index==0 and not row[0].isdigit():
            if row[0] not in {'open_time','open_time_ms','open_timestamp'}:raise ValueError('EXACT_RECOGNIZED_SOURCE_HEADER_REQUIRED')
            header=True;continue
        if not row[0].isdigit() or not row[6].isdigit():raise ValueError('INTEGER_ORIGINAL_SOURCE_CLOCK_REQUIRED')
        opened=int(row[0])*1000
        if opened%s.MINUTE or not left<=opened<right or int(row[6])*1000+1000!=opened+s.MINUTE:raise ValueError('EXACT_RAW_OPEN_INCLUSIVE_CLOSE_MAPPING_REQUIRED')
        values=tuple(float(row[k]) for k in (1,2,3,4,5,7))
        if any(not math.isfinite(x) for x in values) or any(values[k]<=0 for k in range(4)) or values[4]<0 or values[5]<0 or values[1]<max(values[0],values[3],values[2]) or values[2]>min(values[0],values[3],values[1]):raise ValueError('FINITE_GENUINE_SOURCE_OHLCV_REQUIRED')
        if opened in rows and rows[opened]!=tuple(row):raise ValueError('CONFLICTING_DUPLICATE_ORIGINAL_SOURCE_ROW')
        rows[opened]=tuple(row)
    return rows,dict(CSV_member=expected,CSV_SHA256=s.sha(text.encode()),observed_minutes=len(rows),header_present=header)


def _pins(raw):
    v=json.loads(raw)
    container=v.get('files',v.get('artifacts'))
    if type(container) is dict:return container
    if type(container) is list:return {r['path']:dict(SHA256=r['SHA256'],bytes=r['bytes']) for r in container}
    raise ValueError('EXACT_FINAL_SOURCE_FILE_PIN_CONTAINER_REQUIRED')


def capture_and_normalize(root,*,source_authorization_raw,expected_source_authorization_sha256):
    # Completion/index/QA are metadata. All actual price bodies remain behind
    # exact source-only root authorization plus current adapter code identity.
    s.require_source_stage_authority(source_authorization_raw,expected_source_authorization_sha256)
    root=Path(root).resolve();pinraw=s.exact(root/'FINAL_DELIVERABLE_PINS.json',s.FINAL_PINS);pins=_pins(pinraw)
    def metadata(name):
        possible=(name,str((root/name).relative_to(s.ROOT)))
        key=next((k for k in possible if k in pins),None)
        if key is None:raise ValueError('EXACT_FINAL_INDEX_OR_QUALIFIER_PIN_REQUIRED')
        pin=pins[key];return s.exact(root/name,pin['SHA256'],pin['bytes'])
    indexraw=metadata('FINAL_RAW_SOURCE_INDEX.json');qraw=metadata('FINAL_SOURCE_QUALIFICATION_RECEIPT.json')
    scope=s.admit_actual_source_stage(qraw,source_authorization_raw,expected_source_authorization_sha256)
    index=json.loads(indexraw);qa=json.loads(qraw)
    if qa.get('status')!='PASS_RAW_SOURCE_RESTORE_WITH_27_UNKNOWN_MARK_MINUTES':raise ValueError('EXACT_COMPLETE_RAW_SOURCE_RESTORE_STATUS_REQUIRED')
    expected_identity=s.jsha(dict(raw_index_SHA256=s.sha(indexraw),raw_qualification_SHA256=s.sha(qraw),daily_projection_SHA256=DAILY_SHA,funding_projection_SHA256=FUNDING_SHA,allowlist_SHA256=s.ACTUAL_ALLOWLIST_SHA256))
    if scope.qualification.source_identity!=expected_identity:raise ValueError('EXACT_RAW_SOURCE_AND_PROJECTION_IDENTITY_REQUIRED')
    if index.get('schema')!='FULL2022_RAW_SOURCE_INDEX_V1' or len(index.get('monthly',[]))!=120 or len(index.get('daily',[]))!=16:raise ValueError('EXACT120_MONTHLY16_DAILY_RAW_SOURCE_INDEX_REQUIRED')
    monthly=index['monthly'];daily=index['daily'];allitems=monthly+daily
    key=lambda r:(r['family'],r['symbol'],r['period'])
    if len({key(r) for r in monthly})!=120 or len({key(r) for r in daily})!=16:raise ValueError('UNIQUE_ORIGINAL_RAW_SOURCE_STREAMS_REQUIRED')
    qmap={key(r):r for r in qa['monthly']+qa['daily']}
    # Preserve exact original ZIP/checksum objects in captured source bindings.
    bodies={};filepins={};owner={};total_added=0
    for rec in allitems:
        path=source_path(rec['source_path']);raw=s.exact(path,rec['ZIP_SHA256'],rec['ZIP_bytes']);name=str(path.relative_to(s.ROOT))
        bodies[name]=raw;filepins[name]=dict(SHA256=s.sha(raw),bytes=len(raw))
        if rec.get('CHECKSUM_path') is not None:
            cp=source_path(rec['CHECKSUM_path']);cb=s.exact(cp,rec['CHECKSUM_SHA256'],rec['CHECKSUM_bytes'])
            if cb.decode('ascii').split()[0]!=s.sha(raw):raise ValueError('ORIGINAL_OFFICIAL_CHECKSUM_MISMATCH')
            cn=str(cp.relative_to(s.ROOT));bodies[cn]=cb;filepins[cn]=dict(SHA256=s.sha(cb),bytes=len(cb))
        owner[key(rec)]=rec
    def parse_rows(rec):
        raw=bodies[rec['source_path']]
        rows,p=parse_original_zip(raw,symbol=rec['symbol'],period=rec['period'],family=rec['family']);qr=qmap[key(rec)]
        if p['CSV_member']!=qr['CSV_member'] or s.sha(raw)!=qr['ZIP_SHA256'] or len(rows)!=qr['observed_minutes']:
            raise ValueError('ORIGINAL_RAW_PARSER_QUALIFIER_PARITY_REQUIRED')
        return rows
    if sum(r['ZIP_bytes'] for r in monthly)!=158411229:raise ValueError('EXACT_ORIGINAL_MONTHLY_ZIP_BYTE_TOTAL_REQUIRED')
    source_files=dict(filepins)
    for name,blob in ((str((root/'FINAL_RAW_SOURCE_INDEX.json').relative_to(s.ROOT)),indexraw),(str((root/'FINAL_SOURCE_QUALIFICATION_RECEIPT.json').relative_to(s.ROOT)),qraw),(str((root/'FINAL_DELIVERABLE_PINS.json').relative_to(s.ROOT)),pinraw)):
        source_files[name]=dict(SHA256=s.sha(blob),bytes=len(blob))
    source_files[DAILY_PATH]=dict(SHA256=DAILY_SHA,bytes=16950);source_files[FUNDING_PATH]=dict(SHA256=FUNDING_SHA,bytes=724500)
    arrays=[];anchors={};missing=[];dailyclose={}
    for month in range(1,13):
        period=f'2022-{month:02}';left=int(datetime(2022,month,1,tzinfo=timezone.utc).timestamp()*1e6)
        right=s.END if month==12 else int(datetime(2022,month+1,1,tzinfo=timezone.utc).timestamp()*1e6)
        times=np.arange(left,right,s.MINUTE,dtype=np.int64);a=dict(times=times,available_us=times+s.MINUTE)
        for symbol in s.S:
            for family in ('klines','markPriceKlines'):
                k=(family,symbol,period);original=parse_rows(owner[k]);union=dict(original);origins={at:owner[k] for at in original};qr=qmap[k]
                original_missing=set(range(left,right,s.MINUTE))-set(original)
                if original_missing!={int(at)*1000 for at in qr['missing_open_ms']}:raise ValueError('EXACT_ORIGINAL_MISSING_OPEN_MASK_REQUIRED')
                for dr in daily:
                    if dr['family']!=family or dr['symbol']!=symbol or dr['month']!=period:continue
                    if dr.get('priority')!='ONLY_FILL_ORIGINALLY_ABSENT_CLOCKS':raise ValueError('GENUINE_REPAIR_ONLY_ORIGINAL_ABSENCE_PRIORITY_REQUIRED')
                    added=0
                    for at,row in parse_rows(dr).items():
                        if at not in original_missing:continue
                        if at in union and union[at]!=row:raise ValueError('CONFLICTING_GENUINE_REPAIR_SOURCE')
                        if at not in union:union[at]=row;origins[at]=dr;added+=1
                    if added!=dr['expected_genuine_added_asset_minutes']:raise ValueError('EXACT_GENUINE_DAILY_ADDED_MINUTES_REQUIRED')
                    total_added+=added
                absent=set(range(left,right,s.MINUTE))-set(union)
                if absent!={int(at)*1000 for at in qr['union_missing_open_ms']}:raise ValueError('EXACT_UNION_SOURCE_ABSENCE_MASK_REQUIRED')
                if family=='klines' and absent:raise ValueError('NO_NATIVE_TRADE_GAPS_ADMITTED')
                if family=='klines':
                    for field,column in (('open',1),('close',4),('quote_volume',7)):
                        a[symbol+'_'+field]=np.asarray([float(union[int(at)][column]) for at in times],dtype=np.float64)
                else:
                    a[symbol+'_mark']=np.asarray([float(union[int(at)][4]) if int(at) in union else np.nan for at in times],dtype=np.float64)
                    for at in sorted(absent):
                        missing.append((symbol,at));prior=max((v for v in union if v<at),default=None)
                        if prior is None:raise ValueError('NO_PRIOR_GENUINE_NATIVE_MARK_ANCHOR')
                        r=origins[prior];anchors[(symbol,prior)]=dict(symbol=symbol,minute_open_us=prior,completed_us=prior+s.MINUTE,
                            available_us=prior+s.MINUTE,installed_us=prior+s.MINUTE,price_text=union[prior][4],source_SHA256=r['ZIP_SHA256'],
                            record_id=r['CSV_member']+':OPEN_MS:'+str(prior//1000))
        memory=BytesIO();np.savez_compressed(memory,**a);name=f'normalized_months/{period}.npz';blob=memory.getvalue();bodies[name]=blob;filepins[name]=dict(SHA256=s.sha(blob),bytes=len(blob))
        arrays.append(dict(month=period,start_us=left,minutes=len(times),file=name))
    if total_added!=23040 or tuple(sorted(missing))!=tuple(sorted(s.ACTUAL27_OPEN_POINTS_US)):raise ValueError('EXACT16_GENUINE_DAILY_REPAIRS_AND27_MARK_HOLES_REQUIRED')
    # Raw source arrival is unknown; these are explicitly nominal completion
    # clocks under the reviewed replay convention, never venue-arrival proof.
    anchorraw=s.canonical(list(anchors.values()));bodies['MARK_ANCHORS.json']=anchorraw;filepins['MARK_ANCHORS.json']=dict(SHA256=s.sha(anchorraw),bytes=len(anchorraw))
    dailyraw=s.exact(source_path(DAILY_PATH),DAILY_SHA,16950);fundraw=s.exact(source_path(FUNDING_PATH),FUNDING_SHA,724500)
    # The final projection includes source-event annotations. The execution
    # projection removes all optional/archived fields before native finance.
    events=json.loads(fundraw);events=[dict(symbol=r['symbol'],event_us=r['calc_time_ms']*1000,raw_rate=r['raw_rate'],reported_interval_hours=r['reported_interval_hours'],raw_rate_unit='UNCONFIRMED') for r in events]
    funding=s.canonical(events);bodies['RAW_EVENTS.json']=funding;filepins['RAW_EVENTS.json']=dict(SHA256=s.sha(funding),bytes=len(funding))
    bodies['DAILY_PROJECTION.npz']=dailyraw;filepins['DAILY_PROJECTION.npz']=dict(SHA256=DAILY_SHA,bytes=len(dailyraw))
    bodies['RAW_QUALIFICATION.json']=qraw;filepins['RAW_QUALIFICATION.json']=dict(SHA256=s.sha(qraw),bytes=len(qraw))
    for name in source_files:bodies.pop(name,None)
    transport=dict(schema='FULL2022_CAPTURED_SOURCE_TRANSPORT_V1',source_identity=scope.qualification.source_identity,
        files=filepins,source_files=source_files,qualification_file='RAW_QUALIFICATION.json',mark_anchor_file='MARK_ANCHORS.json',daily_projection_file='DAILY_PROJECTION.npz',funding_file='RAW_EVENTS.json',months=arrays)
    return transport,bodies,scope
