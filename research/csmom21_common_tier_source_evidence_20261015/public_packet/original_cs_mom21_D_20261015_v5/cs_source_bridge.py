"""New-CS-only 2022 source capture, with unchanged original parser semantics.

Import does no source-body I/O. Pure byte/array helpers have no file/provider API.
Actual capture accepts only the new CS sealed SourcePreparationScope. It never
mints source/history authority or constructs/iterates an execution provider.
The twelve normalized months remain memory-only on the first-six path. All old
container hashes and source-to-serialized numeric bits are checked before return.
"""
from datetime import datetime, timezone
from io import BytesIO, StringIO
import csv
import json
import math
from pathlib import Path, PurePosixPath
import stat
from types import SimpleNamespace
import zipfile

import numpy as np
import cs_common as c

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE_ROOT = ROOT / 'full2022_unaffected_source_restore_20261015'
S = ('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
MINUTE = 60_000_000
START = 1640995200000000
END = 1672531200000000
FINAL_PINS_SHA256 = 'b10686c8f84d3aa111d48763612b0433c2469ca605e15f4910b80a39cee6d9d5'
RAW_INDEX_SHA256 = 'ab57ebc72f05ac0e59df232b477de27f8674b34aca0667168b4c69c40ab065ab'
QUALIFICATION_SHA256 = '36310f40bddad0c6de5482085ba8fc0c81571060f7dda5da6deb62125fa1c5ec'
SOURCE_IDENTITY = '1d5fc1db1ee3fd95746f29d267ea7d7c3edac616d5a8f0bee1320f6ee786da2f'
ALLOWLIST_SHA256 = '55e87de1c4b238ab907d57c950de2eedc1a2ec245e8b6e0fe57cd2efe07c0f71'
DAILY_PATH = 'full2022_source_metadata_plan_20261015/source_only_projections/DAILY_CLOSE_SOURCE_ONLY.npz'
DAILY_SHA = 'ae81b8c2ec4f40d889ae82757bdd72f5b4c04afadd72467366e1f10371801887'
FUNDING_PATH = 'full2022_source_metadata_plan_20261015/source_only_projections/RAW_RATE_INTERVAL_EVENTS.json'
FUNDING_SHA = '4a6d644c0339facf4cc4e8607fc1379acb06c1f52c162af6cab739b4670b7c99'
ACTUAL27_OPEN_POINTS_US = (('DOGEUSDT', 1657631820000000), ('DOGEUSDT', 1657631880000000), ('DOGEUSDT', 1657631940000000), ('DOGEUSDT', 1657632000000000), ('DOGEUSDT', 1657632060000000), ('ETHUSDT', 1657630620000000), ('ETHUSDT', 1657631220000000), ('ETHUSDT', 1657631700000000), ('ETHUSDT', 1657631760000000), ('ETHUSDT', 1657631820000000), ('ETHUSDT', 1657631880000000), ('ETHUSDT', 1657631940000000), ('ETHUSDT', 1657632000000000), ('ETHUSDT', 1657632060000000), ('ETHUSDT', 1657633920000000), ('ETHUSDT', 1657695540000000), ('SOLUSDT', 1657631760000000), ('SOLUSDT', 1657631820000000), ('SOLUSDT', 1657631880000000), ('SOLUSDT', 1657631940000000), ('SOLUSDT', 1657632000000000), ('SOLUSDT', 1657632060000000), ('XRPUSDT', 1657631820000000), ('XRPUSDT', 1657631880000000), ('XRPUSDT', 1657631940000000), ('XRPUSDT', 1657632000000000), ('XRPUSDT', 1657632060000000))
OLD_NORMALIZED_MONTH_PINS = (('normalized_months/2022-01.npz', 1640995200000000, 44640, '2d9b13255281e50ccfdb1f095311acf21cdd43c2304c1ac57ec61a55f56dd771', 4065603, 0, 44640), ('normalized_months/2022-02.npz', 1643673600000000, 40320, 'c753c43d60e8b9c035665629cb22bf60adc30a14b0611082c7badfc6243b9ee2', 3604642, 0, 40320), ('normalized_months/2022-03.npz', 1646092800000000, 44640, 'c9949d105ab7d217444c3f76fa12855c961632447f329e3e5ef329d4eb049f87', 3913246, 0, 44640), ('normalized_months/2022-04.npz', 1648771200000000, 43200, '159bc87006fcfec1903c3c172edf4da784edb67445c15307ab2644bbf3ea0726', 3797733, 0, 43200), ('normalized_months/2022-05.npz', 1651363200000000, 44640, '2660b15d7761a2f322ba560406b636d6b89266e0d880b451b652fac1b345f11f', 3852995, 0, 44640), ('normalized_months/2022-06.npz', 1654041600000000, 43200, '128e75dad845231fb8acbbba9a5d480281655a1e8186b8fd44905962305b5311', 3679353, 0, 43200), ('normalized_months/2022-07.npz', 1656633600000000, 44640, 'b8fae41f84e957b3d636681cb1161afa0a72cc85fc1744c8f39ad1fd16c2bf5d', 3721698, 0, 44640), ('normalized_months/2022-08.npz', 1659312000000000, 44640, '9dd75372c9915421375e85437fdfcb8985e4a72e6e159b6407c3b6c2ef62e581', 3674739, 0, 44640), ('normalized_months/2022-09.npz', 1661990400000000, 43200, 'b79bf546ff05211e6ca3f8104319e0756f6efe383810d9a2410f305643c334e5', 3519482, 0, 43200), ('normalized_months/2022-10.npz', 1664582400000000, 44640, '74550b445a6b60f49047f50b3432b7be39058348dccc25a470becfdb3bc63e0b', 3595945, 0, 44640), ('normalized_months/2022-11.npz', 1667260800000000, 43200, '807e17b7d664be61fb9146e76a21bdc74da24c9fd81974806e2386f8409de1b9', 3732607, 0, 43200), ('normalized_months/2022-12.npz', 1669852800000000, 44640, 'e317348fe9c181eec0055b627fae28f4cad54b9106d0f0b7a9df6e5e432b3438', 3628258, 0, 44640))
# Local constant-only namespace preserves selected parser/normalizer AST.
# It contains no callable source reader, authority factory, or scope validator.
s = SimpleNamespace(S=S, ROOT=ROOT, MINUTE=MINUTE, START=START, END=END,
    sha=c.sha, jsha=c.jsha, canonical=c.canonical,
    ACTUAL27_OPEN_POINTS_US=ACTUAL27_OPEN_POINTS_US,
    ACTUAL_ALLOWLIST_SHA256=ALLOWLIST_SHA256)


def source_path(name):
    return ROOT / c.relative(name)


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


def verify_normalized_numeric_bits(raw, source_arrays):
    """Pure no-I/O container round-trip witness, including exact NaN payloads."""
    if type(raw) is not bytes or type(source_arrays) is not dict:
        raise ValueError('EXACT_NORMALIZED_BYTES_AND_SOURCE_ARRAY_DICT_REQUIRED')
    needed = {'times', 'available_us'} | {symbol + '_' + key for symbol in S
        for key in ('open', 'close', 'quote_volume', 'mark')}
    if set(source_arrays) != needed:
        raise ValueError('EXACT_22_ORIGINAL_NORMALIZED_ARRAYS_REQUIRED')
    count = source_arrays['times'].shape[0]
    if type(count) is not int or not 0 < count <= 44640:
        raise ValueError('BOUNDED_NATIVE_MONTH_REQUIRED')
    with np.load(BytesIO(raw), allow_pickle=False) as arrays:
        if len(arrays.files) != len(needed) or set(arrays.files) != needed:
            raise ValueError('EXACT_ORIGINAL_NORMALIZED_MEMBER_NAMESPACE_REQUIRED')
        identities = {}
        for key in sorted(needed):
            want = source_arrays[key]
            dtype = np.dtype('int64' if key in ('times', 'available_us') else 'float64')
            if (type(want) is not np.ndarray or want.dtype != dtype or want.shape != (count,)
                    or not want.flags.c_contiguous):
                raise ValueError('EXACT_SOURCE_ARRAY_SCHEMA_REQUIRED')
            got = arrays[key]
            if got.dtype != want.dtype or got.shape != want.shape or got.tobytes() != want.tobytes():
                raise ValueError('ORIGINAL_NATIVE_MONTH_NUMERIC_BITS_CHANGED')
            identities[key] = dict(dtype=want.dtype.str, shape=list(want.shape),
                raw_SHA256=c.sha(want.tobytes()))
    return identities


def _require_source_scope(source_scope, root):
    # No caller-provided validator, generated flag, old-D class, or old GO.
    # Reject ordinary missing/duck-typed objects even before importing the entry.
    if type(source_scope).__name__ != 'SourcePreparationScope':
        raise ValueError('EXACT_NEW_CS_SEALED_SOURCE_SCOPE_REQUIRED')
    import cs_entry
    if Path(cs_entry.__file__).resolve() != HERE / 'cs_entry.py':
        raise ValueError('EXACT_NEW_CS_ENTRY_MODULE_REQUIRED')
    if type(source_scope) is not cs_entry.SourcePreparationScope:
        raise ValueError('EXACT_NEW_CS_SEALED_SOURCE_SCOPE_REQUIRED')
    if source_scope.validate_current(year=2022) is not True:
        raise ValueError('CURRENT_NEW_CS_SOURCE_AUTHORITY_REQUIRED')
    root = Path(root)
    if root.is_symlink() or any(parent.is_symlink() for parent in root.parents):
        raise ValueError('ORDINARY_BOUND_2022_SOURCE_ROOT_REQUIRED')
    root = root.resolve()
    if root != Path(source_scope.source_root(2022)).resolve() or root != SOURCE_ROOT:
        raise ValueError('EXACT_SCOPE_BOUND_2022_SOURCE_ROOT_REQUIRED')
    if source_scope.qualification_for(2022).source_identity != SOURCE_IDENTITY:
        raise ValueError('EXACT_QUALIFIED_2022_SOURCE_IDENTITY_REQUIRED')
    return root


def capture_2022(root, *, source_scope):
    """Future admitted SOURCE stage only; no provider or financial code imports."""
    root = _require_source_scope(source_scope, root)
    def read(path, expected, size=None):
        # Scope compares name/hash/size against its immutable qualified lineage.
        name = str(Path(path).relative_to(ROOT))
        return source_scope.read_source(2022, name, expected, size)
    pinraw = read(root / 'FINAL_DELIVERABLE_PINS.json', FINAL_PINS_SHA256, 77473)
    pins = _pins(pinraw)
    def metadata(name):
        possible = (name, str((root / name).relative_to(ROOT)))
        key = next((key for key in possible if key in pins), None)
        if key is None:
            raise ValueError('EXACT_FINAL_INDEX_OR_QUALIFIER_PIN_REQUIRED')
        pin = pins[key]
        return read(root / name, pin['SHA256'], pin['bytes'])
    indexraw = metadata('FINAL_RAW_SOURCE_INDEX.json')
    qraw = metadata('FINAL_SOURCE_QUALIFICATION_RECEIPT.json')
    if c.sha(indexraw) != RAW_INDEX_SHA256 or c.sha(qraw) != QUALIFICATION_SHA256:
        raise ValueError('EXACT_QUALIFIED_2022_METADATA_REQUIRED')
    index = c.exact_object(indexraw); qa = c.exact_object(qraw)
    if qa.get('status') != 'PASS_RAW_SOURCE_RESTORE_WITH_27_UNKNOWN_MARK_MINUTES':
        raise ValueError('EXACT_COMPLETE_RAW_SOURCE_RESTORE_STATUS_REQUIRED')
    expected_identity = c.jsha(dict(raw_index_SHA256=c.sha(indexraw),
        raw_qualification_SHA256=c.sha(qraw), daily_projection_SHA256=DAILY_SHA,
        funding_projection_SHA256=FUNDING_SHA, allowlist_SHA256=ALLOWLIST_SHA256))
    if expected_identity != SOURCE_IDENTITY:
        raise ValueError('EXACT_RAW_SOURCE_AND_PROJECTION_IDENTITY_REQUIRED')
    if index.get('schema') != 'FULL2022_RAW_SOURCE_INDEX_V1' or len(index.get('monthly', [])) != 120 or len(index.get('daily', [])) != 16:
        raise ValueError('EXACT120_MONTHLY16_DAILY_RAW_SOURCE_INDEX_REQUIRED')
    monthly=index['monthly'];daily=index['daily'];allitems=monthly+daily
    key=lambda r:(r['family'],r['symbol'],r['period'])
    if len({key(r) for r in monthly})!=120 or len({key(r) for r in daily})!=16:raise ValueError('UNIQUE_ORIGINAL_RAW_SOURCE_STREAMS_REQUIRED')
    qmap={key(r):r for r in qa['monthly']+qa['daily']}
    # Preserve exact original ZIP/checksum objects in captured source bindings.
    bodies={};filepins={};owner={};total_added=0
    for rec in allitems:
        path=source_path(rec['source_path']);raw=read(path,rec['ZIP_SHA256'],rec['ZIP_bytes']);name=str(path.relative_to(s.ROOT))
        bodies[name]=raw;filepins[name]=dict(SHA256=s.sha(raw),bytes=len(raw))
        if rec.get('CHECKSUM_path') is not None:
            cp=source_path(rec['CHECKSUM_path']);cb=read(cp,rec['CHECKSUM_SHA256'],rec['CHECKSUM_bytes'])
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
    arrays=[];anchors={};missing=[];dailyclose={};numeric_witnesses=[]
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
        old_name, old_start, old_count, old_sha, old_bytes, old_lo, old_hi = OLD_NORMALIZED_MONTH_PINS[month - 1]
        if (name, left, len(times), c.sha(blob), len(blob), 0, len(times)) != (old_name, old_start, old_count, old_sha, old_bytes, old_lo, old_hi):
            raise ValueError('EXACT_OLD_NATIVE_NORMALIZED_MONTH_BYTES_REQUIRED')
        bits = verify_normalized_numeric_bits(blob, a)
        numeric_witnesses.append(dict(file=name, SHA256=c.sha(blob), bytes=len(blob), array_identities=bits))
        arrays.append(dict(month=period,start_us=left,minutes=len(times),file=name))
    if total_added!=23040 or tuple(sorted(missing))!=tuple(sorted(s.ACTUAL27_OPEN_POINTS_US)):raise ValueError('EXACT16_GENUINE_DAILY_REPAIRS_AND27_MARK_HOLES_REQUIRED')
    # Raw source arrival is unknown; these are explicitly nominal completion
    # clocks under the reviewed replay convention, never venue-arrival proof.
    anchorraw=s.canonical(list(anchors.values()));bodies['MARK_ANCHORS.json']=anchorraw;filepins['MARK_ANCHORS.json']=dict(SHA256=s.sha(anchorraw),bytes=len(anchorraw))
    dailyraw=read(source_path(DAILY_PATH),DAILY_SHA,16950);fundraw=read(source_path(FUNDING_PATH),FUNDING_SHA,724500)
    # The final projection includes source-event annotations. The execution
    # projection removes all optional/archived fields before native finance.
    events=json.loads(fundraw);events=[dict(symbol=r['symbol'],event_us=r['calc_time_ms']*1000,raw_rate=r['raw_rate'],reported_interval_hours=r['reported_interval_hours'],raw_rate_unit='UNCONFIRMED') for r in events]
    funding=s.canonical(events);bodies['RAW_EVENTS.json']=funding;filepins['RAW_EVENTS.json']=dict(SHA256=s.sha(funding),bytes=len(funding))
    bodies['DAILY_PROJECTION.npz']=dailyraw;filepins['DAILY_PROJECTION.npz']=dict(SHA256=DAILY_SHA,bytes=len(dailyraw))
    bodies['RAW_QUALIFICATION.json']=qraw;filepins['RAW_QUALIFICATION.json']=dict(SHA256=s.sha(qraw),bytes=len(qraw))
    for name in source_files:bodies.pop(name,None)
    transport=dict(schema='FULL2022_CAPTURED_SOURCE_TRANSPORT_V1',source_identity=SOURCE_IDENTITY,
        files=filepins,source_files=source_files,qualification_file='RAW_QUALIFICATION.json',mark_anchor_file='MARK_ANCHORS.json',daily_projection_file='DAILY_PROJECTION.npz',funding_file='RAW_EVENTS.json',months=arrays)
    source_scope.validate_current(year=2022)
    if len(numeric_witnesses) != 12:
        raise ValueError('ALL12_EXACT_OLD_NATIVE_MONTH_WITNESSES_REQUIRED')
    transport['normalization_equivalence'] = dict(
        schema='CS2022_EXACT_OLD_NORMALIZED_MONTH_BYTES_AND_SOURCE_BITS_V1',
        old_preparation_SHA256='a4afcb2eb87d28936ba8d28e17dca52406fd63bbec2070c2036da1d5633fd9cf',
        old_prepared_source_review_SHA256='6fe46f96a5cac8d1c8f0830448eaa1d964fc35cf882ef92ccde7817cdd47644d',
        twelve_exact_old_container_hashes=True, source_to_serialized_numeric_bits=True,
        unchanged_parser_semantics=True, native_month_witnesses=numeric_witnesses,
        normalized_months_persisted=False, historical_execution_authorized=False)
    return transport,bodies
