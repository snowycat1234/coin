"""STEP1 pin-bound source/calendar readiness; no account or history entry."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,json
import numpy as np
CORE5=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY=86_400_000_000
MAX_I64=2**63-1
class SourceReadinessError(ValueError):pass

def clock(x):
    if not isinstance(x,(int,np.integer)) or isinstance(x,(bool,np.bool_)) or not 0<=int(x)<=MAX_I64:
        raise SourceReadinessError('NONNEGATIVE_NONBOOLEAN_INT64_CLOCK_REQUIRED')
    return int(x)

def decision_grid(decision_us,signal_interval_minutes):
    t=clock(decision_us)
    if type(signal_interval_minutes) is not int or signal_interval_minutes not in (1440,240):
        raise SourceReadinessError('SIGNAL_INTERVAL_1440_OR_240_ONLY')
    if t%(signal_interval_minutes*60_000_000):raise SourceReadinessError('ORIGINAL_UTC_DECISION_GRID_REQUIRED')
    return t,t//DAY*DAY

@dataclass(frozen=True)
class SourcePacket:
    """Raw source bytes plus an independently pinned manifest, NOT return clocks.
    approved_manifest_sha256 must come from a trusted reviewed source binding.
    A self-selected caller hash is not independent source certification. This
    module checks byte identity and readiness, not provider/venue authority.
    """
    source_bytes:bytes
    manifest_bytes:bytes
    approved_manifest_sha256:str

def _bars(rows,interval,t):
    if not isinstance(rows,list) or not rows or len(rows)%5:raise SourceReadinessError('COMPLETE_ORDERED_CORE5_SOURCE_ROWS_REQUIRED')
    by_time=[];seen_locators=set()
    for offset in range(0,len(rows),5):
        group=rows[offset:offset+5]
        if any(not isinstance(r,dict) for r in group) or tuple(r.get('symbol') for r in group)!=CORE5:
            raise SourceReadinessError('REORDERED_OR_MALFORMED_SOURCE')
        end=clock(group[0].get('close_us'));values=[];available=[]
        if end%interval:raise SourceReadinessError('UTC_SOURCE_BAR_ALIGNMENT_REQUIRED')
        for r in group:
            op=clock(r.get('open_us'));cl=clock(r.get('close_us'));av=clock(r.get('available_us'))
            if cl!=end or op+interval!=cl or av<cl or av>t or cl>t:
                raise SourceReadinessError('INCOMPLETE_DELAYED_OR_FUTURE_SOURCE')
            if r.get('complete') is not True or r.get('imputed') is not False or r.get('actual_source') is not True:
                raise SourceReadinessError('ACTUAL_COMPLETE_NONIMPUTED_SOURCE_REQUIRED')
            p=r.get('close')
            if isinstance(p,bool) or not isinstance(p,(int,float)) or not np.isfinite(p) or p<=0:
                raise SourceReadinessError('POSITIVE_FINITE_SOURCE_CLOSE_REQUIRED')
            locator=r.get('record_locator')
            if not isinstance(locator,str) or not locator or locator.startswith('/') or '..' in Path(locator).parts:
                raise SourceReadinessError('PROJECT_RELATIVE_SOURCE_RECORD_LOCATOR_REQUIRED')
            if locator in seen_locators:raise SourceReadinessError('DUPLICATE_SOURCE_RECORD_LOCATOR')
            seen_locators.add(locator)
            values.append(float(p));available.append(av)
        if by_time and end-by_time[-1][0]!=interval:raise SourceReadinessError('MISSING_DUPLICATE_OR_SHIFTED_SOURCE_BARS')
        by_time.append((end,values,available))
    return by_time

def certify_source(packet,*,decision_us,signal_interval_minutes):
    t,expected=decision_grid(decision_us,signal_interval_minutes)
    if type(packet) is not SourcePacket:raise SourceReadinessError('PIN_BOUND_SOURCE_PACKET_REQUIRED_NOT_CALLER_RETURNS')
    if type(packet.source_bytes) is not bytes or type(packet.manifest_bytes) is not bytes:raise SourceReadinessError('IMMUTABLE_SOURCE_BYTES_REQUIRED')
    if hashlib.sha256(packet.manifest_bytes).hexdigest()!=packet.approved_manifest_sha256:
        raise SourceReadinessError('SOURCE_MANIFEST_PIN_MISMATCH')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise SourceReadinessError('DUPLICATE_JSON_SOURCE_FIELD')
            result[k]=v
        return result
    def bad_constant(value):raise SourceReadinessError('NONFINITE_JSON_SOURCE_VALUE')
    try:
        manifest=json.loads(packet.manifest_bytes,object_pairs_hook=pairs,parse_constant=bad_constant)
        source=json.loads(packet.source_bytes,object_pairs_hook=pairs,parse_constant=bad_constant)
    except (ValueError,UnicodeError) as error:raise SourceReadinessError('MALFORMED_PINNED_SOURCE_JSON') from error
    if not isinstance(manifest,dict) or not isinstance(source,dict):raise SourceReadinessError('SOURCE_AND_MANIFEST_OBJECTS_REQUIRED')
    if manifest.get('schema')!='H090_REVIEWED_SOURCE_BAR_BINDING_V2' or manifest.get('status')!='PINNED_ACTUAL_COMPLETE_SOURCE_BARS':
        raise SourceReadinessError('REVIEWED_SOURCE_BAR_BINDING_REQUIRED')
    if manifest.get('source_blob_SHA256')!=hashlib.sha256(packet.source_bytes).hexdigest():raise SourceReadinessError('SOURCE_BLOB_HASH_MISMATCH')
    if tuple(manifest.get('symbol_order',()))!=CORE5 or tuple(source.get('symbol_order',()))!=CORE5:
        raise SourceReadinessError('EXACT_CORE5_SOURCE_ORDER_REQUIRED')
    if not isinstance(manifest.get('source_index_SHA256'),str) or len(manifest['source_index_SHA256'])!=64 or any(x not in '0123456789abcdef' for x in manifest['source_index_SHA256']):
        raise SourceReadinessError('ORIGINAL_SOURCE_INDEX_BINDING_REQUIRED')
    if manifest.get('signal_interval_minutes')!=signal_interval_minutes:
        raise SourceReadinessError('SOURCE_SIGNAL_INTERVAL_MISMATCH')
    daily=_bars(source.get('daily_bars'),DAY,t)
    signal=daily if signal_interval_minutes==1440 else _bars(source.get('signal_bars'),signal_interval_minutes*60_000_000,t)
    # Preserve original target/risk eligibility.31 closes are only the return
    # dependency, not permission to drop the upstream200 complete-bar warmup.
    if len(daily)<200 or len(signal)<200:raise SourceReadinessError('ORIGINAL200_SIGNAL_AND_RISK_WARMUP_REQUIRED')
    if signal[-1][0]!=t:raise SourceReadinessError('LATEST_SIGNAL_CLOSE_REQUIRED')
    if daily[-1][0]!=expected:raise SourceReadinessError('LATEST_EXPECTED_UTC_DAILY_CLOSE_REQUIRED_NO_FALLBACK')
    selected=daily[-31:]
    wanted=[expected-i*DAY for i in range(30,-1,-1)]
    if wanted[0]<0 or [r[0] for r in selected]!=wanted:raise SourceReadinessError('EXACT31_LATEST_UTC_DAILY_CLOSES_REQUIRED')
    closes=np.asarray([r[1] for r in selected],np.float64)
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):returns=np.diff(closes,axis=0)/closes[:-1]
    if not np.isfinite(returns).all():raise SourceReadinessError('NONFINITE_DERIVED_RETURN')
    # BOTH endpoints, all5 assets: ten underlying source observations per return.
    availability=np.asarray([max(selected[i][2]+selected[i+1][2]) for i in range(30)],dtype=np.int64)
    ends=np.asarray(wanted[1:],dtype=np.int64)
    if np.any(availability>t):raise SourceReadinessError('DERIVED_RETURN_NOT_AVAILABLE')
    provenance={'schema':'H090_STEP1_CERTIFIED_CALENDAR_SOURCE_V2','source_manifest_SHA256':packet.approved_manifest_sha256,
        'source_blob_SHA256':manifest['source_blob_SHA256'],'source_index_SHA256':manifest['source_index_SHA256'],
        'decision_us':t,'expected_daily_end':expected,'signal_interval_minutes':signal_interval_minutes,
        'return_ends_us':ends.tolist(),'derived_return_available_us':availability.tolist(),
        'selected_returns_SHA256':hashlib.sha256(np.ascontiguousarray(returns,dtype='<f8').tobytes()).hexdigest(),
        'actual_complete_daily_bars':len(daily),'actual_complete_signal_bars':len(signal),
        'source_failure_action':'BLOCK_NEW_RISK_PRESERVE_EXISTING_EXPLICIT_GAP_REDUCE_ONLY_AND_INVENTORY',
        'native_integration':'NO_GO'}
    return returns,ends,availability,provenance
