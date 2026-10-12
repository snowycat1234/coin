import argparse,importlib.util,json,time
from decimal import Decimal,localcontext
from pathlib import Path
import numpy as np
import pandas as pd
from core import split_money,expiry_class
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('old',ROOT/'research/minute-conditional-selector-20261011/experiment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
INPUT=ROOT/'research/short-native-activity-20261012/result';DAY=m.DAY_US

def run(state,source,expected=None):
    m.require(not state.exists() and not m.git('status','--porcelain'),'Fresh state/clean source')
    if not expected:m.require(m.git('rev-parse','HEAD').decode().strip()==source,'Publishedsource')
    m.verify_manifest(HERE/'SOURCE_SHA256.txt');state.mkdir();start=time.monotonic();body=json.loads((INPUT/'ACCOUNT.json').read_bytes());summary=body['summary']
    with np.load(INPUT/'MINUTE.npz',allow_pickle=False) as z:minute={k:z[k].copy() for k in z.files}
    symbols=tuple(summary['symbols']);closes=minute['close_us'];first=int(closes[0]-60_000_000);end=int(closes[-1]);d=np.arange(first,end,DAY,dtype=np.int64)
    m.require(len(closes)==44640 and len(d)==31 and np.all(np.diff(closes)==60000000),'Original full31day calendar')
    with localcontext() as ctx:
        ctx.prec=50;money=split_money(body['trades'],body['funding'],summary['positions'],summary['terminal_mark_prices'])
        net=sum((v['net'] for v in money.values()),Decimal(0));targetnav=Decimal(summary['decimal_strings']['NAV']);error=abs(Decimal(10000)+net-targetnav)
        m.require(error<Decimal('1e-8'),'ExactDecimalmarkedNAV')
        realized=sum((Decimal(r['decimal_strings']['realized_PnL']) for r in body['trades']),Decimal(0))
        unrealized=sum((Decimal(p['decimal_strings']['quantity'])*(Decimal(str(summary['terminal_mark_prices'][s]))-Decimal(p['decimal_strings']['entry_price'])) for s,p in summary['positions'].items()),Decimal(0))
        fees=sum((v['fees'] for v in money.values()),Decimal(0));fund=sum((v['funding'] for v in money.values()),Decimal(0))
        fill_error=abs(Decimal(10000)+realized+unrealized-fees+fund-targetnav);m.require(fill_error<Decimal('1e-8'),'Fillbasisexecutionnotdoubledebited')
    rows=[dict(symbol=s,side=side,**{k:str(x) for k,x in v.items()}) for (s,side),v in money.items()]
    targets=pd.DataFrame(body['targets']).pivot(index='available_us',columns='symbol',values='target_weight').reindex(index=d,columns=symbols).to_numpy(float)
    actual=np.column_stack([minute[s+'_signed_weight'] for s in symbols]);dayid=((closes-first-1)//DAY).astype(int)
    desired=.99*targets[dayid];desired[closes>end-6*60000000]=0.;diff=actual-desired
    checkpoint=np.arange(31)*1440+5;tracking=[]
    for j,s in enumerate(symbols):tracking.append(dict(symbol=s,mean_absolute_weight_error=float(np.abs(diff[:,j]).mean()),
        after5attempt_mean_absolute_weight_error=float(np.abs(diff[checkpoint,j]).mean()),mean_actual_long_weight=float(np.maximum(actual[:,j],0).mean()),
        mean_actual_short_weight=float(np.maximum(-actual[:,j],0).mean()),terminal_signed_notional=float(summary['terminal_signed_marked_notional'][s])))
    daily=[];previous=10000.;previousfee=previousexec=previousfund=0.
    for i,t in enumerate(d):
        k=(i+1)*1440-1;fee=float(minute['cumulative_fees'][k]);execution=float(minute['cumulative_execution_costs'][k]);funding=float(minute['cumulative_funding'][k]);nav=float(minute['nav'][k])
        daily.append(dict(decision_us=int(t),net_USDT=nav-previous,fees_USDT=fee-previousfee,execution_USDT=execution-previousexec,
            funding_cash_USDT=funding-previousfund,gross_price_USDT=(nav-previous)+(fee-previousfee)+(execution-previousexec)-(funding-previousfund)))
        previous,previousfee,previousexec,previousfund=nav,fee,execution,funding
    expiries=[{**r,'remaining_class':expiry_class(r)} for r in body['rejections'] if r.get('reason')=='FIVE_ATTEMPTS_EXPIRED']
    terminal=[r for r in expiries if r.get('kind')=='TERMINAL'];torders={r['order_id'] for r in terminal}
    terminalfills=[r for r in body['trades'] if r['fill_id'].rsplit(':',2)[0] in torders]
    report=dict(status='COMPLETE_SAVED_ACCOUNT_DRAG_AND_TRACKING_BRIDGES',source_commit=source,old_account_reruns=0,new_models=0,provider_downloads=0,
        independent_midprice_NAV_error_USDT=str(error),independent_fillbasis_NAV_error_USDT=str(fill_error),perasset_side=rows,
        joint_marked_profit_USDT=str(net),realized_fillbasis_price_USDT=str(realized),unpaid_unrealized_fillbasis_USDT=str(unrealized),
        realized_exposure=dict(mean_long_weight=float(np.maximum(actual,0).sum(1).mean()),mean_short_weight=float(np.maximum(-actual,0).sum(1).mean()),
            max_gross_weight=float(minute['gross_weight'].max()),all_available_observation_DD=summary['all_observation_max_drawdown']),
        target_tracking=tracking,mean_portfolio_L1_weight_error=float(np.abs(diff).sum(1).mean()),
        after5attempt_mean_portfolio_L1_weight_error=float(np.abs(diff[checkpoint]).sum(1).mean()),
        expiry_counts={k:sum(r['remaining_class']==k for r in expiries) for k in ('SUBSTEP_REMAINDER','AT_LEAST_ONE_EXECUTABLE_STEP')},
        terminal_expiry=terminal,terminal_paid_fill_legs=len(terminalfills),paid_flat=False,remaining_marked_inventory_USDT=summary['gross_notional'],
        tracking_scope='STORED_WEIGHT_TARGET_ERROR_INCLUDES_PRICE_NAV_DRIFT_LATENCY_NOT_PURE_EXECUTION_PNL',
        conclusion='LONG_PRICE_LOSS_DOMINATES_PAID_COSTS;CS_LONG_SHORT_BINDING_NEXT_SINGLE_HYPOTHESIS;TERMINAL_CAPACITY_REMAINS_BLOCKED',
        scope='JOINT_CONDITIONAL_WALLET_DESCRIPTION_NOT_ISOLATED_SHORT_STRATEGY_RETURN')
    pd.DataFrame(rows).to_csv(state/'ASSET_SIDE_BRIDGE.csv',index=False);pd.DataFrame(daily).to_csv(state/'DAILY_BRIDGE.csv',index=False);pd.DataFrame(tracking).to_csv(state/'TRACKING.csv',index=False)
    m.save(state/'RESULT.json',report);m.save(state/'TIMING.json',dict(seconds=time.monotonic()-start))
    if expected:
        for name in ('RESULT.json','ASSET_SIDE_BRIDGE.csv','DAILY_BRIDGE.csv','TRACKING.csv'):
            m.require(m.git('show',expected+':research/short-account-drag-20261012/result/'+name)==(state/name).read_bytes(),'Exactcold '+name)
        m.save(state/'PUBLIC_RESTORE.json',dict(status='PASS_ZERO_WALLET_SAVED_ACCOUNT_DRAG_RESTORE',old_account_reruns=0,new_fits=0,artifact_commit=expected))
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
