"""UNRUN independent audit of only the new conditional signed-perpetual accounts.

The archived HandLedger supplies weighted-entry/realized/quote-wallet math.
This reader adds isolated/free cash reservations and sparse event bridges, then
checks saved minute/day/month arrays. No producer account, simulate(), target
function, old financial suite, ZIP/CRC or API is called. Root must freeze the
small ACTUAL_BINDING and wait for every producer to actually close before use.
"""
from __future__ import annotations
import argparse, gc, hashlib, importlib.util, json, math, os, resource, sys, time
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np
import polars as pl
from quant import resources

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
REFERENCE='docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
REFERENCE_SHA='3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'
STATUS='PASS_CONDITIONAL_PERPETUAL_DIRECTIONAL_JOURNAL_NAV_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
ACTUAL_STATUS='COMPLETE_CONDITIONAL_USDM_FOUR_DIRECTION_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
SYMS=('BTCUSDT','ETHUSDT');MODES=('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH')
COSTS={'BASE27':(4,4,27),'STRESS43':(8,8,43)};UNITS={'RAW_AS_FRACTION':Decimal(1),'RAW_AS_PERCENT':Decimal('.01')}
D=Decimal;Z=D(0);MIN=60_000_000;DAY=86_400_000_000;FEE=D('.00055')
CASH_TOL=1e-7;RATIO_TOL=1e-10

def need(ok,msg):
    if not bool(ok):raise ValueError(msg)

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def module(path,name,digest):
    need(sha(ROOT/path)==digest and not (ROOT/path).is_symlink(),'Pinned independent helper '+path)
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

def dec(value):
    need(not isinstance(value,bool),'Nonboolean money');v=D(str(value));need(v.is_finite(),'Finite money');return v

def exact(row,key):
    text=row.get('decimal_strings',{})
    return dec(text[key] if key in text else row[key])

def stamp(day):return int(datetime.fromisoformat(day).timestamp())*1_000_000

def project(g,name):
    # This explicit existing source registry is ordinary small metadata. All
    # names still require an exact frozen digest; no arbitrary docs/data read.
    return g.ordinary(ROOT/name) if name=='docs/OPEN_SOURCE_REGISTRY.md' else g.project(name)

def same(a,b,label,maximum,tol=CASH_TOL):
    x=np.asarray(a,dtype=np.float64);y=np.asarray(b,dtype=np.float64)
    need(x.shape==y.shape and np.isfinite(x).all() and np.isfinite(y).all(),label+' shapes/finite')
    error=float(np.max(np.abs(x-y),initial=0.));maximum['ratio' if tol==RATIO_TOL else 'cash']=max(maximum['ratio' if tol==RATIO_TOL else 'cash'],error)
    need(error<=tol,label+f' error {error} > {tol}')

def payload(item,run=None):
    p=Path(item.get('path',item.get('normalized_path','')))
    need(p.is_absolute() and '..' not in p.parts and p.is_relative_to(STATE) and p.is_file(),'Actual D-hosted allowed payload')
    if run is not None:need(p.is_relative_to(run),'Only new account artifact')
    for parent in (p,*p.parents):
        need(not parent.is_symlink(),'No payload symlink')
        if parent==STATE:break
    digest=item.get('sha256',item.get('normalized_sha256'));size=item.get('bytes',item.get('normalized_bytes'))
    need(p.stat().st_size==size and sha(p)==digest,'Exact accepted/published file bytes')
    return p

def window_reader(manifest,w):
    """Financially necessary columns once/window; no source QA or index read."""
    start,end=stamp(w['start']),stamp(w['end_exclusive']);count=(end-start)//MIN
    expected={'122D':('2025-08-01T00:00:00+00:00','2025-12-01T00:00:00+00:00',122),
              '90D':('2025-12-01T00:00:00+00:00','2026-03-01T00:00:00+00:00',90)}[w['id']]
    need((start,end,w['days'])==(stamp(expected[0]),stamp(expected[1]),expected[2]) and count==w['minutes_per_symbol'],'Fixed seen windows/no locked period')
    result=dict(start=start,end=end,count=count,days=w['days'],market={},bars={},events=[],proofs=[])
    def read(ids,columns):
        frames=[]
        for identity in ids:
            item=manifest['source_files'][identity];p=payload(item);frames.append(pl.read_parquet(p,columns=columns))
            result['proofs'].append(dict(id=identity,path=str(p),sha256=item['normalized_sha256'],bytes=item['normalized_bytes'],
                rows=item['rows'],format_evidence_role=item['format_evidence_role']))
        return pl.concat(frames,how='vertical')
    for s in SYMS:
        ids=w['symbols'][s]['source_ids']
        trade=read(ids['trade_1m'],['open_us','open','quote_volume']).sort('open_us')
        marks=read(ids['mark_1m'],['timestamp_ms','close']).sort('timestamp_ms')
        bars=read(ids['trade_1d_warmup']+ids['trade_1d_score'],['symbol','close_us','available_us','close']).sort('close_us')
        fund=read(ids['funding'],['calc_time_ms','last_funding_rate']).sort('calc_time_ms')
        times=np.arange(start,end,MIN,dtype=np.int64)
        need(np.array_equal(trade['open_us'],times) and np.array_equal(marks['timestamp_ms'].to_numpy()*1000,times),'Financial shared calendar alignment')
        result['market'][s]=dict(open=trade['open'].to_numpy(),quote=trade['quote_volume'].to_numpy(),mark=marks['close'].to_numpy())
        need(all(np.isfinite(v).all() for v in result['market'][s].values()) and np.all(result['market'][s]['open']>0)
            and np.all(result['market'][s]['mark']>0) and np.all(result['market'][s]['quote']>=0),'Finite actual financial price/capacity inputs')
        result['bars'][s]=bars
        for e,r in fund.iter_rows():
            need(start<=e*1000<end and math.isfinite(r),'Original event allowed range/signed rate retained')
            result['events'].append(dict(symbol=s,event_us=e*1000,raw_rate=r))
    result['events'].sort(key=lambda r:(r['event_us'],r['symbol']))
    need(len({(r['symbol'],r['event_us']) for r in result['events']})==len(result['events'])
        and len(result['events'])==sum(w['symbols'][s]['rows_inherited_from_receipts']['funding'] for s in SYMS),'Exact original event identities/counts')
    return result

