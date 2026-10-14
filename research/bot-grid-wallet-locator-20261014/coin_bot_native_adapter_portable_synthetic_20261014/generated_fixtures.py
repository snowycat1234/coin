"""Fixed toy-only dense arrays generated in memory, never loaded market data."""
from dataclasses import dataclass
import numpy as np
from native_adapter import PORT,ACCOUNT,NATIVE,GridNativeAdapter,F,H,S,DAY,M,D
START=207*DAY  # Monday1970-07-27: a synthetic clock, not a market-data period.
NAMES=('RANGE','PARTIAL','SIGN_FLIP','WEEK_RESET','TERMINAL_RESIDUAL','ORIGINAL_CSH','NEUTRAL','RISK_GAP','UNKNOWN_COV','BAD_RANGE','FLAT_WEEK_RESET')


def original_csh(days):
 # Execute unchanged original six-source function bodies on generated history.
 t=np.arange(0,209*DAY+days*DAY,DAY,dtype=np.int64)
 k=np.arange(len(t))[:,None];j=np.arange(5)[None,:]
 p=100*(1+.0006*k*(2-j)+.035*np.sin(.35*k+.8*j)+.008*np.sin(.17*k*(j+1)))
 decisions=np.arange(START,START+days*DAY,DAY,dtype=np.int64);ids=np.searchsorted(t,decisions)
 hold=F.signed_intents(p,np.zeros_like(p),t,S)[ids,2]
 matched,proof,_,_=F.match(t,p,decisions,hold,np.ones((days,5),bool))
 raw={a:matched[a] for a in ('CS_MATCHED','VOL_MATCHED')}
 raw['STATIC50']=.5*raw['CS_MATCHED']+.5*raw['VOL_MATCHED']
 sized,cov,_=F.allocate(t,p,decisions,raw)
 return t,p,sized['STATIC50'],cov


def make(name='RANGE'):
 if name not in NAMES:raise ValueError('GENERATED_ONLY_FIXED_FIXTURE_NAME')
 days=8 if name in ('WEEK_RESET','FLAT_WEEK_RESET') else 2 if name=='SIGN_FLIP' else 1
 end=START+days*DAY;clock=np.arange(START,end,DAY,dtype=np.int64)
 t,p,generated_original,cov=original_csh(days)
 # Most fixtures force simple target states to test adapter plumbing, not alpha.
 w=generated_original if name=='ORIGINAL_CSH' else np.tile(np.array([.2,.05,0.,0.,-.1]),(days,1))
 if name=='SIGN_FLIP':w[1,0]=-.15
 if name=='NEUTRAL':w[:]=[.2,0.,0.,0.,-.2]
 if name=='RISK_GAP':w[:]=[.29,0.,0.,0.,-.1]
 if name in ('WEEK_RESET','FLAT_WEEK_RESET'):
  w[:]=0.;w[:,0]=.2+.005*np.arange(days)
 minutes=np.arange(days*1440)
 prices=100+6*np.sin(minutes*.027)
 if name=='ORIGINAL_CSH':prices=100+np.sin(minutes*.02)
 quote=np.full(days*1440,500000.)
 if name=='PARTIAL':quote[0]=2000000.;quote[1]=91000.;quote[2:30]=12000.
 if name=='RISK_GAP':prices[30:]=200.;quote[:]=2000000.
 if name=='FLAT_WEEK_RESET':
  prices[:20]=100.;prices[20:35]=105.;prices[35:50]=110.;prices[50:7*1440]=111.;prices[7*1440-1:]=100.;quote[:]=5000000.
 if name=='TERMINAL_RESIDUAL':quote[-61:]=0.
 market={s:dict(open=(prices.copy() if s==S[0] else np.full(days*1440,100.)),
                close=(prices.copy() if s==S[0] else np.full(days*1440,100.)),
                mark=(prices.copy() if s==S[0] else np.full(days*1440,100.)),quote_volume=quote.copy()) for s in S}
 daily=PORT.native.pl.DataFrame([dict(symbol=s,close_us=int(c),close=100.) for c in clock for s in S])
 events=[dict(event_us=START+n*M+1,symbol=s,raw_rate=.001) for n in (1,2,4,16,60) for s in (S[0],S[-1])]
 if name=='FLAT_WEEK_RESET':events=[]
 events.sort(key=lambda e:(e['event_us'],S.index(e['symbol'])))
 window=dict(start=START,end=end,symbols=S,daily=daily,events=events,market=market)
 # Fixed valid synthetic range independent of future minute values.
 closes={int(c):[H.CompletedClose(int(c)-(29-i)*DAY,D(90 if i%2==0 else 110),int(c)-(29-i)*DAY) for i in range(30)] for c in clock}
 if name=='BAD_RANGE':closes={int(c):[H.CompletedClose(int(c)-(29-i)*DAY,D(90),int(c)-(29-i)*DAY) for i in range(30)] for c in clock}
 covariance={int(c):(cov[i] if name=="ORIGINAL_CSH" else np.eye(5)*.04) for i,c in enumerate(clock)}
 if name=='UNKNOWN_COV':covariance={}
 def factory(_daily,clocks,mode):
  if mode!='LONG_SHORT' or not np.array_equal(clock,clocks):raise ValueError('GENERATED_TARGET_CLOCK')
  return PORT.native.pl.DataFrame([dict(available_us=int(c),symbol=s,target_weight=float(w[i,j])) for i,c in enumerate(clock) for j,s in enumerate(S)]),dict(source='UNCHANGED_ORIGINAL_CSH_FUNCTIONS_ON_GENERATED_CLOSES' if name=='ORIGINAL_CSH' else 'GENERATED_TARGET_STATE_MACHINE_FIXTURE',fixture=name)
 return window,factory,closes,covariance,w.copy()


class CashReference(NATIVE):
 """Independent cash control on exact original Decimal target quantities."""
 def schedule(self,target,signal,kind,only_symbols=None):
  active=S if only_symbols is None else tuple(only_symbols)
  if S[0] in active:
   btc_kind=kind[S[0]] if isinstance(kind,dict) else kind
   if btc_kind=='DAILY_TARGET' and target[S[0]]>0:
    target=dict(target);target[S[0]]=target[S[0]]*D('.9')
  return super().schedule(target,signal,kind,only_symbols)


def new_sim(arm,name='RANGE',direct=False):
 window,factory,closes,cov,weights=make(name)
 cls=(CashReference if arm=='CASH' else NATIVE) if direct else GridNativeAdapter
 kwargs={} if direct else dict(arm=arm,daily_closes=closes,covariance=cov,initial_observations={START:H.CompletedMinute(START,D(100),START)})
 return cls(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=factory,account_factory=ACCOUNT,**kwargs)


def finish(sim):
 while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
 return sim
