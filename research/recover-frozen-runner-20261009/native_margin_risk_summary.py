"""Offline isolated-margin diagnostics from complete saved native journals.

No account/simulator construction, execution, market reads, download or policy
change. Dollar and normalized headroom, price distance and near observations
are summarized by the actual filled position lifetime, including pre-takeover.
"""
import argparse,hashlib,json,re,sys
from datetime import datetime,UTC
from decimal import Decimal as D,localcontext
from pathlib import Path
import numpy as np
import polars as pl
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'src'))
from quant.bybit_isolated_account import liquidation_price,validated_tiers
MINUTE=60_000_000
SOURCES={
 'scripts/investment/resumable_perpetual.py':'318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585',
 'src/quant/bybit_isolated_account.py':'d82cfca41a76f12aea60ea2608a5c5d26670d7c55394cb07619b69fdffd2619a',
 'src/quant/perpetual_account.py':'ffa57a4c3c3b031945fcbc5db429d8b5e6ef06e880a8a577265836602ad55110'}
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=lambda p:dict(bytes=p.stat().st_size,sha256=sha(p))
def need(ok,message):
    if not ok:raise ValueError(message)
def utc(t):return datetime.fromtimestamp(t/1e6,UTC).isoformat()
def encode(o):return (json.dumps(o,indent=2,allow_nan=False)+'\n').encode()


def scalar_risk(quantity,entry,collateral,mark,*,leverage=1,fee='.00055',mmr='.005',deduction=0):
    """Exact source price helper; free cash is intentionally not an input."""
    q,e,c,p,l,f,m,d=map(lambda x:D(str(x)),(quantity,entry,collateral,mark,leverage,fee,mmr,deduction))
    need(c>=0 and p>0 and l>0 and 0<=m<1 and 0<=f<1 and d>=0,'Invalid margin diagnostic inputs')
    if q==0:
        need(c==0 and e==0,'Flat position must have zero basis and collateral')
        return dict(side='FLAT',quantity='0',entry_price='0',isolated_collateral='0',mark_price=str(p),isolated_equity='0',maintenance='0',margin_headroom=None,normalized_margin_headroom=None,engine_trigger_headroom=None,liquidation_price=None,adverse_price_distance=None,positive_price_trigger=False,threshold_crossed=False)
    need(e>0,'Held position requires positive entry')
    with localcontext() as ctx:
        ctx.prec=40;side=1 if q>0 else -1;amount=abs(q);extra=c-amount*e/l
        lp=liquidation_price(e,amount,l,extra,m,f,d,'LONG' if q>0 else 'SHORT')
        equity=c+q*(p-e);maintenance=amount*p*m-d;headroom=equity-maintenance
        trigger_buffer=side*(p-lp)*amount*(1-side*m)
        distance=side*(p-lp)/p if lp>0 else None
        return dict(side='LONG' if q>0 else 'SHORT',quantity=str(q),entry_price=str(e),isolated_collateral=str(c),mark_price=str(p),isolated_equity=str(equity),maintenance=str(maintenance),margin_headroom=str(headroom),normalized_margin_headroom=str(headroom/(amount*p)),engine_trigger_headroom=str(trigger_buffer),liquidation_price=str(lp),adverse_price_distance=None if distance is None else str(distance),positive_price_trigger=lp>0,threshold_crossed=p<=lp if q>0 else p>=lp)


def vector_risk(q,e,c,p,l,f,m,d,*,price_override=None):
    """Array form of the pinned liquidation_price expressions; held rows only."""
    amount=np.abs(q);side=np.sign(q);extra=c-amount*e/l
    lp=(e*amount-side*e*amount/l-side*extra/(1-side*f)-side*d)/(amount*(1-side*m)) if price_override is None else price_override
    equity=c+q*(p-e);maintenance=amount*p*m-d;headroom=equity-maintenance
    distance=np.where(lp>0,side*(p-lp)/p,np.nan)
    return dict(margin_headroom=headroom,normalized_margin_headroom=headroom/(amount*p),engine_trigger_headroom=side*(p-lp)*amount*(1-side*m),liquidation_price=lp,adverse_price_distance=distance,equity=equity,maintenance=maintenance)


