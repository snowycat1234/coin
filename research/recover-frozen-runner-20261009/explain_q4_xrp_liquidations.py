"""Read-only Decimal journal explanation of two frozen Q4 XRP takeovers.

No simulator/account instances, wallet advances, fitting or network calls.
Receipt deltas are folded only to reconcile saved states and NAV identities.
"""
import argparse,json,sys
from datetime import datetime,UTC
from decimal import Decimal as D,localcontext
from pathlib import Path
import numpy as np
import polars as pl
import q4_native92 as run
SYMBOLS=run.base.frozen.SYMBOLS;MINUTE=run.base.frozen.MINUTE
PUBLIC=run.PUBLIC/'xrp-liquidation-explanation';MODEL='SELECTED_FULL773_256'
TOL=D('1e-24')


def close(a,b):run.require(abs(a-b)<=TOL,'Decimal saved receipt identity differs')
def utc(t):return datetime.fromtimestamp(t/1e6,UTC).isoformat()
def serialized(o):
    if isinstance(o,D):return str(o)
    if isinstance(o,dict):return {k:serialized(v) for k,v in o.items()}
    if isinstance(o,list):return [serialized(v) for v in o]
    return o


def fold(trades,funds,t,inclusive=False):
    """Saved cash/collateral/quantity deltas, never a financial transition engine."""
    free=D(10000);positions={s:dict(quantity=D(0),collateral=D(0),entry=D(0)) for s in SYMBOLS};fees=funding=realized=execution=D(0)
    stream=sorted([(r['event_us'],-1 if r.get('liquidation_takeover') else 1,i,'trade',r) for i,r in enumerate(trades)]+[(r['event_us'],0,i,'funding',r) for i,r in enumerate(funds)])
    for stamp,priority,index,kind,r in stream:
        if stamp>t or stamp==t and not inclusive:break
        p=positions[r['symbol']];x=r.get('decimal_strings',{})
        if kind=='funding':
            close(p['quantity'],D(str(r['quantity'])));amount=D(x.get('signed_funding_USDT',str(r['signed_funding_USDT'])))
            run.require(amount>=0 or free>=-amount,'A funding debit consumed isolated collateral; this audit scope must stop')
            free+=amount;funding+=amount
        else:
            close(p['quantity'],D(x['quantity_before']));close(p['entry'],D(x['entry_price_before']));q=abs(D(x['position_delta']));fill=D(x['fill_price'])
            if r.get('liquidation_takeover'):
                close(D(x['takeover_margin_loss']),p['collateral']);close(D(x['realized_PnL']),-p['collateral']);close(D(x['free_cash_delta']),D(0))
            elif r['leg']=='OPEN':
                close(D(x['margin_allocated']),q*fill);close(D(x['isolated_balance_delta']),q*fill)
                close(D(x['entry_price_after']),(abs(p['quantity'])*p['entry']+q*fill)/(abs(p['quantity'])+q))
            else:
                close(D(x['margin_released']),p['collateral']*q/abs(p['quantity']));close(D(x['isolated_balance_delta']),-D(x['margin_released']))
                close(D(x['realized_PnL']),(D(1) if p['quantity']>0 else D(-1))*q*(fill-p['entry']))
            p['quantity']+=D(x['position_delta']);p['collateral']+=D(x['isolated_balance_delta']);p['entry']=D(x['entry_price_after']);free+=D(x['free_cash_delta'])
            close(p['quantity'],D(x['quantity_after']));run.require(free>=0 and p['collateral']>=-TOL,'Negative saved free cash or collateral')
            fees+=D(x['fee_amount']);execution+=D(x['execution_cost']);realized+=D(x['realized_PnL'])
    return dict(free_cash=free,positions=positions,fees=fees,funding=funding,realized_PnL_at_fill_prices=realized,execution_cost=execution)


def nav(state,prices):return state['free_cash']+sum((p['collateral']+p['quantity']*(prices[s]-p['entry']) for s,p in state['positions'].items()),D(0))
def short_metrics(p,mark):
    q=abs(p['quantity']);run.require(p['quantity']<0,'This explanation is for actual held shorts');extra=p['collateral']-q*p['entry']
    lp=(2*p['entry']*q+extra/(1+D('.00055')))/(q*(1+D('.005')))
    equity=p['collateral']+p['quantity']*(mark-p['entry']);maintenance=q*mark*D('.005')
    return dict(quantity=p['quantity'],entry_price_USDT_per_XRP=p['entry'],isolated_collateral_USDT=p['collateral'],one_x_entry_notional_USDT=q*p['entry'],extra_collateral_USDT=extra,mark_price_USDT_per_XRP=mark,liquidation_threshold_USDT_per_XRP=lp,bankruptcy_price_USDT_per_XRP=p['entry']+p['collateral']/q,unrealized_PnL_USDT=p['quantity']*(mark-p['entry']),isolated_equity_USDT=equity,maintenance_USDT=maintenance,equity_minus_maintenance_USDT=equity-maintenance,threshold_crossed=mark>=lp,mark_over_entry_return=mark/p['entry']-1)