def target_reference(w,mode):
    """Scalar strict SMA hook states + explicit signed 30-day sample covariance."""
    states=dict.fromkeys(SYMS,0);rows=[];witness=[]
    for t in range(w['start'],w['end'],DAY):
        raw=[];returns=[]
        for s in SYMS:
            b=w['bars'][s];i=int(np.searchsorted(b['close_us'].to_numpy(),t,side='right')-1)
            need(i>=199 and b['close_us'][i]==t and np.all(b['available_us'][i-199:i+1].to_numpy()<=t),'200 completed causal available days')
            closes=b['close'][i-199:i+1].to_numpy();fast=math.fsum(map(float,closes[-50:]))/50;slow=math.fsum(map(float,closes))/200
            old=states[s]
            if mode=='CASH':states[s]=0
            elif old:states[s]=0 if old==1 and fast<slow or old==-1 and fast>slow else old
            elif mode in ('LONG_ONLY','LONG_SHORT') and fast>slow:states[s]=1
            elif mode in ('SHORT_ONLY','LONG_SHORT') and fast<slow:states[s]=-1
            raw.append(.3*states[s]);r=np.diff(closes[-31:])/closes[-31:-1];returns.append(r)
            witness.append(dict(decision_us=t,symbol=s,fast=fast,slow=slow,old_state=old,new_state=states[s]))
        r=np.column_stack(returns);centered=r-r.mean(axis=0);cov=centered.T@centered/29*365
        weights=np.asarray(raw);sigma=math.sqrt(max(float(weights@cov@weights),0.))
        if sigma>.10:weights=weights*(.10/sigma)
        for s,a,b in zip(SYMS,weights,raw,strict=True):rows.append((t,s,a,b,mode))
    return pl.DataFrame(rows,schema=['available_us','symbol','target_weight','raw_signed_target','mode'],orient='row'),witness