def tier_at(rows,notional):
    return next((r for r in rows if r['riskLimitValue'] is None or notional<=D(r['riskLimitValue'])),rows[-1])
def tiers_vector(rows,notional):
    m=np.full(len(notional),float(rows[-1]['maintenanceMargin']));d=np.full(len(notional),float(rows[-1]['mmDeduction']));unassigned=np.ones(len(notional),bool)
    for r in rows:
        ix=unassigned if r['riskLimitValue'] is None else unassigned&(notional<=float(r['riskLimitValue']))
        m[ix]=float(r['maintenanceMargin']);d[ix]=float(r['mmDeduction']);unassigned[ix]=False
    return m,d


def new_lifetime(symbol,index,t,side):
    return dict(id=f'{symbol}:{index}:{t}',symbol=symbol,side=side,start_us=t,start_UTC=utc(t),end_us=None,end_UTC=None,closing_cause=None,minute_observations=0,event_observations=0,near_minute_observations=0,near_event_observations=0,crossed_minute_observations=0,crossed_event_observations=0,actual_liquidations=0,partial_liquidation_instructions=0,minimum_margin_headroom=None,minimum_normalized_margin_headroom=None,minimum_engine_trigger_headroom=None,minimum_adverse_price_distance=None,near_minute_intervals=[],actual_liquidation_witnesses=[])


def update_minima(life,metrics,witness):
    for field in ('margin_headroom','normalized_margin_headroom','engine_trigger_headroom','adverse_price_distance'):
        value=metrics[field]
        if value is None:continue
        key='minimum_'+field
        if life[key] is None or D(str(value))<D(str(life[key]['value'])):life[key]=dict(value=str(value),witness=witness)


