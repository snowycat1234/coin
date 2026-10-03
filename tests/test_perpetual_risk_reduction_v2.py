"""ONE UNRUN D046 case: legal risk-only rounding, exact completion and causality.

All inputs below are synthetic; no saved source/market/account is read. The
old scheduler is called only as the new minimal tail-dust failure reproducer,
not as another replay of an already accepted financial suite.
"""
from copy import deepcopy
from decimal import Decimal as D
import json
from types import SimpleNamespace
import numpy as np
import polars as pl
import pytest
from quant.perpetual_account import USDTLinearPerpetualAccount
from scripts.investment import perpetual_risk_reduction_research_v2 as fix

MINUTE=60_000_000
START=1_725_148_800_000_000


def test_risk_reduction_legal_quantity_exact_completion_and_future_prefix(tmp_path):
    cost=fix.base.COSTS[0]
    # A tiny target tail must neither round to zero nor be treated as epsilon.
    buy=fix.risk_reduction_request(D('-1'),D('-.9999999974'),D('1000'),cost)
    sell=fix.risk_reduction_request(D('1'),D('.9999999974'),D('1000'),cost)
    assert buy==D('.00999201') and buy*D('1000.8')==D('10.000003608')
    assert sell==D('.01000801') and sell*D('999.2')==D('10.000003592')
    assert fix.risk_target_reached(D('-.9999999974'),D('-.99000799'))
    assert fix.risk_target_reached(D('.9999999974'),D('.98999199'))
    assert not fix.risk_target_reached(D('-.9999999974'),D('-1'))
    assert not fix.risk_target_reached(D('-.5'),D('.4'))
    assert not fix.risk_target_reached(D('0'),D('.00000001'))
    assert fix.risk_target_reached(D('0'),D('0'))
    assert fix.risk_reduction_request(D('-1'),D('-1'),D('1000'),cost)==0
    with pytest.raises(ValueError,match='reducing toward target'):
        fix.risk_reduction_request(D('-1'),D('.1'),D('1000'),cost)

    # Clip a legal gross request to the actual lot inventory; never cross zero.
    account=USDTLinearPerpetualAccount()
    account.update_marks(START,{s:dict(price='2500',close_us=START,available_us=START) for s in fix.base.SYMBOLS})
    opened=account.execute_fill('BTCUSDT','SELL','.005',START+MINUTE+1,START,'synthetic-dust-open',
        execution_mid_price='2500',quote_available_us=START+MINUTE,available_quantity='.005')
    assert opened['status']=='FILLED' and account.positions['BTCUSDT'].quantity==D('-.005')
    clipped=fix.risk_reduction_request(D('-.005'),D('-.0049999974'),D('1000'),cost)
    assert clipped==D('.005')
    rejected=account.execute_fill('BTCUSDT','BUY',clipped,START+3*MINUTE+1,START+2*MINUTE,'synthetic-dust-close',
        execution_mid_price='1000',quote_available_us=START+3*MINUTE,available_quantity='.005',reduce_only=True)
    assert rejected['status']=='REJECTED' and rejected['executed_quantity']==0
    assert rejected['reason']=='BELOW_MIN_NOTIONAL_OR_CAPACITY'
    assert account.positions['BTCUSDT'].quantity==D('-.005') and len(account.trades)==1

    def targets(_bars,decisions,mode):
        assert mode=='LONG_SHORT'
        return pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=-.3 if s=='BTCUSDT' else 0.)
            for t in decisions for s in fix.base.SYMBOLS]),dict(scope='NEW_RISK_SCHEDULER_SYNTHETIC_FIXED_TARGET')
    stub=SimpleNamespace(fixed_targets=targets)
    fixed,proof=fix.adapted_simulate(stub)
    assert len(proof)==1 and len(proof[0]['changes'])==2
    assert all(row['matches']==1 for row in proof[0]['changes'])
    old=fix.private.namespace(fix.base,['simulate'],dict(strategy=stub),[])['simulate']

    def window():
        n=32;times=START+np.arange(n,dtype=np.int64)*MINUTE;market={}
        for symbol in fix.base.SYMBOLS:
            opened=np.full(n,1000.);marked=np.full(n,1000.)
            if symbol=='BTCUSDT':
                # First close breaches; first reduction leaves a sub-lot
                # frozen target tail in the OLD scheduler. A later close
                # requires another genuine causal reduction, not tolerance.
                marked[3:]=1008.;opened[4:]=1008.
                marked[5:]=1018.;opened[6:]=1018.
            market[symbol]=dict(open=opened,close=opened.copy(),mark=marked,quote_volume=np.full(n,10_000_000.))
        daily=pl.DataFrame([dict(symbol=s,close_us=START,close=1000.) for s in fix.base.SYMBOLS])
        events=[dict(symbol='BTCUSDT',event_us=START+i*MINUTE+1000,raw_rate=.0001,
            reported_interval_hours=8.) for i in (5,20)]
        return dict(start=START,end=START+n*MINUTE,times=times,market=market,daily=daily,events=events,input_proofs=[])

    fixture=window()
    original=old(fixture,'LONG_SHORT',cost,fix.base.UNITS[0])
    assert original['summary']['completion']=='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION'
    assert original['summary']['stop_us']==START+9*MINUTE+1
    # One outstanding tail is expired/removed at the stop; its actual rejected
    # request proves the sub-step quantity without inventing a saved market row.
    tiny=[r for r in original['rejections'] if r.get('requested_quantity',1)<float(fix.STEP)]
    assert tiny and all(r.get('executed_quantity')==0 for r in tiny)
    repaired=fixed(fixture,'LONG_SHORT',cost,fix.base.UNITS[0])
    assert repaired['summary']['completion']=='COMPLETE_CONDITIONAL_ACCOUNT'
    assert repaired['summary']['completed_minutes']==32 and repaired['minute'].height==32
    assert repaired['summary']['terminal_cash_realized'] and repaired['summary']['terminal_marked_notional']==0
    assert abs(repaired['summary']['accounting_bridge_error_USDT'])<=1e-7
    first_old=original['trades'][0];first_new=repaired['trades'][0]
    assert first_new==first_old  # Original DAILY_TARGET branch is unchanged.
    risk_signals={row['signal_us'] for row in repaired['breaches']}
    risk_trades=[row for row in repaired['trades'] if row['signal_us'] in risk_signals]
    assert len(risk_trades)>=2
    assert START+4*MINUTE in risk_signals and START+6*MINUTE in risk_signals
    for row in risk_trades:
        assert row['side']=='BUY' and row['leg']=='CLOSE'
        strings=row['decimal_strings'];q0,q1=D(strings['quantity_before']),D(strings['quantity_after'])
        quantity,fill=D(strings['quantity']),D(strings['fill_price'])
        assert q0<0 and q0<=q1<=0 and quantity<=abs(q0)
        assert quantity%fix.STEP==0 and quantity*fill>=D('10')
        i=(row['event_us']-START-1)//MINUTE
        assert quantity*D(str(fixture['market']['BTCUSDT']['open'][i]))<=D(str(fixture['market']['BTCUSDT']['quote_volume'][i-1]))*D('.001')
        assert D(strings['fee_USDT_mid'])==quantity*fill*D('.00055')
        assert D(strings['execution_mid_price'])==D(str(fixture['market']['BTCUSDT']['open'][i]))
    assert not any(r.get('reason')=='FIVE_ATTEMPTS_EXPIRED' and r.get('kind')=='RISK_REDUCTION' for r in repaired['rejections'])

    # Genuine sub-10USDT capacity remains unable to fill; it is not rounded up.
    dry=window();dry['market']['BTCUSDT']['quote_volume'][4:]=5000.
    denied=fixed(dry,'LONG_SHORT',cost,fix.base.UNITS[0])
    assert denied['summary']['completion']=='NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION'
    assert denied['summary']['stop_us']==START+9*MINUTE+1
    assert len(denied['trades'])==1 and denied['summary']['positions']['BTCUSDT']['quantity']==-2.97
    assert denied['summary']['unpaid_liability']==0

    # Capacity above10 but below the requested reduction can fill partially.
    # The next eligible attempt completes toward the same frozen target; any
    # subsequent true drift is rescheduled from an actually closed new mark.
    partial=window();partial['market']['BTCUSDT']['quote_volume'][4]=20_000.
    split=fixed(partial,'LONG_SHORT',cost,fix.base.UNITS[0])
    assert split['summary']['completion']=='COMPLETE_CONDITIONAL_ACCOUNT'
    assert split['summary']['terminal_cash_realized']
    assert any(r.get('status')=='PARTIAL' and r.get('phase')=='REDUCE' for r in split['rejections'])
    for row in split['trades']:
        if row['leg']=='CLOSE':
            q0,q1=(D(row['decimal_strings'][k]) for k in ('quantity_before','quantity_after'))
            assert q0<=q1<=0 and D(row['decimal_strings']['quantity'])<=abs(q0)

    changed=deepcopy(fixture);cut=START+16*MINUTE
    for symbol in fix.base.SYMBOLS:
        for key in ('open','mark','close'):
            changed['market'][symbol][key][16:]*=1.0001
        changed['market'][symbol]['quote_volume'][16:]*=1.01
    changed['events'][1]['raw_rate']=-.0005
    future=fixed(changed,'LONG_SHORT',cost,fix.base.UNITS[0])
    assert repaired['minute'].filter(pl.col('close_us')<=cut).equals(future['minute'].filter(pl.col('close_us')<=cut))
    for key in ('trades','funding','breaches'):
        field='signal_us' if key=='breaches' else 'event_us'
        assert [r for r in repaired[key] if r[field]<cut]==[r for r in future[key] if r[field]<cut]
    evidence=dict(scope='NEW_SYNTHETIC_RISK_CORRECTNESS_NOT_MARKET_OR_ALPHA',derivation=proof,
        original_prefix={k:original[k] for k in ('summary','trades','rejections','breaches')},
        repaired={k:repaired[k] for k in ('summary','trades','funding','rejections','breaches')},
        capacity_denied={k:denied[k] for k in ('summary','trades','rejections')},
        capacity_partial={k:split[k] for k in ('summary','trades','rejections','breaches')},
        future_prefix_unchanged_through_us=cut,ordinary_first_entry_unchanged=True,
        whole_position_dust_rejected=rejected)
    (tmp_path/'risk_reduction_evidence.json').write_text(json.dumps(evidence,indent=2,sort_keys=True),encoding='utf-8')