def current_mark(w,s,t,strict=False):
    # Input mark row i is the minute ending at start+(i+1)*MIN.
    i=min((int(t)-w['start']-int(strict))//MIN-1,w['count']-1)
    return (None,None) if i<0 else (dec(w['market'][s]['mark'][i]),w['start']+(i+1)*MIN)

def financial_journals(w,case,trades,funds,ref,maximum):
    hand={s:ref.HandLedger(Z) for s in SYMS};free=D(10000);margin=dict.fromkeys(SYMS,Z);liability=Z
    exec_cost=turnover=Z;attribution={d:dict(gross=Z,fees=Z,execution_cost=Z,funding=Z) for d in ('LONG','SHORT')}
    snapshots=[];capacity=defaultdict(lambda:Z);fill_keys=set();owned=0
    def debit(s,amount):
        nonlocal free,liability
        a=min(free,amount);free-=a;amount-=a;b=min(margin[s],amount);margin[s]-=b;liability+=amount-b
    def save(t):
        snapshots.append(dict(t=t,free=float(free),liability=float(liability),wallet=float(D(10000)+sum((h.wallet for h in hand.values()),Z)),
            fees=float(sum((h.fees for h in hand.values()),Z)),funding=float(sum((h.funding_cash for h in hand.values()),Z)),
            cost=float(exec_cost),turnover=float(turnover),q=[float(hand[s].quantity) for s in SYMS],
            entry=[float(hand[s].entry_fill) for s in SYMS],margin=[float(margin[s]) for s in SYMS]))
    save(w['start']-1)
    expected=w['events'][:len(funds)];need(len(funds)<=len(w['events']),'Funding cannot invent events')
    need([r['event_us'] for r in trades]==sorted(r['event_us'] for r in trades),'No time-reordered actual fills')
    for t in dict.fromkeys(r['event_us'] for r in trades):
        legs=[r['leg'] for r in trades if r['event_us']==t]
        need(legs==sorted(legs,key=lambda x:0 if x=='CLOSE' else 1),'All assets reduce before any asset increases at one fill time')
    for r,e in zip(funds,expected,strict=True):
        need(r['symbol']==e['symbol'] and r['event_us']==e['event_us'] and r['raw_rate']==e['raw_rate'],'Every original signed funding row/prefix exactly once')
    stream=sorted([(r['event_us'],1,i,r) for i,r in enumerate(trades)]+[(r['event_us'],0,i,r) for i,r in enumerate(funds)],key=lambda r:r[:3])
    with localcontext() as ctx:
        ctx.prec=50
        for t,kind,index,r in stream:
            s=r['symbol'];h=hand[s]
            if kind==0:
                q=h.quantity;mark,close=current_mark(w,s,t,True);raw=expected[index]['raw_rate'];rate=dec(raw)*UNITS[case['unit_id']]
                need(bool(r['owned'])==bool(q),'Funding signed owned quantity, no nominal substitute')
                same(exact(r,'quantity'),q,'Funding owned q',maximum,RATIO_TOL)
                if mark is None:need(q==0 and r['mark_price'] is None,'Only fresh flat can have no prior mark')
                elif r['mark_price'] is not None:
                    same(exact(r,'mark_price'),mark,'Strict prior funding mark',maximum)
                    need(r['mark_close_us']==close and close<t,'Funding not valued at current/future close')
                need(not q or r['mark_price'] is not None,'Owned funding requires explicit strictly past mark')
                amount=-q*mark*rate if q else Z
                same(exact(r,'signed_funding_USDT'),amount,'Signed conditional funding cash',maximum)
                if q:owned+=1;attribution['LONG' if q>0 else 'SHORT']['funding']+=amount
                h.wallet+=amount;h.funding_cash+=amount
                if amount>=0:free+=amount
                else:debit(s,-amount)
            else:
                need((r['fill_id'],r['leg']) not in fill_keys,'Exact once fill leg');fill_keys.add((r['fill_id'],r['leg']))
                q=exact(r,'quantity');delta=exact(r,'position_delta');mid=exact(r,'execution_mid_price');fill=exact(r,'fill_price')
                old_q=h.quantity;old_entry=h.entry_fill;before_free=free;before_margin=margin[s]
                need(q>0 and q%D('1e-8')==0 and abs(delta)==q and r['side']==('BUY' if delta>0 else 'SELL'), 'Signed step/side/quantity')
                need(t%MIN==1 and w['start']<t<w['end'],'Only actual trade-open+1us scoring fills')
                i=(t-w['start'])//MIN;need(i>0,'Previous completed minute liquidity required')
                same(mid,w['market'][s]['open'][i],'Actual separately observed trade open mid',maximum)
                earliest=((r['signal_us']+MIN-1)//MIN+1)*MIN+1
                need(earliest<=t<=earliest+4*MIN,'Strict execution latency and at most five attempts')
                limit=dec(w['market'][s]['quote'][i-1])*D('.001')/mid
                capacity[(s,t)]+=q;need(capacity[(s,t)]<=limit,'Prior-minute capacity shared by close/open legs')
                spread,slip,_=COSTS[case['cost_id']];direction=D(1) if delta>0 else D(-1)
                same(fill,mid*(1+direction*D(spread+slip)/10000),'Declared conservative execution price',maximum)
                need(q*fill>=10,'No invented below-notional fill/dust forgiveness')
                mark,_=current_mark(w,s,t);same(exact(r,'mark_price'),mark,'Separate causal valuation mark',maximum)
                if r['leg']=='OPEN':
                    need(not old_q or old_q*delta>0,'Open must add same direction or fresh position')
                    allocated=q*fill;need(free>=allocated+q*fill*FEE,'Actual affordable free margin plus fee')
                    margin[s]+=allocated;free-=allocated+q*fill*FEE
                    released=Z
                else:
                    need(r['leg']=='CLOSE' and old_q*delta<0 and q<=abs(old_q),'Close cannot cross zero')
                    released=margin[s]*q/abs(old_q);margin[s]-=released;free+=released;allocated=Z
                calc=h.fill(delta,fill,FEE)
                need(case['mode'] not in ('LONG_ONLY','CASH') or h.quantity>=0,'No forbidden short at any fill')
                need(case['mode'] not in ('SHORT_ONLY','CASH') or h.quantity<=0,'No forbidden long at any fill')
                if r['leg']=='CLOSE':
                    if calc['realized_PnL']>=0:free+=calc['realized_PnL']
                    else:debit(s,-calc['realized_PnL'])
                    debit(s,calc['fee'])
                    if not h.quantity:free+=margin[s];margin[s]=Z
                cost=q*abs(fill-mid);exec_cost+=cost;turnover+=q*fill
                for key,value in dict(quantity_before=old_q,quantity_after=h.quantity,entry_price_before=old_entry,
                    entry_price_after=h.entry_fill,fee_amount=calc['fee'],fee_USDT_mid=calc['fee'],realized_PnL=calc['realized_PnL'],
                    cash_delta=calc['realized_PnL']-calc['fee'],margin_allocated=allocated,margin_released=released,
                    free_cash_delta=free-before_free,isolated_balance_delta=margin[s]-before_margin,execution_cost=cost).items():
                    same(exact(r,key),value,'Decimal leg '+key,maximum,RATIO_TOL if 'quantity' in key else CASH_TOL)
                need(r['fee_asset']=='USDT','Perpetual fees must not subtract base inventory')
                label='LONG' if (old_q if r['leg']=='CLOSE' else delta)>0 else 'SHORT'
                attribution[label]['gross']-=delta*mid;attribution[label]['fees']+=calc['fee'];attribution[label]['execution_cost']+=cost
                if r['leg']=='OPEN':
                    marks={a:current_mark(w,a,t)[0] for a in SYMS};nav=D(10000)+sum((a.wallet+a.unrealized(marks[sym]) for sym,a in hand.items()),Z)
                    need(nav>0 and all(abs(hand[a].quantity)*marks[a]<=D('.3')*nav for a in SYMS)
                        and sum((abs(hand[a].quantity)*marks[a] for a in SYMS),Z)<=D('.6')*nav,'Postcost absolute perasset/gross caps cannot net away')
            same(free+sum(margin.values(),Z)-liability,D(10000)+sum((h.wallet for h in hand.values()),Z),'Shared wallet no notional double credit/debit',maximum)
            need(free>=0 and all(x>=0 for x in margin.values()),'No hidden negative free/margin balance')
            save(t)
    return dict(hand=hand,free=free,margin=margin,liability=liability,states=snapshots,cost=exec_cost,turnover=turnover,owned=owned,attribution=attribution)

def sample(states,times,side='right'):
    ix=np.searchsorted(np.asarray([s['t'] for s in states],dtype=np.int64),times,side=side)-1
    need(np.all(ix>=0),'Initial cash observation retained')
    def arr(k):return np.asarray([s[k] for s in states],dtype=float)[ix]
    return {k:arr(k) for k in ('wallet','free','liability','fees','funding','cost','turnover','q','entry','margin')}

def nav_values(w,times,state):
    marks=np.column_stack([w['market'][s]['mark'][np.clip((np.asarray(times)-w['start'])//MIN-1,0,w['count']-1)] for s in SYMS])
    return state['wallet']+(state['q']*(marks-state['entry'])).sum(axis=1),marks

def audit_case(w,case,g,ref,run,target_expected,target_witness,maximum):
    artifacts=case['artifacts'];paths={k:payload(v,run) for k,v in artifacts.items()}
    summary=case['summary'];minute=pl.read_parquet(paths['minute_nav_inventory.parquet']);daily=pl.read_parquet(paths['daily_nav.parquet'])
    targets=pl.read_parquet(paths['targets.parquet']);trades=json.loads(paths['trades.json'].read_bytes());funds=json.loads(paths['funding.json'].read_bytes())
    need(targets.columns==target_expected.columns and targets.height==target_expected.height,'Same complete target schema/count')
    causal_keys=('available_us','symbol','raw_signed_target','mode')
    for i,(observed,expected) in enumerate(zip(targets.select(*causal_keys).iter_rows(),target_expected.select(*causal_keys).iter_rows(),strict=True)):
        if observed!=expected:
            raise ValueError('STRICT_SMA_TARGET_DISAGREEMENT_NO_EPSILON_REPAIR '+json.dumps(dict(actual=observed,expected=expected,independent_witness=target_witness[i])))
    same(targets['target_weight'],target_expected['target_weight'],'Independent signed covariance targets',maximum,RATIO_TOL)
    need(minute.height==summary['completed_minutes']<=w['count']==summary['required_minutes']
        and minute['close_us'].to_list()==list(range(w['start']+MIN,w['start']+(minute.height+1)*MIN,MIN)),'All saved score minutes contiguous, not removed/repaired')
    complete=minute.height==w['count']
    need(not complete or len(funds)==len(w['events']),'Complete calendar keeps all original funding events including unowned')
    need(case['mode']!='CASH' or not trades,'Cash reference has no invented fills')
    calc=financial_journals(w,case,trades,funds,ref,maximum);states=calc['states'];times=minute['close_us'].to_numpy()
    sampled=sample(states,times);nav,marks=nav_values(w,times,sampled);q=sampled['q'];notionals=q*marks;gross=np.abs(notionals).sum(axis=1)
    need(np.all(nav>0),'Recorded nonhalted minute NAV positive')
    need(case['mode'] not in ('LONG_ONLY','CASH') or np.all(q>=0),'No forbidden short at any minute')
    need(case['mode'] not in ('SHORT_ONLY','CASH') or np.all(q<=0),'No forbidden long at any minute')
    for name,value in dict(nav=nav,free_cash=sampled['free'],isolated_balance=sampled['margin'].sum(axis=1),
        gross_notional=gross,net_signed_notional=notionals.sum(axis=1),cumulative_fees=sampled['fees'],
        cumulative_execution_costs=sampled['cost'],cumulative_funding=sampled['funding'],cumulative_turnover=sampled['turnover'],
        gross_weight=gross/nav,net_signed_weight=notionals.sum(axis=1)/nav).items():
        same(minute[name],value,'Every minute '+name,maximum,RATIO_TOL if 'weight' in name else CASH_TOL)
    for i,s in enumerate(SYMS):
        equity=sampled['margin'][:,i]+q[:,i]*(marks[:,i]-sampled['entry'][:,i])
        for name,value in {'_quantity':q[:,i],'_signed_marked_notional':notionals[:,i],
            '_isolated_balance':sampled['margin'][:,i],'_isolated_equity':equity,'_signed_weight':notionals[:,i]/nav}.items():
            same(minute[s+name],value,'Every minute '+s+name,maximum,RATIO_TOL if name in ('_quantity','_signed_weight') else CASH_TOL)
        need(np.all((q[:,i]==0)|(equity>np.abs(notionals[:,i])*.005)),'No completed minute silently continues through assumed margin halt')
    mask=times%DAY==0;endpoints=nav[mask]
    need(daily.height==len(endpoints) and daily['day_end_us'].to_list()==times[mask].tolist(),'Continuous daily endpoints, no reset')
    same(daily['nav'],endpoints,'Daily NAV',maximum)
    for key,source in [('fees','fees'),('execution_costs','cost'),('turnover','turnover')]:
        values=sampled[source][mask];same(daily[key],np.diff(np.r_[0.,values]),'Daily actual '+key,maximum)
    # Sparse AFTER-leg/funding observations plus both sides of every mark/funding
    # boundary retain intermediate risk losses that minute/daily endpoints omit.
    stop=summary.get('stop_us');last=w['end'] if stop is None else int(stop)
    need(w['start']<=last<=w['end'] and all(r['event_us']<=last for r in trades+funds),'Actual stopped prefix never trades/funds after stop')
    mark_times=np.arange(w['start']+MIN,min(last,w['end'])+1,MIN,dtype=np.int64)
    pre=sample(states,mark_times,'left');post=sample(states,mark_times,'right')
    pre_nav,_=nav_values(w,mark_times,pre);post_nav,_=nav_values(w,mark_times,post)
    events=np.asarray([s['t'] for s in states[1:]],dtype=np.int64)
    event_state={k:np.asarray([s[k] for s in states[1:]],dtype=float) for k in sampled}
    event_nav,_=nav_values(w,events,event_state) if len(events) else (np.array([]),None)
    obs=sorted([(w['start']-1,-1,10000.)]+[(int(t),0,float(n)) for t,n in zip(mark_times,pre_nav)]
        +[(int(t),i+1,float(n)) for i,(t,n) in enumerate(zip(events,event_nav))]
        +[(int(t),len(events)+1,float(n)) for t,n in zip(mark_times,post_nav)])
    curve=np.asarray([r[2] for r in obs]);mdd=float(np.max(1-curve/np.maximum.accumulate(curve),initial=0.))
    same(summary['all_observation_max_drawdown'],mdd,'All observed mark/fund/leg MDD including initial cash',maximum,RATIO_TOL)
    terminal_marks={s:current_mark(w,s,last)[0] for s in SYMS};hand=calc['hand']
    terminal_nav=D(10000)+sum((h.wallet+(h.unrealized(terminal_marks[s]) if h.quantity else Z) for s,h in hand.items()),Z)
    totals=dict(NAV=terminal_nav,free_cash=calc['free'],isolated_balance=sum(calc['margin'].values(),Z),unpaid_liability=calc['liability'],
        net_PnL=terminal_nav-10000,fees_USDT=sum((h.fees for h in hand.values()),Z),funding_USDT=sum((h.funding_cash for h in hand.values()),Z),
        realized_PnL=sum((h.realized for h in hand.values()),Z),execution_cost_USDT=calc['cost'],gross_fill_turnover_USDT=calc['turnover'])
    totals['unrealized_PnL']=sum((h.unrealized(terminal_marks[s]) if h.quantity else Z for s,h in hand.items()),Z)
    totals['gross_PnL_same_quantities']=totals['realized_PnL']+totals['unrealized_PnL']+calc['cost']
    for key,value in totals.items():same(exact(summary,key),value,'Final shared-account '+key,maximum)
    same(exact(summary,'accounting_bridge_error_USDT'),0.,'Final capital/PnL bridge',maximum)
    terminal_gross=Z
    for s,h in hand.items():
        p=summary['positions'][s];same(exact(p,'quantity'),h.quantity,'Terminal signed q',maximum,RATIO_TOL)
        same(exact(p,'entry_price'),h.entry_fill,'Terminal original remaining entry fill',maximum)
        same(exact(p,'isolated_balance'),calc['margin'][s],'Terminal isolated reserve',maximum)
        if h.quantity:
            label='LONG' if h.quantity>0 else 'SHORT';calc['attribution'][label]['gross']+=h.quantity*terminal_marks[s]
            terminal_gross+=abs(h.quantity)*terminal_marks[s]
    same(summary['terminal_marked_notional'],terminal_gross,'Actual marked inventory not assumed cash/dust',maximum)
    months=[];previous=np.array([10000.,0.,0.,0.]);dates=[datetime.fromtimestamp(int(t)/1e6,UTC).strftime('%Y-%m') for t in times[mask]-1]
    for month in dict.fromkeys(dates):
        j=max(i for i,m in enumerate(dates) if m==month);index=np.flatnonzero(mask)[j]
        current=np.array([nav[index],sampled['fees'][index],sampled['cost'][index],sampled['funding'][index]])
        net,fee,cost,funding=current-previous
        months.append(dict(month=month,days=dates.count(month),net_PnL=float(net),fees=float(fee),spread_cost=float(cost/2),slippage_cost=float(cost/2),
            funding_USDT=float(funding),gross_PnL=float(net+fee+cost-funding),ending_NAV=float(nav[index]),ending_signed_quantities=dict(zip(SYMS,map(float,q[index])))))
        previous=current
    need([m['month'] for m in summary['months']]==[m['month'] for m in months],'Every saved month, no selected window')
    for a,b in zip(summary['months'],months,strict=True):
        need(a['days']==b['days'],'Month complete observation day count')
        for key in ('net_PnL','fees','spread_cost','slippage_cost','funding_USDT','gross_PnL','ending_NAV'):same(a[key],b[key],'Month '+key,maximum)
        for s in SYMS:same(a['ending_signed_quantities'][s],b['ending_signed_quantities'][s],'Month signed q',maximum,RATIO_TOL)
    need(complete==(summary['completion']=='COMPLETE_CONDITIONAL_ACCOUNT'),'Honest incomplete/halt scope')
    minute_dd=float(np.max(1-np.r_[10000.,nav]/np.maximum.accumulate(np.r_[10000.,nav]),initial=0.))
    daily_dd=float(np.max(1-np.r_[10000.,endpoints]/np.maximum.accumulate(np.r_[10000.,endpoints]),initial=0.))
    metrics=None
    exposure=dict(minute_mean_gross_weight=float(np.mean(gross/nav)) if len(nav) else None,
        minute_max_gross_weight=float(np.max(gross/nav)) if len(nav) else None,
        minute_mean_net_signed_weight=float(np.mean(notionals.sum(axis=1)/nav)) if len(nav) else None,
        per_asset={s:dict(mean_absolute_weight=float(np.mean(np.abs(notionals[:,i])/nav)) if len(nav) else None,
            maximum_absolute_weight=float(np.max(np.abs(notionals[:,i])/nav)) if len(nav) else None,
            above_cap_minutes=int(np.sum(np.abs(notionals[:,i])/nav>.3))) for i,s in enumerate(SYMS)},
        scope='RECORDED_MINUTE_SNAPSHOTS_ONLY_NOT_MATCHED_REALIZED_RISK')
    concentration=None
    if complete:
        r=endpoints/np.r_[10000.,endpoints[:-1]]-1;vol=float(np.std(r,ddof=1)*math.sqrt(365))
        metrics=dict(days=w['days'],initial_nav=10000.,final_nav=float(endpoints[-1]),total_return=float(endpoints[-1]/10000-1),
            annual_return=float((endpoints[-1]/10000)**(365/w['days'])-1),annual_volatility=vol,
            sharpe=float(np.mean(r)*365/vol) if vol>0 else 0.,max_drawdown=daily_dd,
            fees=float(sampled['fees'][-1]),execution_costs=float(sampled['cost'][-1]),turnover=float(sampled['turnover'][-1]))
        for key,v in metrics.items():same(summary['daily_metrics'][key],v,'Saved descriptive daily metrics '+key,maximum,RATIO_TOL if key in ('annual_return','annual_volatility','sharpe','max_drawdown','total_return') else CASH_TOL)
        same(summary['minute_max_drawdown'],minute_dd,'Minute MDD distinct from daily/event',maximum,RATIO_TOL)
        observed=summary['realized_exposure']
        signed=notionals.sum(axis=1)/nav;collateral=sampled['margin'].sum(axis=1)
        for key,value in dict(minute_mean_gross_weight=exposure['minute_mean_gross_weight'],minute_max_gross_weight=exposure['minute_max_gross_weight'],
            minute_mean_net_signed_weight=exposure['minute_mean_net_signed_weight'],minute_min_net_signed_weight=float(np.min(signed)),minute_max_net_signed_weight=float(np.max(signed)),
            minute_mean_isolated_collateral_over_initial_capital=float(np.mean(collateral/10000)),minute_max_isolated_collateral_over_initial_capital=float(np.max(collateral/10000)),
            minute_mean_isolated_collateral_over_NAV=float(np.mean(collateral/nav)),minute_max_isolated_collateral_over_NAV=float(np.max(collateral/nav)),
            minimum_recorded_minute_free_cash_USDT=float(min(10000.,np.min(sampled['free'])))).items():
            same(observed[key],value,'Recorded realized exposure '+key,maximum,CASH_TOL if key.endswith('USDT') else RATIO_TOL)
        delta=np.diff(np.r_[10000.,endpoints]);positive=delta[delta>0];positive_sum=float(np.sum(positive));absolute=float(np.abs(delta).sum())
        concentration=dict(positive_days=len(positive),total_days=len(delta),positive_gain_USDT=positive_sum,absolute_daily_net_delta_USDT=absolute,
            top5_positive_day_share=float(np.sort(positive)[-5:].sum()/positive_sum) if positive_sum else None,
            largest_absolute_day_share=float(np.abs(delta).max()/absolute) if absolute else None)
        for key,value in concentration.items():
            if value is None:need(summary['daily_net_gain_concentration'][key] is None,'Undefined flat concentration retained')
            else:same(summary['daily_net_gain_concentration'][key],value,'Daily net concentration '+key,maximum,RATIO_TOL if key.endswith('share') else CASH_TOL)
    else:need(summary['daily_metrics'] is None and summary['minute_max_drawdown'] is None,'Halt cannot masquerade as completed return metrics')
    attribution={}
    for label,values in calc['attribution'].items():
        values['net_contribution']=values['gross']-values['fees']-values['execution_cost']+values['funding']
        attribution[label]={k:float(v) for k,v in values.items()}
        for key,value in values.items():same(summary['long_short_marked_contribution'][label][key],value,'Signed actual contribution '+label+' '+key,maximum)
    same(sum(v['net_contribution'] for v in attribution.values()),totals['net_PnL'],'Long+short contributions total actual net',maximum)
    need(summary['funding_original_events']==len(w['events']) and summary['funding_observed_events']==len(funds)
        and summary['funding_owned_events']==calc['owned'] and summary['funding_deferred_after_halt_events']==len(w['events'])-len(funds),'Actual original/owned/deferred event counts')
    need(case['mode'] not in ('LONG_ONLY','CASH') or all(h.quantity>=0 for h in hand.values()),'Forbidden terminal short')
    need(case['mode'] not in ('SHORT_ONLY','CASH') or all(h.quantity<=0 for h in hand.values()),'Forbidden terminal long')
    return dict(id=case['id'],period=case['period'],mode=case['mode'],cost_id=case['cost_id'],unit_id=case['unit_id'],
        complete_calendar_verified=complete,completed_minutes_verified=minute.height,completed_days_verified=daily.height,
        completed_months_verified=len(months),completed_fills_verified=len(trades),original_funding_events=len(w['events']),
        observed_funding_events=len(funds),owned_events=calc['owned'],summary={k:float(v) for k,v in totals.items()},
        minute_max_drawdown=minute_dd,daily_max_drawdown=daily_dd,all_observation_max_drawdown=mdd,
        actual_terminal_marked_notional=float(terminal_gross),terminal_cash_realized=terminal_gross==0,
        long_short_marked_contribution=attribution,months=months,daily_metrics_descriptive=metrics,
        realized_exposure=exposure,daily_net_gain_concentration=concentration,
        full_market_frozen_order_quantity_sizing_independently_rebuilt=False,
        sizing_evidence_scope='PINNED_CONTROLLER_AND_PASSED_NEW_CAUSAL_CASE_ONLY_NO_ORDER_KIND_OR_FROZEN_INTENT_JOURNAL',
        ledger_artifact_hashes={k:v['sha256'] for k,v in artifacts.items()},
        realized_risk_is_not_matched_across_modes=True,conditional_funding_unit_not_certified=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','actual','run-dir','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();g=module(GUARD,'perpetual_independent_guards',GUARD_SHA);ref=module(REFERENCE,'perpetual_independent_hand',REFERENCE_SHA)
    need(os.getenv('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and pl.thread_pool_size()<=2,'Clean bounded progress CPU2 runtime')
    need(args.run_dir.parent==STATE and args.run_dir.is_dir() and not args.run_dir.is_symlink()
        and {p.name for p in args.run_dir.iterdir()}=={'ACTUAL_BINDING.json'} and args.output.parent==ROOT/'reports/fast_research'
        and not args.output.exists(),'New prebound manifest-only audit STATE and output')
    plan,plan_sha=g.small(args.run_dir/'ACTUAL_BINDING.json');own=sha(__file__)
    need(plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['protocol_path']==str(args.protocol.relative_to(ROOT))
        and plan['actual_report']==str(args.actual.relative_to(ROOT)),'Exact independent invocation frozen after actual completion')
    need(plan['tolerances']==dict(cash_USDT=CASH_TOL,ratio=RATIO_TOL),'Tolerance frozen before real financial reads')
    binding=dict(task_id=os.getenv('COIN_TASK_ID'),checker_sha256=own,ACTUAL_BINDING_sha256=plan_sha,
        actual_reports={str(args.actual):plan['actual_report_sha256']},source_hashes=plan['source_hashes'])
    g.write(args.run_dir/'RUN_BINDING.json',binding);began=time.monotonic();before=resources.status();maximum=dict(cash=0.,ratio=0.);rows=[]
    report=dict(status='FAIL_CONDITIONAL_PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDIT',binding=binding,run_dir=str(args.run_dir),
        run_binding_sha256=sha(args.run_dir/'RUN_BINDING.json'),independent_source_sha256=own,cases=rows,
        tolerances=plan['tolerances'],maximum_errors=maximum,financial_method='SPARSE_ARCHIVED_HANDLEDGER_DECIMAL_PLUS_INDEPENDENT_MARGIN_RESERVATION_AND_NUMPY_SNAPSHOTS',
        funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,candidate='NO_QUALIFIED_CANDIDATE',
        long_term_APR='NOT_EVALUABLE',source_QA_or_old_financial_suites_repeated=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
    report['full_market_frozen_order_quantity_sizing_independently_rebuilt']=False
    report['sizing_evidence_scope']='PINNED_CONTROLLER_PLUS_PASSED_NEW_CAUSAL_CASE; ORDER_KIND/FROZEN_INTENT_NOT_IN_SAVED_JOURNAL'
    error=None;progress=None
    try:
        g.bounded(before);spec,proto_sha=g.small(args.protocol,plan['protocol_sha256']);actual,actual_sha=g.small(args.actual,plan['actual_report_sha256'])
        need(actual['status']==ACTUAL_STATUS and actual['completed_cases']==actual['required_cases']==32
            and actual['binding']['task_id']==plan['actual_task_id'] and actual['binding']['protocol_sha256']==proto_sha
            and actual['binding']['source_hashes']==spec['frozen_sources'] and not actual['unit_certified'] and not actual['native_market_certified'], 'Complete32 actual fixed conditional scenarios')
        report['actual_task']=g.closed(plan['actual_task_id']);run=Path(spec['run_dir']);rb,rb_sha=g.small(run/'RUN_BINDING.json',actual['run_binding_sha256'])
        need(rb==actual['binding'],'Producer actual RUN_BINDING')
        hashes={str(args.protocol.relative_to(ROOT)):proto_sha,str(args.actual.relative_to(ROOT)):actual_sha}
        need(plan['source_hashes'].get(GUARD)==GUARD_SHA and plan['source_hashes'].get(REFERENCE)==REFERENCE_SHA,'Exact accepted independent math and guards')
        for name,digest in [*spec['frozen_sources'].items(),*plan['source_hashes'].items()]:
            need(name not in hashes or hashes[name]==digest,'No conflicting scientific source map');g.small(project(g,name),digest,False);hashes[name]=digest
        rules=spec['rules'];need(all(rules[k]==v for k,v in dict(initial_capital_USDT=10000.,annual_vol_target=.10,
            past_covariance_completed_days=30,asset_abs_cap=.3,gross_cap=.6,leverage=1,MMR=.005,sizing_buffer=.99,
            taker_fee_bps_per_side=5.5,participation_rate=.001,maximum_attempts=5).items()),'Original capital/covariance/caps/fee/capacity assumptions')
        need([(c['id'],c['half_spread_bps'],c['slippage_bps'],c['roundtrip_bps']) for c in spec['cost_scenarios']]==[(k,*v) for k,v in COSTS.items()]
            and [(u['id'],dec(u['scale'])) for u in spec['unit_scenarios']]==list(UNITS.items()),'Two fixed cost/unit scenarios, no inferred unit')
        manifest_ref=spec['input_manifest'];manifest,_=g.small(project(g,manifest_ref['path']),manifest_ref['sha256'])
        need(manifest['funding_rate_unit']=='UNCONFIRMED' and not manifest['funding_unit_certified'],'Input metadata does not certify units')
        trade_ref=spec['trade_source_acceptance'];acceptance,_=g.small(project(g,trade_ref['path']),trade_ref['sha256'])
        need(acceptance['status']==trade_ref['required_status'] and not acceptance.get('funding_unit_certified',False),'Exact already accepted new trade source only')
        smoke_ref=spec['required_smoke_receipt'];smoke,_=g.small(project(g,smoke_ref['path']),smoke_ref['sha256'])
        need(smoke['status']==smoke_ref['required_status'] and smoke.get('test_exit_code')==0 and smoke.get('source_bytes_unchanged') is True,'Already passed sole new route receipt')
        report['synthetic_task']=g.closed(smoke['binding']['task_id'])
        selectors=[f'{p}_{m}_{c}_{u}' for p in ('122D','90D') for m in MODES for c in COSTS for u in UNITS]
        need([c['id'] for c in actual['cases']]==selectors,'Exactly every predeclared paired scenario, no OOS selection')
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(32);progress.value['detail']='仅新条件多空账本：逐腿资金/分钟NAV；不认证资金费单位或原生执行'
        for window_spec,produced_inputs in zip(manifest['windows'],actual['input_windows'],strict=True):
            w=window_reader(manifest,window_spec)
            need(produced_inputs['id']==window_spec['id'] and produced_inputs['input_proofs']==w['proofs'],'Same exact accepted necessary financial source bindings')
            for mode in MODES:
                target,witness=target_reference(w,mode)
                for case in [c for c in actual['cases'] if c['period']==window_spec['id'] and c['mode']==mode]:
                    progress.update('独立逐腿与全部分钟快照',len(rows),32,'账户',period=case['period'],direction=mode,cost=case['cost_id'],funding_unit=case['unit_id'])
                    rows.append(audit_case(w,case,g,ref,run,target,witness,maximum));gc.collect()
                    need(time.monotonic()-began<=plan['budgets']['wall_seconds'] and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=plan['budgets']['peak_RSS_bytes'],'Independent frozen process budget')
            del w;gc.collect()
        for name,digest in hashes.items():g.small(project(g,name),digest,False)
        paired=[]
        for period in ('122D','90D'):
            for cost in COSTS:
                for unit in UNITS:
                    legs={r['mode']:r for r in rows if (r['period'],r['cost_id'],r['unit_id'])==(period,cost,unit)}
                    ls,long=legs['LONG_SHORT'],legs['LONG_ONLY'];difference=ls['summary']['net_PnL']-long['summary']['net_PnL']
                    short=ls['long_short_marked_contribution']['SHORT']['net_contribution']
                    long_change=ls['long_short_marked_contribution']['LONG']['net_contribution']-long['summary']['net_PnL']
                    same(difference,short+long_change,'Direction ablation short plus changed-long decomposition',maximum)
                    paired.append(dict(period=period,cost_id=cost,unit_id=unit,LONG_SHORT_minus_LONG_ONLY_net_USDT=difference,
                        LONG_SHORT_short_net_contribution_USDT=short,changed_long_net_contribution_USDT=long_change,
                        both_complete_calendars=ls['complete_calendar_verified'] and long['complete_calendar_verified'],
                        same_long_trade_timing_or_realized_risk_claimed=False))
        report.update(status=STATUS,verified_source_hashes=hashes,actual_report_sha256=actual_sha,actual_run_binding_sha256=rb_sha,
            required_cases=32,completed_cases_verified=32,completed_full_calendar_cases_verified=sum(r['complete_calendar_verified'] for r in rows),
            incomplete_or_halted_cases_verified=sum(not r['complete_calendar_verified'] for r in rows),paired_direction_ablation=paired,
            comparison_scope='SAME_INDICATORS_HOOKS_CADENCE_PRODUCT_COSTS_INPUTS; MODE_STATE_CHANGES_TIMING_CAPITAL_AND_NAV_SIZING; NOT_SIGN_INVERTED_OLD_RETURNS')
    except Exception as caught:
        error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        report.update(completed_cases_verified=len(rows),elapsed_seconds=time.monotonic()-began,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resources_before=before,resources_after=resources.status(),own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        try:g.bounded(report['resources_after'])
        except Exception as caught:error=error or caught;report.update(status='FAIL_CONDITIONAL_PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDIT',budget_error=str(caught))
        if report['elapsed_seconds']>plan['budgets']['wall_seconds'] or report['peak_RSS_bytes']>plan['budgets']['peak_RSS_bytes']:
            error=error or RuntimeError('Independent resource limit');report.update(status='FAIL_CONDITIONAL_PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDIT',budget_error=str(error))
        digest,size=g.write(args.output,report)
        need(sum(p.stat().st_size for p in args.run_dir.iterdir() if p.is_file())+size<=plan['budgets']['new_owned_bytes'],'Only small independent metadata outputs')
        print(json.dumps(dict(status=report['status'],report=str(args.output),sha256=digest,completed_cases=len(rows))),flush=True)
    if error:raise error

if __name__=='__main__':main()
