"""In-memory minute and source-bar generators; no external market inputs."""
import hashlib,json
import numpy as np
from native_control import (S,DAY,MINUTE,PORT,ORIGINAL_TARGETS,SyntheticSourceRegistry,
                            H090NativeControl,DESCRIPTOR)
from calendar_readiness_v2 import SourcePacket
START=240*DAY
BASE27={'id':'BASE27','half_spread_bps':4,'slippage_bps':4,'roundtrip_bps':27}
STRESS43={'id':'STRESS43','half_spread_bps':8,'slippage_bps':8,'roundtrip_bps':43}
UNIT={'id':'RAW_AS_FRACTION','scale':1.0}


def generated_original_csh(days):
    """Unchanged six-original function bodies on generated complete closes.

    This is the unlagged original STATIC50/CSH recipe; no archived lagged
    PRICE_ONLY_CSH target array is read or used.
    """
    times=np.arange(0,START+(days+1)*DAY,DAY,dtype=np.int64)
    k=np.arange(len(times))[:,None];j=np.arange(5)[None,:]
    closes=100*(1+.0006*k*(2-j)+.035*np.sin(.35*k+.8*j)+.008*np.sin(.17*k*(j+1)))
    decisions=np.arange(START,START+days*DAY,DAY,dtype=np.int64)
    ids=np.searchsorted(times,decisions)
    held=ORIGINAL_TARGETS.signed_intents(closes,np.zeros_like(closes),times,S)[ids,2]
    matched,_,_,_=ORIGINAL_TARGETS.match(times,closes,decisions,held,np.ones((days,5),bool))
    raw={a:matched[a] for a in ('CS_MATCHED','VOL_MATCHED')}
    raw['STATIC50']=.5*raw['CS_MATCHED']+.5*raw['VOL_MATCHED']
    sized,cov,_=ORIGINAL_TARGETS.allocate(times,closes,decisions,raw)
    return times,closes,sized['STATIC50'],cov


def source_document(t,close_matrix=None):
    closes=np.full((200,5),100.) if close_matrix is None else np.asarray(close_matrix,dtype=float)
    if closes.shape!=(200,5):raise ValueError('GENERATED200_CORE5_CLOSES_REQUIRED')
    daily=[]
    for i in range(200):
        end=t-(199-i)*DAY
        for j,s in enumerate(S):
            daily.append(dict(symbol=s,open_us=end-DAY,close_us=end,available_us=end,
                close=float(closes[i,j]),complete=True,imputed=False,actual_source=True,
                record_locator=f'generated/day{i}/{s}'))
    return {'symbol_order':list(S),'daily_bars':daily,
            'fixture_scope':'GENERATED_NOT_REAL_PROVIDER_OR_ARRIVAL_CERTIFICATION'}


def encode_source(source,manifest_changes=None):
    raw=json.dumps(source,sort_keys=True,separators=(',',':'),allow_nan=True).encode()
    manifest={'schema':'H090_REVIEWED_SOURCE_BAR_BINDING_V2',
        'status':'PINNED_ACTUAL_COMPLETE_SOURCE_BARS',
        'source_blob_SHA256':hashlib.sha256(raw).hexdigest(),
        'source_index_SHA256':hashlib.sha256(b'EXPLICIT_GENERATED_SOURCE_INDEX_V1').hexdigest(),
        'symbol_order':list(S),'signal_interval_minutes':1440,
        'fixture_scope':'GENERATED_ONLY_NOT_REAL_PROVIDER_OR_ARRIVAL_CERTIFICATION'}
    manifest.update(manifest_changes or {})
    binding=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
    return SourcePacket(raw,binding,hashlib.sha256(binding).hexdigest()),manifest


def make_generated(days=1,*,weights=None,original_recipe=False,quote=10000000.,
                   source_mutations=None,events=None,minute_prices=None):
    if type(days) is not int or not 1<=days<=3:raise ValueError('BOUNDED_GENERATED1_TO3_DAYS')
    clocks=np.arange(START,START+days*DAY,DAY,dtype=np.int64)
    if original_recipe:
        times,all_closes,w,_=generated_original_csh(days)
        matrices={int(t):all_closes[np.searchsorted(times,t)-199:np.searchsorted(times,t)+1] for t in clocks}
        recipe='EXACT_UNLAGGED_ORIGINAL_STATIC50_CSH_FUNCTIONS_GENERATED_INPUTS'
    else:
        w=np.tile([.2,.2,.2,0.,0.],(days,1)) if weights is None else np.asarray(weights,float)
        if w.ndim==1:w=np.tile(w,(days,1))
        if w.shape!=(days,5):raise ValueError('EXACT_GENERATED_TARGET_SHAPE')
        matrices={int(t):np.full((200,5),100.) for t in clocks}
        recipe='GENERATED_TARGET_BOUNDARY_STATE_FIXTURE_NOT_STRATEGY_ALPHA'
    packets={};approved={};daily=[]
    for t in clocks:
        t=int(t);document=source_document(t,matrices[t])
        for j,s in enumerate(S):daily.append(dict(symbol=s,close_us=t,close=float(matrices[t][-1,j])))
        if source_mutations and t in source_mutations:source_mutations[t](document)
        packet,manifest=encode_source(document)
        packets[t]=packet
        approved[t]={'manifest_SHA256':packet.approved_manifest_sha256,
                     'source_index_SHA256':manifest['source_index_SHA256']}
    registry=SyntheticSourceRegistry(approved)
    n=days*1440
    quotes=np.full(n,float(quote)) if np.isscalar(quote) else np.asarray(quote,float)
    if quotes.shape!=(n,):raise ValueError('COMPLETE_GENERATED_QUOTE_MINUTES')
    if minute_prices is None:
        price_map={s:np.concatenate([np.full(1440,matrices[int(t)][-1,j]) for t in clocks]) for j,s in enumerate(S)}
    elif isinstance(minute_prices,dict):
        price_map={s:np.asarray(minute_prices[s],float) for s in S}
    else:
        price_map={s:np.asarray(minute_prices,float) for s in S}
    market={s:{'open':price_map[s].copy(),'close':price_map[s].copy(),
               'mark':price_map[s].copy(),'quote_volume':quotes.copy()} for s in S}
    window={'fixture_scope':'GENERATED_NATIVE_FINANCE_ONLY','start':START,'end':START+days*DAY,
        'symbols':S,'daily':PORT.native.pl.DataFrame(daily),'events':list(events or []),'market':market}
    def factory(_daily,decisions,mode):
        if mode!='LONG_SHORT' or not np.array_equal(decisions,clocks):raise ValueError('EXACT_GENERATED_FACTORY_CLOCK')
        return PORT.native.pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(w[i,j]))
            for i,t in enumerate(clocks) for j,s in enumerate(S)]),{'source':recipe,'fixture_scope':'GENERATED_ONLY'}
    return window,factory,packets,registry,w.copy()


def new_h090(bundle,*,preloaded=True,cost=BASE27):
    window,factory,packets,registry,_=bundle
    return H090NativeControl(window,'LONG_SHORT',cost,UNIT,
        target_factory=factory if preloaded else None,source_registry=registry,source_packets=packets)


def finish(sim,bundle=None):
    while sim.stop is None and sim.cursor<sim.end:
        if bundle is not None:
            i=(sim.cursor-START)//DAY
            sim.advance_day(original_csh_weights=dict(zip(S,bundle[-1][i],strict=True)))
        else:sim.advance_day()
    return sim
