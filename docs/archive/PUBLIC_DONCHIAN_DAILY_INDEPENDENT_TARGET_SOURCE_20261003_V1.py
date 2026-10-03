"""UNRUN D037 target-only draft; final source/schema binding still required.

Independent scalar prior20/SMA200 arithmetic and pinned original hooks.
No production fixed_targets, account simulator, source QA, market IO or CLI run.
The final ledger entry will import accepted D033 V3 financial methods unchanged.
"""
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace
import ast, hashlib, math
import numpy as np
import polars as pl

ROOT=Path('/mnt/d/codex/coin'); DAY=86_400_000_000; MINUTE=60_000_000
SYMBOLS=('BTCUSDT','ETHUSDT')
VENDOR=ROOT/'third_party/jesse_example_donchian'
PINS={
 'donchian_original.py':'fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe',
 'donchian_indicator_original.py':'b7e96ebe3ba476c771a65b353c269a84d02e04587f0d76166c5f322bbbb3a401',
 'LICENSE':'80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d',
 'JESSE_LICENSE':'8985ca8447e233f34397a52fe77989c02e27b8145d43bd8c715ae9c7a96056d4'}

def need(value,message):
    if not bool(value):raise ValueError(message)

def original_rules():
    """Load the original class only, with independent scalar indicator formulas."""
    for name,digest in PINS.items():
        need(hashlib.sha256((VENDOR/name).read_bytes()).hexdigest()==digest,'Pinned original public hook/license')
    channel=namedtuple('DonchianChannel','upperband middleband lowerband')
    def prior_channel(candles,period=20):
        need(len(candles)>=period,'Raw hook needs previous20 complete bars')
        upper=max(float(v) for v in candles[-period:,3]);lower=min(float(v) for v in candles[-period:,4])
        return channel(upper,(upper+lower)/2,lower)
    def sma(candles,period=200):
        need(len(candles)>=period,'Raw SMA needs current-inclusive200 complete bars')
        return math.fsum(float(v) for v in candles[-period:,2])/period
    tree=ast.parse((VENDOR/'donchian_original.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Donchian']
    need(len(nodes)==1,'One exact original strategy class')
    namespace=dict(Strategy=object,utils=None,ta=SimpleNamespace(donchian=prior_channel,sma=sma))
    exec(compile(ast.Module(nodes,type_ignores=[]),str(VENDOR/'donchian_original.py')+'<independent-indicators>','exec'),namespace)
    return namespace['Donchian']

def expected_daily_weights(daily,calendar):
    """Schema adapter UNFINALIZED: symbol/open_us/close_us/available_us/high/low/close.

    Only selected past closed bars are used. Daily schema/complete source coverage
    are independently bound by the final entry before this function is invoked.
    Every scoring window starts flat; daily warmup contains no account state.
    """
    required={'symbol','open_us','close_us','available_us','high','low','close'}
    need(required<=set(daily.columns),'Explicit normalized official1d schema')
    need(calendar.ndim==1 and len(calendar)>0 and np.all(np.diff(calendar)==MINUTE),'Complete scoring minute decisions')
    need(int(calendar[0])%DAY==0,'Scoring begins UTC00:00, fresh flat account')
    need(set(daily['symbol'].unique().to_list())==set(SYMBOLS),'Exactly two fixed symbols')
    weights=np.zeros((len(calendar),2));witnesses=[];Public=original_rules()
    decisions=np.arange(int(calendar[0]),int(calendar[-1])//DAY*DAY+1,DAY,dtype=np.int64)
    for column,symbol in enumerate(SYMBOLS):
        rows=daily.filter((pl.col('symbol')==symbol)&(pl.col('close_us')<=int(calendar[-1]))).sort('close_us')
        need(rows.height==rows.unique('close_us').height,'No duplicate daily closes')
        for name in ('open_us','close_us','available_us'):
            need(rows.schema[name]==pl.Int64 and rows[name].null_count()==0,'Known integer daily time')
        need(np.array_equal(rows['close_us'].to_numpy(),rows['open_us'].to_numpy()+DAY),'Exclusive full UTC daily close')
        need(np.all(rows['open_us'].to_numpy()%DAY==0),'UTC daily candle alignment')
        close=rows['close'].to_numpy();high=rows['high'].to_numpy();low=rows['low'].to_numpy()
        need(np.isfinite(np.c_[close,high,low]).all() and np.all(low>0) and np.all(low<=close) and np.all(close<=high),'Finite consistent official daily OHLC')
        stamps=rows['close_us'].to_numpy();available=rows['available_us'].to_numpy()
        need(np.all(available>=stamps),'A candle cannot be available before its exclusive close')
        indices=np.searchsorted(stamps,decisions,side='right')-1;held=False;day_weights=[]
        for decision,index in zip(decisions,indices,strict=True):
            index=int(index);decision=int(decision)
            need(index>=199 and int(stamps[index])==decision,'Current completed UTC daily bar, not a future bar')
            need(np.all(np.diff(stamps[index-199:index+1])==DAY),'SMA200 requires200 consecutive calendar days')
            need(np.all(available[index-199:index+1]<=decision),'All200 observations available at the decision')
            upper=max(float(v) for v in high[index-20:index]);lower=min(float(v) for v in low[index-20:index])
            mean=math.fsum(float(v) for v in close[index-199:index+1])/200
            scalar_entry=float(close[index])>upper and float(close[index])>mean
            scalar_exit=float(close[index])<lower
            candles=np.zeros((200,6));candles[:,0]=stamps[index-199:index+1]//1000
            candles[:,2]=close[index-199:index+1];candles[:,3]=high[index-199:index+1];candles[:,4]=low[index-199:index+1]
            rules=Public();rules.candles=candles;rules.close=float(close[index]);exits=[]
            rules.liquidate=lambda:exits.append(True)
            need((rules.should_long() and all(f() for f in rules.filters()))==scalar_entry,'Raw entry/filter hooks equal scalar prior20/SMA200')
            rules.update_position();need(bool(exits)==scalar_exit,'Raw exit hook equals strict prior20 lower break')
            before=held
            if held and scalar_exit:held=False
            elif not held and scalar_entry:held=True
            day_weights.append(.3 if held else 0.)
            if held!=before:witnesses.append(dict(symbol=symbol,decision_us=decision,held=held,close=float(close[index]),upper=upper,lower=lower,SMA200=mean))
        offsets=((calendar-int(calendar[0]))//DAY).astype(np.int64)
        weights[:,column]=np.asarray(day_weights)[offsets]
    # Last minute intent is common end liquidation; an infeasible residual stays MTM.
    weights[-1]=0.
    return weights,dict(warmup_bars=200,donchian_previous_bars=20,SMA_current_inclusive_bars=200,
        original_hook_formula_checks=True,production_fixed_targets_called=False,initial_held_state='FLAT',
        warmup_account_trading=False,transition_witnesses=witnesses,source_availability='DECLARED_CLOSE_PROXY_NOT_REAL_PUBLICATION_CERTIFICATION')

def verify_saved_targets(daily,calendar,intent,targets,receipt):
    """Actual new saved target outputs only; never construct executable orders."""
    strategy='COIN_JESSE_DONCHIAN_1D_SPOT_ADAPTER'
    need(receipt['strategy_id']==strategy and receipt['paired_comparison_allowed'] and not receipt['warmup_failed'],'Only complete paired daily target output')
    need(receipt['calendar_sha256']==hashlib.sha256(calendar.tobytes()).hexdigest() and receipt['decision_count']==len(calendar),'Exact complete scoring calendar')
    need(receipt['timeframe_minutes']==1440 and receipt['original_public_hook_reused'] and not receipt['original_native_Jesse_engine_replicated'],'Fixed original daily signal hook port')
    need(receipt['public_upstream_sha256']==PINS and receipt['daily_prices_used_for_execution_or_risk'] is False and receipt['model_fits']==0,'Exact hook and separate minute execution/risk scope')
    weights,proof=expected_daily_weights(daily,calendar)
    need(intent.height==2*len(calendar) and set(intent['symbol'].unique().to_list())==set(SYMBOLS),'All minute intents without missing/drop')
    compressed=[]
    for column,symbol in enumerate(SYMBOLS):
        one=intent.filter(pl.col('symbol')==symbol).sort('decision_us')
        need(one.height==len(calendar) and np.array_equal(one['decision_us'].to_numpy(),calendar),'Exactly one daily-derived intent per scoring minute')
        need(np.array_equal(one['available_us'].to_numpy(),calendar) and np.array_equal(one['target_weight'].to_numpy(),weights[:,column]),'Past-only signal availability and exact daily held-state weights')
        reasons=np.where(weights[:,column]==.3,'PUBLIC_DAILY_LONG_HOLD','PUBLIC_DAILY_FLAT').astype(object)
        reasons[-1]='COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL'
        need(np.array_equal(one['reason'].to_numpy(),reasons),'Saved reasons reflect fresh daily hook state and terminal intent')
        need(np.array_equal(one['comparison_order_eligible_us'].to_numpy(),calendar+MINUTE)
            and np.array_equal(one['preserved_v8_intent_earliest_order_us'].to_numpy(),calendar+5_000_000),'Original minute comparison eligibility distinct from preserved5second metadata')
        changes=np.r_[True,np.diff(weights[:,column])!=0]
        compressed.extend(dict(available_us=int(t),symbol=symbol,target_weight=float(w))
            for t,w in zip(calendar[changes],weights[:,column][changes],strict=True))
    expected=pl.DataFrame(compressed).sort(['available_us','symbol'])
    need(expected.equals(targets.sort(['available_us','symbol'])),'Saved compressed targets exactly equal full minute intent changes')
    return dict(**proof,strategy=strategy,completed_minute_decisions=len(calendar),target_rows_verified=targets.height,
        terminal_target_is_zero=True,terminal_day_close_used_for_signal=False,warmup_used_for_account_trades=False)