def explain(state,output=None):
    run.source_check(state);arms=('Static50','Cash50',MODEL);inputs={};book={};bound={}
    for arm in arms:
        directory=state/'q4-native92'/arm/'account';book[arm]=dict(trades=run.read(directory/'trades.json'),funds=run.read(directory/'funding.json'),liqs=run.read(directory/'liquidations.json'),summary=run.read(directory/'summary.json'),minute=pl.read_parquet(directory/'minute_nav_inventory.parquet'))
        for n in ('trades.json','funding.json','liquidations.json','summary.json','minute_nav_inventory.parquet'):
            p=directory/n;inputs[p.relative_to(state).as_posix()]=run.record(p)
        receipt=run.read(run.PUBLIC/'results'/arm/'PUBLIC_READBACK.json');bound[arm]=dict(artifact_commit=receipt['artifact_commit'],archive_SHA256=receipt['archive_SHA256'],account_journal_exact=receipt['account_journal_exact'])
    work=run.locations(state)[2]/'data/normalized';source_marks={};grid=[]
    for symbol in SYMBOLS:
        for family in ('klines','markPriceKlines'):
            p=work/'minute'/symbol/family/'2024-11.parquet';df=pl.read_parquet(p);inputs[p.relative_to(state).as_posix()]=run.record(p);key='open_us' if family=='klines' else 'timestamp_ms';tt=df[key].to_numpy()*(1 if family=='klines' else 1000)
            stamps=np.arange(1731753840000000,1731754500000000,MINUTE,dtype=np.int64);ix=np.searchsorted(tt,stamps);run.require(np.array_equal(tt[ix],stamps),'Missing actual trade/mark event-window bar')
            grid.append(dict(symbol=symbol,family=family,actual_rows=len(ix),consecutive=True,zero_quote_rows=int((df['quote_volume'].to_numpy()[ix]==0).sum()) if family=='klines' else None))
            if family=='markPriceKlines':source_marks[symbol]={int(t)+MINUTE:D(str(float(v))) for t,v in zip(tt,df['close'].to_numpy(),strict=True)}
    events=[]
    with localcontext() as ctx:
        ctx.prec=50
        for arm in arms:
            b=book[arm];final=fold(b['trades'],b['funds'],run.END,True);close(final['free_cash'],D(b['summary']['decimal_strings']['free_cash']))
            close(final['free_cash'],D(10000)+final['realized_PnL_at_fill_prices']-final['fees']+final['funding'])
            for key,field in [('fees','fees_USDT'),('funding','funding_USDT'),('realized_PnL_at_fill_prices','realized_PnL'),('execution_cost','execution_cost_USDT')]:close(final[key],D(b['summary']['decimal_strings'][field]))
            run.require(all(abs(p['quantity'])<=TOL and abs(p['collateral'])<=TOL for p in final['positions'].values()),'Original final account must remain flat')
        for arm in arms[:2]:
            b=book[arm];w=b['liqs'][0];t=w['event_us'];before=fold(b['trades'],b['funds'],t);after=fold(b['trades'],b['funds'],t,True);p=before['positions']['XRPUSDT'];mark=source_marks['XRPUSDT'][t];prev=source_marks['XRPUSDT'][t-MINUTE];metrics=short_metrics(p,mark);prior_metrics=short_metrics(p,prev)
            close(p['quantity'],D(w['quantity']));close(p['entry'],D(w['entry_price']));close(p['collateral'],D(w['isolated_margin_lost']));close(mark,D(w['mark_price']));close(metrics['bankruptcy_price_USDT_per_XRP'],D(w['bankruptcy_price']));run.require(metrics['threshold_crossed'] and metrics['equity_minus_maintenance_USDT']<0 and not prior_metrics['threshold_crossed'] and prior_metrics['equity_minus_maintenance_USDT']>0,'Saved previous/current mark must straddle the actual threshold')
            xs=[r for r in b['trades'] if r['symbol']=='XRPUSDT'];takeover=next(r for r in xs if r['fill_id']==w['id']);start=max(r['event_us'] for r in xs if r['event_us']<t and r['leg']=='OPEN' and D(r['decimal_strings']['quantity_before'])==0);episode=[r for r in xs if start<=r['event_us']<t];efunds=[r for r in b['funds'] if r['symbol']=='XRPUSDT' and start<r['event_us']<=t];last_fund=max(efunds,key=lambda r:r['event_us']);next_fill=next(r for r in xs if r['event_us']>t)
            current_prices={s:source_marks[s][t] for s in SYMBOLS};previous_prices={s:source_marks[s][t-MINUTE] for s in SYMBOLS};nav_pre=nav(before,current_prices);nav_post=nav(after,current_prices);nav_previous=nav(before,previous_prices);observed=b['minute'].filter(pl.col('close_us').is_in([t-MINUTE,t])).sort('close_us');run.require(observed.height==2 and abs(float(nav_previous)-observed['nav'][0])<1e-8 and abs(float(nav_post)-observed['nav'][1])<1e-8,'Event NAV and previous-minute NAV must reconcile');close(nav_pre-nav_post,metrics['isolated_equity_USDT']);close(before['free_cash'],after['free_cash'])
            ordinary=[r for r in b['trades'] if t-MINUTE<r['event_us']<=t and not r.get('liquidation_takeover')];fund_same=[r for r in b['funds'] if t-MINUTE<r['event_us']<=t];run.require(not ordinary and not fund_same,'A concurrent fill/funding event requires expanded ordering analysis')
            flat=b['minute'].filter((pl.col('close_us')>=t)&(pl.col('close_us')<next_fill['event_us']));run.require(flat['XRPUSDT_quantity'].eq(0).all() and flat['XRPUSDT_isolated_balance'].eq(0).all() and next_fill['signal_us']>t,'No resurrected collateral or same-signal reentry')
            gross_pre=sum((abs(before['positions'][s]['quantity'])*current_prices[s] for s in SYMBOLS),D(0))/nav_pre
            model=book[MODEL];model_state=fold(model['trades'],model['funds'],t,True);model_metrics=short_metrics(model_state['positions']['XRPUSDT'],mark);model_nav=nav(model_state,current_prices);mr=model['minute'].filter(pl.col('close_us')==t);run.require(mr.height==1 and abs(float(model_nav)-mr['nav'][0])<1e-8 and not model_metrics['threshold_crossed'] and not model['liqs'],'Model observed state must reconcile and stay above maintenance')
            event=dict(arm=arm,event_us=t,event_UTC=utc(t),phase=w['phase'],before=metrics,previous_completed_mark=dict(close_us=t-MINUTE,price=prev,equity_minus_maintenance_USDT=prior_metrics['equity_minus_maintenance_USDT']),global_state=dict(NAV_before_current_mark_takeover_USDT=nav_pre,NAV_after_takeover_USDT=nav_post,NAV_previous_minute_USDT=nav_previous,free_cash_before_and_after_USDT=before['free_cash'],gross_weight_before_takeover=gross_pre,XRP_abs_weight_before_takeover=abs(p['quantity'])*mark/nav_pre,mark_move_PnL_all_assets_USDT=nav_pre-nav_previous,instant_takeover_NAV_debit_USDT=nav_pre-nav_post,observed_minute_NAV_change_USDT=nav_post-nav_previous),takeover=dict(original_trade=takeover,isolated_collateral_change_USDT=-p['collateral'],unrealized_PnL_removed_USDT=-metrics['unrealized_PnL_USDT'],NAV_debit_is_remaining_equity_not_second_full_margin_loss=True,extra_liquidation_fee_USDT=0,extra_execution_cost_USDT=0,insurance_surplus_refund_USDT=0,bankruptcy_takeover_not_a_capacity_limited_market_fill=True),episode=dict(start_us=start,start_UTC=utc(start),ordinary_fill_count=len(episode),ordinary_realized_PnL_at_fill_prices_USDT=sum((D(r['decimal_strings']['realized_PnL']) for r in episode),D(0)),ordinary_fees_USDT=sum((D(r['decimal_strings']['fee_amount']) for r in episode),D(0)),ordinary_execution_cost_USDT=sum((D(r['decimal_strings']['execution_cost']) for r in episode),D(0)),signed_funding_USDT=sum((D(r['decimal_strings']['signed_funding_USDT']) for r in efunds),D(0)),funding_events=len(efunds),last_funding=last_fund,liquidation_realized_PnL_USDT=-p['collateral'],PnL_scope='ACTUAL_FILL_PRICE_REALIZED_PNL_INCLUDES_EXECUTION_FRICTION;DO_NOT_SUBTRACT_EXECUTION_COST_AGAIN'),ordering=dict(ordinary_fills_in_event_minute=0,funding_events_in_event_minute=0,mark_close_us=t,mark_source_open_us=t-MINUTE,previous_minute_crossed=False,current_minute_crossed=True,no_missing_event_window_trade_or_mark_bars=True,cash_credits_not_isolated_topups=True),subsequent=dict(flat_minutes_before_next_normal_fill=flat.height,next_original_fill=next_fill,old_margin_refunded_or_restored=False,normal_signal_after_liquidation=True),selected_model_same_observable_time=dict(metrics=model_metrics,NAV_USDT=model_nav,free_cash_USDT=model_state['free_cash'],gross_weight=D(str(float(mr['gross_weight'][0]))),XRP_signed_weight=model_state['positions']['XRPUSDT']['quantity']*mark/model_nav,latest_original_XRP_fill=next(r for r in reversed(model['trades']) if r['symbol']=='XRPUSDT' and r['event_us']<t),no_hindsight_policy_change=True))
            events.append(event)
            event['episode']['realized_plus_takeover_PnL_USDT']=event['episode']['ordinary_realized_PnL_at_fill_prices_USDT']-p['collateral']
            event['episode']['net_PnL_through_liquidation_USDT']=event['episode']['realized_plus_takeover_PnL_USDT']-event['episode']['ordinary_fees_USDT']+event['episode']['signed_funding_USDT']
            model_trades=model['trades'];model_start=max(r['event_us'] for r in model_trades if r['symbol']=='XRPUSDT' and r['event_us']<t and r['leg']=='OPEN' and D(r['decimal_strings']['quantity_before'])==0)
            event['selected_model_same_observable_time']['episode_start_us']=model_start
            event['selected_model_same_observable_time']['episode_start_UTC']=utc(model_start)
        finals={arm:dict(NAV_USDT=book[arm]['summary']['NAV'],net_PnL_USDT=book[arm]['summary']['net_PnL'],realized_PnL_at_fill_prices_USDT=book[arm]['summary']['realized_PnL'],fees_USDT=book[arm]['summary']['fees_USDT'],funding_USDT=book[arm]['summary']['funding_USDT'],execution_cost_USDT=book[arm]['summary']['execution_cost_USDT'],liquidation_loss_USDT=book[arm]['summary']['liquidation_loss_USDT'],full_loss_already_in_reported_NAV=True,existing_full_independent_audit=run.read(run.PUBLIC/'results'/arm/'INDEPENDENT_AUDIT.json')['status']) for arm in arms}
    for name,rec in inputs.items():run.require(run.record(state/name)==rec,'Read-only explanation changed an input')
    result=serialized(dict(status='PASS_READ_ONLY_SAVED_Q4_XRP_ISOLATED_LIQUIDATION_EXPLANATION',engine_SHA256=run.ENGINE_SHA,source_SHA256={n:run.sha(run.REPO/n) for n in ('scripts/investment/resumable_perpetual.py','src/quant/bybit_isolated_account.py','src/quant/perpetual_account.py')},script_SHA256=run.sha(Path(__file__)),bound_public_accounts=bound,inputs=inputs,actual_event_grid=grid,events=events,final_accounts=finals,conclusion='LEGITIMATE_PER_POSITION_ISOLATED_MARGIN_OUTCOME_UNDER_FROZEN_UNCERTIFIED_CONDITIONAL_RULES;NO_EVENT_EVIDENCE_OF_UNIT_COLLATERAL_ALLOCATION_MISSING_BAR_OR_ORDERING_DEFECT',engineering_implication='Track per-position isolated equity/maintenance and liquidation distance independently of portfolio gross/covariance caps. Low global exposure and abundant free cash do not rescue a legacy-basis isolated short when auto-margin is off. This is an audit implication, not a new strategy or authority to retune.',completed_account_bytes_unchanged=True,new_wallets=0,account_or_simulator_instances=0,model_fits=0,policy_changes=0,risk_limit_changes=0,downloads=0,historical_native_risk_tier_or_liquidation_certification=False))
    result['precision_scope']=dict(analysis_decimal_digits=50,original_account_decimal_digits=40,receipt_identity_tolerance_USDT=str(TOL),minute_NAV_comparison_tolerance_USDT='1e-8',tiny_extra_collateral_is_original_decimal_rounding_residue=True)
    run.write_once((output or PUBLIC)/'EVIDENCE.json',run.encoded(result));print(json.dumps(dict(status=result['status'],events=[dict(arm=e['arm'],event_UTC=e['event_UTC'],equity=e['before']['isolated_equity_USDT'],maintenance=e['before']['maintenance_USDT'],LP=e['before']['liquidation_threshold_USDT_per_XRP'],NAV_debit=e['global_state']['instant_takeover_NAV_debit_USDT'],gross=e['global_state']['gross_weight_before_takeover'],model_equity=e['selected_model_same_observable_time']['metrics']['isolated_equity_USDT']) for e in result['events']])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args();explain(a.state,a.output)