def summarize(directory,label,near_distance=.05):
    for name,h in SOURCES.items():need(sha(REPO/name)==h,'Pinned original financial source differs: '+name)
    need(0<near_distance<1 and re.fullmatch('[A-Za-z0-9_]{1,64}',label),'Explicit label and diagnostic distance in(0,1) required')
    names=('summary.json','trades.json','funding.json','liquidations.json','minute_nav_inventory.parquet');inputs={n:record(directory/n) for n in names};summary=read(directory/'summary.json');trades=read(directory/'trades.json');funds=read(directory/'funding.json');liqs=read(directory/'liquidations.json');minute=pl.read_parquet(directory/'minute_nav_inventory.parquet')
    contract=summary['contract'];symbols=tuple(summary['symbols']);times=minute['close_us'].to_numpy()
    need(contract['version']=='bybit_style_isolated_bankruptcy_takeover_v1' and contract['margin_mode']=='ISOLATED' and contract['market_type']=='LINEAR_USDT_PERPETUAL' and contract['contract_multiplier']==1 and contract['quantity_asset']=='BASE','Supported frozen native isolated linear product required')
    need(np.array_equal(np.diff(times),np.full(len(times)-1,MINUTE)) and len(times)==summary['completed_minutes'],'Complete consecutive saved minute grid required')
    need(all(minute[s+'_quantity'][0]==0 and minute[s+'_isolated_balance'][0]==0 for s in symbols),'Complete fresh-account journals required')
    need(all(contract['instrument_profiles'][s]['quantity_asset']=='BASE' and D(contract['instrument_profiles'][s]['contract_multiplier'])==1 for s in symbols),'Unsupported quantity or multiplier units')
    leverage=D(str(contract['leverage']));fee=D(str(contract['taker_fee_bps_per_side']))/10000;tiers={s:validated_tiers(contract['risk_tiers'][s]) for s in symbols};witnesses={r['id']:r for r in liqs}
    need(len(witnesses)==len(liqs),'Duplicate liquidation witness')
    positions={s:dict(q=D(0),e=D(0),c=D(0),life=None) for s in symbols};lives=[];state_tapes={s:[(int(times[0])-MINUTE-1,D(0),D(0),D(0),-1)] for s in symbols};free=D(str(minute['free_cash'][0]));initial=free;free_tape=[(int(times[0])-MINUTE-1,float(free))];seen_liqs=set();min_free=free;funding_margin_debits=0
    stream=sorted([(r['event_us'],-1 if r.get('liquidation_takeover') and witnesses[r['fill_id']]['phase']=='MARK_OBSERVATION' else 1,i,'trade',r) for i,r in enumerate(trades)]+[(r['event_us'],0,i,'funding',r) for i,r in enumerate(funds)],key=lambda r:r[:3])
    def observe(s,t,phase,mark,actual=None):
        p=positions[s]
        if not p['q']:return
        tier=tier_at(tiers[s],abs(p['q'])*mark);metrics=scalar_risk(p['q'],p['e'],max(D(0),p['c']),mark,leverage=leverage,fee=fee,mmr=tier['maintenanceMargin'],deduction=tier['mmDeduction']);life=lives[p['life']]
        w=dict(event_us=t,event_UTC=utc(t),phase=phase,precision='DECIMAL_RECEIPT_DELTAS;ORIGINAL_STATE_RECONCILIATION_TOLERANCE_1E-24',account_free_cash=str(free),metrics=metrics)
        update_minima(life,metrics,w);life['event_observations']+=1;distance=metrics['adverse_price_distance'];life['near_event_observations']+=int(distance is not None and 0<D(distance)<=D(str(near_distance)));life['crossed_event_observations']+=int(metrics['threshold_crossed'])
        if actual is not None:
            need(metrics['threshold_crossed'],'Original takeover must cross unchanged engine price threshold')
            life['actual_liquidations']+=1;life['actual_liquidation_witnesses'].append(dict(original=actual,risk=w))
    with localcontext() as ctx:
        ctx.prec=50
        for t,priority,index,kind,r in stream:
            s=r['symbol'];p=positions[s];x=r.get('decimal_strings',{})
            if kind=='funding':
                need(abs(p['q']-D(str(r['quantity'])))<D('1e-10'),'Funding quantity differs from recorded fill history');mark=None if r['mark_price'] is None else D(x.get('mark_price',str(r['mark_price'])))
                if p['q']:need(mark is not None and r['mark_close_us']<t,'Held funding requires strictly prior saved mark')
                if mark is not None:observe(s,t,'BEFORE_FUNDING',mark)
                amount=D(x.get('signed_funding_USDT',str(r['signed_funding_USDT'])))
                if amount>=0:free+=amount
                else:
                    paid=min(free,-amount);free-=paid;rest=-amount-paid;own=min(p['c'],rest);p['c']-=own;funding_margin_debits+=int(own>0);need(rest-own<=D('1e-24'),'Unpaid liability not supported by this completed-account diagnostic')
                if mark is not None:observe(s,t,'AFTER_FUNDING',mark)
            else:
                need(p['q']==D(x['quantity_before']) and abs(p['e']-D(x['entry_price_before']))<=D('1e-24'),'Recorded quantity/basis continuity differs')
                actual=witnesses[r['fill_id']] if r.get('liquidation_takeover') else None
                if actual is not None:
                    need(actual['quantity']==x['quantity_before'] and abs(p['c']-D(actual['isolated_margin_lost']))<=D('1e-24') and actual['event_us']==t,'Liquidation pre-position/collateral differs');seen_liqs.add(actual['id'])
                mark=D(x['mark_price'])
                if actual is not None:need(mark==D(actual['mark_price']) and abs(p['e']-D(actual['entry_price']))<=D('1e-24'),'Original takeover mark/basis differs')
                observe(s,t,'ACTUAL_LIQUIDATION_BEFORE_TAKEOVER' if actual else 'BEFORE_RECORDED_FILL',mark,actual)
                old_q=p['q'];p['q']+=D(x['position_delta']);p['e']=D(x['entry_price_after']);p['c']+=D(x['isolated_balance_delta']);free+=D(x['free_cash_delta']);need(free>=0 and p['c']>=-D('1e-24'),'Negative saved cash/collateral')
                if old_q and not p['q']:
                    life=lives[p['life']];life.update(end_us=t,end_UTC=utc(t),closing_cause='LIQUIDATION' if actual else 'NORMAL_PAID_CLOSE');p['life']=None;need(abs(p['c'])<=D('1e-24'),'Flat collateral residual');p['c']=D(0)
                elif not old_q and p['q']:
                    p['life']=len(lives);lives.append(new_lifetime(s,sum(l['symbol']==s for l in lives),t,'LONG' if p['q']>0 else 'SHORT'))
                else:need(not old_q or old_q*p['q']>0,'Unclosed reversal in fill journal')
                if r.get('exchange_liquidation_instruction') and p['life'] is not None:lives[p['life']]['partial_liquidation_instructions']+=1
                observe(s,t,'AFTER_RECORDED_FILL',mark)
            min_free=min(min_free,free);state_tapes[s].append((t,p['q'],p['e'],max(D(0),p['c']),-1 if p['life'] is None else p['life']));free_tape.append((t,float(free)))
    need(seen_liqs==set(witnesses) and len(liqs)==summary['liquidation_count'],'All original liquidation events required')
    fc=np.asarray(free_tape);fi=np.searchsorted(fc[:,0],times,side='right')-1;free_error=float(np.max(np.abs(fc[fi,1]-minute['free_cash'].to_numpy())));need(free_error<1e-8,'Saved minute free cash differs from receipt deltas')
    errors={};flat_rows=0
    for s in symbols:
        a=np.asarray(state_tapes[s],dtype=float);ix=np.searchsorted(a[:,0],times,side='right')-1;q,e,c,ids=(a[ix,j] for j in range(1,5));actual_q=minute[s+'_quantity'].to_numpy();actual_c=minute[s+'_isolated_balance'].to_numpy();eq=minute[s+'_isolated_equity'].to_numpy();notional=minute[s+'_signed_marked_notional'].to_numpy();active=q!=0;flat_rows+=int((~active).sum())
        qerror=float(np.max(np.abs(actual_q-q)));cerror=float(np.max(np.abs(actual_c-c)));need(qerror<1e-8 and cerror<1e-8 and (ids[active]>=0).all(),'Saved minute position/collateral lifetime differs')
        need(np.all(actual_q[~active]==0) and np.all(actual_c[~active]==0) and np.all(eq[~active]==0),'Flat observations cannot retain collateral/equity')
        held=np.flatnonzero(active);p=notional[held]/q[held];need(np.isfinite(p).all() and (p>0).all(),'Held mark must be recoverable from saved notional/quantity');m,d=tiers_vector(tiers[s],np.abs(notional[held]));lp=np.zeros(len(held))
        # Evaluate price once per exact receipt state/tier, never from rounded
        # Float64 collateral-minus-entry-notional cancellation near a 1x long.
        for state_id in np.unique(ix[held]):
            selected=ix[held]==state_id;state=state_tapes[s][int(state_id)];sq,se,sc=state[1:4]
            for tier in tiers[s]:
                selected_tier=selected&(m==float(tier['maintenanceMargin']))&(d==float(tier['mmDeduction']))
                if selected_tier.any():lp[selected_tier]=float(scalar_risk(sq,se,sc,1,leverage=leverage,fee=fee,mmr=tier['maintenanceMargin'],deduction=tier['mmDeduction'])['liquidation_price'])
        metrics=vector_risk(q[held],e[held],actual_c[held],p,float(leverage),float(fee),m,d,price_override=lp);eqerror=float(np.max(np.abs(eq[held]-metrics['equity']))) if len(held) else 0.;need(eqerror<1e-8,'Saved isolated equity differs from source formula');errors[s]=dict(quantity=qerror,collateral_USDT=cerror,equity_USDT=eqerror)
        for life_id in np.unique(ids[held]).astype(int):
            life=lives[life_id];sub=np.flatnonzero(ids[held]==life_id);rows=held[sub];life['minute_observations']=len(rows)
            def witness(k):
                row=int(held[k]);tier=tier_at(tiers[s],D(str(abs(notional[row]))));state=state_tapes[s][int(ix[row])];risk=scalar_risk(*state[1:4],p[k],leverage=leverage,fee=fee,mmr=tier['maintenanceMargin'],deduction=tier['mmDeduction'])
                return dict(event_us=int(times[row]),event_UTC=utc(int(times[row])),phase='SAVED_MINUTE_CLOSE',precision='FLOAT64_MARK_FROM_SAVED_SIGNED_NOTIONAL_DIV_QUANTITY;DECIMAL_RECEIPT_STATE_AND_SOURCE_PRICE_HELPER',account_free_cash=str(float(minute['free_cash'][row])),metrics=risk)
            for field in ('margin_headroom','normalized_margin_headroom','engine_trigger_headroom','adverse_price_distance'):
                valid=sub[np.isfinite(metrics[field][sub])]
                if len(valid):k=int(valid[np.argmin(metrics[field][valid])]);w=witness(k);update_minima(life,w['metrics'],w)
            distance=metrics['adverse_price_distance'][sub];near=np.isfinite(distance)&(distance>0)&(distance<=near_distance);crossed=np.isfinite(distance)&(distance<=0);life['near_minute_observations']=int(near.sum());life['crossed_minute_observations']=int(crossed.sum())
            positions_near=np.flatnonzero(near)
            if len(positions_near):
                groups=np.split(positions_near,np.flatnonzero(np.diff(times[rows[positions_near]])!=MINUTE)+1)
                for g in groups:
                    k=int(sub[g[np.argmin(distance[g])]]);life['near_minute_intervals'].append(dict(first_us=int(times[rows[g[0]]]),last_us=int(times[rows[g[-1]]]),observations=len(g),minimum_adverse_distance=str(witness(k)['metrics']['adverse_price_distance'])))
    need(all(l['end_us'] is not None for l in lives) and all(not p['q'] and not p['c'] for p in positions.values()),'Complete original paid-flat account required; no invented terminal close')
    source_final=summary.get('decimal_strings',{});final_free=D(source_final.get('free_cash',str(summary.get('free_cash',float(free)))));final_nav=D(source_final.get('NAV',str(summary.get('NAV',float(free)))));source_pnl=D(source_final.get('net_PnL',str(summary['net_PnL'])))
    with localcontext() as ctx:
        ctx.prec=50;need(max(abs(free-final_free),abs(free-final_nav),abs(free-initial-source_pnl))<=D('1e-24'),'Final original paid-flat cash/NAV/PnL differs from recorded deltas');liquidation_loss=sum((D(w['isolated_margin_lost']) for w in liqs),D(0))
    need(abs(liquidation_loss-D(str(summary['liquidation_loss_USDT'])))<D('1e-8'),'Original liquidation losses differ')
    assets={}
    for s in symbols:
        group=[l for l in lives if l['symbol']==s];assets[s]=dict(lifetimes=len(group),long_lifetimes=sum(l['side']=='LONG' for l in group),short_lifetimes=sum(l['side']=='SHORT' for l in group),near_minute_observations=sum(l['near_minute_observations'] for l in group),near_event_observations=sum(l['near_event_observations'] for l in group),actual_liquidations=sum(l['actual_liquidations'] for l in group))
        for key in ('minimum_margin_headroom','minimum_normalized_margin_headroom','minimum_engine_trigger_headroom','minimum_adverse_price_distance'):
            values=[(l[key],l['id']) for l in group if l[key] is not None];best=min(values,key=lambda v:D(v[0]['value'])) if values else None;assets[s][key]=None if best is None else best[0]|dict(lifetime_id=best[1])
    for n,r in inputs.items():need(record(directory/n)==r,'Completed journal modified during read-only diagnostic')
    return dict(schema='SAVED_NATIVE_ISOLATED_POSITION_LIFETIME_RISK_V1',status='PASS_JOURNAL_ONLY_POSITION_LIFETIME_RISK_SUMMARY',account_label=label,source_account_hashes=inputs,account_binding_identity=hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest(),engine_version='native_daily_scheduler_v1',account_version=contract['version'],financial_source_SHA256=SOURCES,diagnostic_source_SHA256=sha(Path(__file__)),diagnostic=dict(near_adverse_price_distance_fraction=near_distance,near_definition='0<SIGNED_ADVERSE_DISTANCE<=THRESHOLD;ACTUAL_CROSSED_LIQUIDATIONS_SEPARATE',policy_or_risk_limit_change=False),calendar=dict(first_minute_close_us=int(times[0]),last_minute_close_us=int(times[-1]),minutes=len(times)),account_free_cash=dict(first_USDT=str(initial),minimum_event_USDT=str(min_free),minimum_minute_USDT=float(minute['free_cash'].min()),never_added_to_isolated_collateral=True),funding_debits_consuming_isolated_collateral=funding_margin_debits,assets=assets,lifetimes=lives,actual_liquidations=len(liqs),original_liquidation_loss_USDT=summary['liquidation_loss_USDT'],original_liquidation_loss_decimal_USDT=str(liquidation_loss),original_net_PnL_USDT=summary['net_PnL'],original_net_PnL_decimal_USDT=str(source_pnl),flat_asset_minute_rows=flat_rows,reconciliation=dict(maximum_free_cash_error_USDT=free_error,per_asset_maximum_errors=errors,final_original_flat_cash_NAV_PnL=True,decimal_state_tolerance_USDT='1E-24',all_input_hashes_unchanged=True),scope='ALL_SAVED_HELD_MINUTE_CLOSES_PLUS_RECORDED_PRE_POST_FILL_FUNDING_AND_PRE_TAKEOVER;NOT_UNOBSERVED_INTRAMINUTE_OR_NATIVE_EXCHANGE_CERTIFICATION',precision='FLOAT64_MINUTE_SCAN;DECIMAL_RECEIPT_STATE_SOURCE_PRICE_HELPER_FOR_ALL_PRICES_AND_WITNESSES;ORIGINAL_JOURNALS_UNCHANGED',positive_price_trigger_note='FLAT_IS_NA;LONG_LP<=0_HAS_NO_POSITIVE_PRICE_TRIGGER;TINY_POSITIVE_LONG_LP_CAN_REFLECT_ORIGINAL_DECIMAL_ROUNDOFF;NEGATIVE_DISTANCE_MEANS_ENGINE_THRESHOLD_CROSSED',quantity_note='SCALING_QUANTITY_AND_COLLATERAL_TOGETHER_DOES_NOT_CHANGE_FIXED_LEVERAGE_LIQUIDATION_PRICE',historical_risk_tiers_certified=contract['historical_risk_tiers_certified'],new_wallets=0,account_or_simulator_instances=0,downloads=0,model_fits=0,completed_account_files_modified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--account',action='append',required=True,help='LABEL=directory containing original complete saved journals');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--near-distance',type=float,default=.05);a=parser.parse_args()
    for name,h in SOURCES.items():need(sha(REPO/name)==h,'Pinned original financial source differs: '+name)
    a.output.mkdir(parents=True,exist_ok=True);results=[]
    for value in a.account:
        label,path=value.split('=',1);result=summarize(Path(path),label,a.near_distance);target=a.output/(label+'.json');raw=encode(result)
        if target.exists():need(target.read_bytes()==raw,'Refuse replacement of different diagnostic output')
        else:target.write_bytes(raw)
        results.append(dict(account=label,file=target.name,sha256=sha(target),lifetimes=len(result['lifetimes']),near_minute_observations=sum(v['near_minute_observations'] for v in result['assets'].values()),actual_liquidations=result['actual_liquidations'],original_net_PnL_USDT=result['original_net_PnL_USDT']));print(json.dumps(results[-1]),flush=True)
    manifest=dict(schema='FOUR_OR_EXPLICIT_SAVED_NATIVE_RISK_SUMMARIES_V1',source_SHA256=SOURCES,utility_SHA256=sha(Path(__file__)),near_distance=a.near_distance,accounts=results,new_wallets=0,downloads=0,policy_changes=0,original_accounts_unchanged=True);target=a.output/'MANIFEST.json';raw=encode(manifest)
    if target.exists():need(target.read_bytes()==raw,'Different existing diagnostic manifest')
    else:target.write_bytes(raw)


if __name__=='__main__':main()
