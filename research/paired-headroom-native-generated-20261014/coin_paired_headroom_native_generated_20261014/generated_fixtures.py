"""Synthetic clocks/prices only. Source prehistory and wallets are generated."""
from functools import lru_cache
import numpy as np
from native_adapter import (ComparisonTape,PairedNativeAdapter,DirectLegacyTerminal60,
 PORT,ACCOUNT,TERMINAL,ORIGINALS,S,M,DAY)
START=207*DAY
NAMES=('FLAT','DISJOINT','COINCIDENT','MASKED','TERMINAL_ZERO','TERMINAL_LATE','HALT','ORIGINAL_CSH','HARD_RISK','SIGN_LOCK','COINCIDENT_TERMINAL_ZERO','TERMINAL_COMPLETE','OWNERSHIP','CAP_COLLISION','CAP_COLLISION_PAID','OWNERSHIP_HALT','CAP_COLLISION_PARTIAL')

def original_csh():
 t=np.arange(210,dtype=np.int64)*DAY;k=np.arange(len(t))[:,None];j=np.arange(5)[None,:]
 p=100*(1+.0006*k*(2-j)+.035*np.sin(.35*k+.8*j)+.008*np.sin(.17*k*(j+1)))
 clocks=np.array([START],dtype=np.int64);ids=np.searchsorted(t,clocks)
 hold=ORIGINALS.signed_intents(p,np.zeros_like(p),t,S)[ids,2]
 matched,_,_,_=ORIGINALS.match(t,p,clocks,hold,np.ones((1,5),bool))
 raw={a:matched[a] for a in ('CS_MATCHED','VOL_MATCHED')};raw['STATIC50']=.5*raw['CS_MATCHED']+.5*raw['VOL_MATCHED']
 sized,cov,_=ORIGINALS.allocate(t,p,clocks,raw)
 return sized['STATIC50'][0],cov[0]

@lru_cache(None)
def make(name='FLAT'):
 if name not in NAMES:raise ValueError('GENERATED_FIXTURE_NAME')
 days=2 if name=='SIGN_LOCK' else 1;minutes=days*1440
 n=43200+minutes;times=np.arange(n,dtype=np.int64)*M+START-43200*M
 p=np.full(n,100.);opens=p.copy();derived=np.zeros(n,dtype=bool)
 if name in ('DISJOINT','COINCIDENT','MASKED','TERMINAL_ZERO','TERMINAL_LATE','SIGN_LOCK','COINCIDENT_TERMINAL_ZERO','TERMINAL_COMPLETE'):
  p[1000:1005]=100*np.exp(.6)
  opens[1:]=p[:-1]
  gap=1001 if name.startswith('COINCIDENT') else 2000
  opens[gap]=p[gap-1]*np.exp(.4)
 if name.startswith('CAP_COLLISION'):
  p[1000:1005]=100*np.exp(.5);opens[1:]=p[:-1]
  p[43200+20]=120.;p[43200+21:]=121.;opens[43200+20]=100.;opens[43200+21]=120.;opens[43200+22:]=121.
  if name=='CAP_COLLISION_PAID':
   # Return to the original cap mark so its existing scaled target resolves.
   p[43200+22:]=120.;opens[43200+23:]=120.
 if name=='HALT':p[43200+20:]=400.;opens[43200+20:]=400.
 if name=='HARD_RISK':p[43200+20:]=120.;opens[43200+20:]=120.
 if name=='MASKED':derived[43200-1]=True
 scale={s:(j+1 if name.startswith('OWNERSHIP') else 1) for j,s in enumerate(S)}
 source={s:{'mark':p.copy()*scale[s],'open':opens.copy()*scale[s]} for s in S}
 tape=ComparisonTape(times,S,source,{s:derived.copy() for s in S})
 quote=np.full(minutes,5_000_000.)
 if name in ('TERMINAL_ZERO','TERMINAL_LATE','COINCIDENT_TERMINAL_ZERO','TERMINAL_COMPLETE'):
  quote[1:]=0.
  if name=='TERMINAL_LATE':quote[-12:]=10_000.
  if name=='TERMINAL_COMPLETE':quote[-35:]=100_000.
 market={s:dict(open=opens[43200:].copy()*scale[s],close=p[43200:].copy()*scale[s],mark=p[43200:].copy()*scale[s],quote_volume=quote.copy()) for s in S}
 w=np.array([-.2,0.,0.,0.,0.]);cov=np.eye(5)*.04
 if name.startswith('OWNERSHIP'):w[1]=.1
 if name=='ORIGINAL_CSH':w,cov=original_csh()
 if name in ('HARD_RISK','CAP_COLLISION','CAP_COLLISION_PAID','CAP_COLLISION_PARTIAL'):
  w[0]=-.3;quote[19:]=0.
  if name=='CAP_COLLISION_PAID':quote[23:]=2_000_000.
  if name=='CAP_COLLISION_PARTIAL':quote[23:]=50_000.
 for s in S:market[s]['quote_volume']=quote.copy()
 daily=PORT.native.pl.DataFrame([dict(symbol=s,close_us=START+d*DAY,close=100.*scale[s]) for d in range(days) for s in S])
 events=[dict(event_us=START+2*M,symbol=S[0],raw_rate=.001),dict(event_us=START+2*M,symbol=S[1],raw_rate=8.7 if name=='OWNERSHIP_HALT' else 7.6 if name.startswith('OWNERSHIP') else .002)]
 window=dict(fixture_scope='GENERATED_PAIRED_HEADROOM_ONLY',start=START,end=START+days*DAY,symbols=S,
  daily=daily,events=events,market=market,comparison_features=tape,headroom_features=tape.legacy)
 def factory(daily,clocks,mode):
  if mode!='LONG_SHORT' or list(clocks)!=[START+d*DAY for d in range(days)]:raise ValueError('GENERATED_TARGET_CLOCK')
  frame=PORT.native.pl.DataFrame([dict(available_us=START+d*DAY,symbol=s,target_weight=float(w[j])) for d in range(days) for j,s in enumerate(S)])
  return frame,dict(source='UNCHANGED_ORIGINAL_CSH_FUNCTIONS_GENERATED' if name=='ORIGINAL_CSH' else 'GENERATED_MECHANICAL_STATE',
   annual_vol=float(np.sqrt(w@cov@w)),annual_vol_target=.10,feature_lag_hours=0)
 return window,factory

def new(arm,name='FLAT',reference=False):
 window,factory=make(name)
 cls=(TERMINAL if arm=='disabled' else DirectLegacyTerminal60) if reference else PairedNativeAdapter
 kwargs={} if reference else {'arm':arm}
 return cls(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=factory,account_factory=ACCOUNT,**kwargs)

def finish(sim):
 while sim.stop is None and sim.cursor<sim.end:sim.advance_day()
 return sim
