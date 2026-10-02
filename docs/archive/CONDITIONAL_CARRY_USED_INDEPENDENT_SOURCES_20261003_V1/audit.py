"""Independent fixed conditional carry source/transaction/NAV audit; never calls simulate_account."""
from decimal import Decimal, localcontext
import hashlib, json, math
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
WORK=STATE/'test-conditional-carry-independent-audit-20261003-v1'
SYMBOLS=('BTCUSDT','ETHUSDT');MINUTE_US=60000000
D=Decimal;ZERO=D(0);CAPITAL=D(10000);RESERVE=D(1250)
SPOT_RATE=D('.001');PERP_RATE=D('.00055');HALF_SPREAD=SLIP=D('.0004')
USDT_TOL=D('1e-7');RATIO_TOL=D('1e-10');QTY_TOL=D('1e-12')
MAX_USDT_ERROR=MAX_RATIO_ERROR=ZERO


def need(ok,message):
    if not ok:raise AssertionError(message)


def number(value):
    need(type(value) in (int,float) and math.isfinite(value),'Finite original/output scalar required')
    return D.from_float(float(value))


def close(actual,expected,tolerance=USDT_TOL):
    global MAX_USDT_ERROR,MAX_RATIO_ERROR
    error=abs(number(actual)-expected)
    if tolerance==USDT_TOL:MAX_USDT_ERROR=max(MAX_USDT_ERROR,error)
    elif tolerance==RATIO_TOL:MAX_RATIO_ERROR=max(MAX_RATIO_ERROR,error)
    need(error<=tolerance,'Independent ledger mismatch:'+str(error))
    return error


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()


def expected_fill(symbol,product,side,gross,mid):
    """Independent Decimal received-asset formulas, fixed declared proxy costs."""
    need(symbol in SYMBOLS and product in ('SPOT','PERP') and side in ('buy','sell')
         and gross>0 and mid>0,'Explicit positive leg fill')
    with localcontext() as context:
        context.prec=80
        fill=mid*(1+(HALF_SPREAD+SLIP)*(1 if side=='buy' else -1))
        if product=='SPOT':
            if side=='buy':
                amount=gross*SPOT_RATE;asset=symbol.removesuffix('USDT')
                base=gross*(1-SPOT_RATE);quote=-gross*fill;fee=amount*mid
            else:
                amount=fee=gross*fill*SPOT_RATE;asset='USDT';base=-gross
                quote=gross*fill*(1-SPOT_RATE)
        else:
            amount=fee=gross*fill*PERP_RATE;asset='USDT';base=quote=ZERO
        return dict(fill_price=fill,base_position_delta=base,spot_quote_delta=quote,
            fee_asset=asset,fee_amount=amount,fee_USDT=fee,
            spread_USDT=gross*mid*HALF_SPREAD,slippage_USDT=gross*mid*SLIP,
            gross_mid_notional_USDT=gross*mid)


class Wallet:
    """Reconcile recorded sparse transactions, without choosing trades or prices."""
    def __init__(self):
        self.cash=CAPITAL;self.p={s:dict(spot=ZERO,short=ZERO,margin=ZERO,entry=ZERO) for s in SYMBOLS}
        self.deposited=set();self.funding=ZERO;self.fees=self.spread=self.slippage=self.turnover=ZERO
    def debit(self,symbol,amount):
        need(amount>=0,'Nonnegative quote debit required')
        free=max(ZERO,min(self.cash,amount));isolated=amount-free
        self.cash-=free;self.p[symbol]['margin']-=isolated
        return free,isolated
    def reserve(self,symbol):
        need(symbol not in self.deposited,'Only one initial isolated deposit per asset')
        self.cash-=RESERVE;self.p[symbol]['margin']+=RESERVE;self.deposited.add(symbol)
    def apply_fill(self,row,original_mid):
        symbol,product,side=(row[key] for key in ('symbol','product','side'))
        need(symbol in SYMBOLS,'Declared asset only')
        p=self.p[symbol];gross=number(row['gross_quantity']);mid=number(original_mid)
        if product=='SPOT' and side=='buy':self.reserve(symbol)
        before=self.cash;expect=expected_fill(symbol,product,side,gross,mid)
        errors=[close(row['cash_before'],before)]
        for field,value in expect.items():
            if field=='fee_asset':need(row[field]==value,'Received fee asset differs')
            else:errors.append(close(row[field],value,QTY_TOL if field=='base_position_delta' else USDT_TOL))
        close(row['mid_proxy'],mid);free=isolated=realized=ZERO
        with localcontext() as context:
            context.prec=80
            if product=='SPOT':
                self.cash+=expect['spot_quote_delta'];p['spot']+=expect['base_position_delta']
                if side=='sell':
                    need(abs(p['spot'])<=QTY_TOL,'All received net base must be sold, no oversell')
                    p['spot']=ZERO  # Declared exact-fraction/dust-zero proxy, not a venue filter.
            else:
                free,isolated=self.debit(symbol,expect['fee_USDT'])
                if side=='sell':
                    need(p['short']==0,'No repeated opening short')
                    p['short']=gross;p['entry']=expect['fill_price']
                else:
                    close(row['gross_quantity'],p['short'],QTY_TOL)
                    realized=gross*(p['entry']-expect['fill_price'])
                    self.cash+=p['margin']+realized;p['margin']=p['short']=p['entry']=ZERO
            self.fees+=expect['fee_USDT'];self.spread+=expect['spread_USDT'];self.slippage+=expect['slippage_USDT']
            self.turnover+=gross*mid/CAPITAL
        for field,value in (('cash_after',self.cash),('perp_realized_PnL_USDT',realized),
                            ('fee_free_cash_debit',free),('fee_isolated_balance_debit',isolated)):
            errors.append(close(row[field],value))
        need(self.cash>=0,'No negative free cash after fill')
        need(row['no_short_sale_proceeds'] is True and row['fractional_quantity_proxy'] is True,'Declared accounting scope differs')
        return max(errors)
    def apply_funding(self,row,original_rate,strictly_past_mark,owned):
        symbol=row['symbol'];need(symbol in SYMBOLS,'Original funding asset required')
        rate=number(original_rate);p=self.p[symbol]
        need(row['ownership_qualified'] is owned,'Strict interval event ownership differs')
        close(row['raw_rate'],rate,QTY_TOL)
        amount=p['short']*number(strictly_past_mark)*rate if owned else ZERO
        free=isolated=ZERO
        if amount>=0:self.cash+=amount
        else:free,isolated=self.debit(symbol,-amount)
        self.funding+=amount
        need(self.cash>=0,'No negative free cash after funding debit')
        for field,value in (('signed_funding_USDT',amount),('free_cash_debit',free),
                            ('isolated_balance_debit',isolated),('cumulative_funding_USDT',self.funding)):
            close(row[field],value)
        need(row['funding_unit_certified'] is False and row['charge_mark_or_native_settlement_certified'] is False,
             'Conditional fractions must not become native funding proof')
    def valuation(self,source_prices):
        nav=self.cash;gross=ZERO;assets={};equities={}
        with localcontext() as context:
            context.prec=80
            for symbol in SYMBOLS:
                spot,mark=(number(value) for value in source_prices[symbol])
                p=self.p[symbol];spot_value=p['spot']*spot
                equity=p['margin']+p['short']*(p['entry']-mark)
                need(not p['short'] or equity>0,'Active isolated insolvency cannot use cross-leg rescue')
                nav+=spot_value+equity;asset=spot_value+p['short']*mark
                gross+=asset;assets[symbol]=asset;equities[symbol]=equity
            need(nav>0,'Insolvent proxy must fail without clipping')
            return nav,gross/nav,{s:assets[s]/nav for s in SYMBOLS},equities


class Observations:
    def __init__(self):self.peak=CAPITAL;self.max_dd=ZERO;self.first_breach=None
    def record(self,timestamp,nav,gross,assets,equities,held,cause):
        need(nav>0,'Finite positive conditional NAV required')
        self.peak=max(self.peak,nav);self.max_dd=max(self.max_dd,(self.peak-nav)/self.peak)
        reasons=(['TOTAL_GROSS'] if gross>=D('.6') else [])
        reasons+=['ASSET_GROSS_'+s for s in SYMBOLS if assets[s]>=D('.3')]
        reasons+=['ISOLATED_EQUITY_'+s for s in SYMBOLS if equities[s]<=RESERVE/D(2)]
        if held and reasons and self.first_breach is None:self.first_breach=dict(signal_us=timestamp,cause=cause,reasons=reasons)
        return self.peak,self.max_dd

# Final source-clock/8fill/732event/Arrow-minute/daily/month mapping awaits frozen
# source/protocol/output bindings and a verified actual closed task with exit zero.

import importlib.util, os, sys, time, resource, statistics
from array import array
from datetime import datetime, timezone
OUT=ROOT/'reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json'
MONTHS=('2025-08','2025-09','2025-10','2025-11');START=1754006400000000;END=1764547200000000

def load(path):return json.loads(Path(path).read_bytes())
def write_new(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')

def original_inputs(spec,actual,reader):
    import pyarrow.parquet as pq
    options=load(ROOT/spec['source_options_path']);fundspec=load(ROOT/spec['funding_contract_path'])
    accepted=load(ROOT/fundspec['source_acceptance_path'])
    selected=options['sources'];fund=[r for r in accepted['sources'] if r['kind']=='fundingRate']
    lookup={(r['kind'],r['symbol'],r['month']):r for r in selected}
    need(len(selected)==len(lookup)==24 and len(fund)==8,'Exact 24close+8fund source metadata required')
    expected=[dict(kind=r['kind'],symbol=r['symbol'],month=r['month'],parquet_path=r['parquet_path'],
                   parquet_sha256=r['parquet_sha256'],rows=r['rows']) for r in selected+fund]
    sortkey=lambda r:(r['kind'],r['symbol'],r['month'])
    need(sorted(actual['input_bindings'],key=sortkey)==sorted(expected,key=sortkey),'Actual32 source inputs differ from acceptance')
    prices={s:{key:array('d') for key in ('spot','mark')} for s in SYMBOLS}
    for symbol in SYMBOLS:
        for month in MONTHS:
            streams=[reader.source_rows(lookup[k,symbol,month]) for k in ('spot1m','markPriceKlines','indexPriceKlines')]
            for spot,mark,index in zip(*streams,strict=True):
                need(spot[:2]==mark[:2]==index[:2],'Original close clocks differ')
                prices[symbol]['spot'].append(spot[2]);prices[symbol]['mark'].append(mark[2])
        need(len(prices[symbol]['spot'])==len(prices[symbol]['mark'])==175680,'All175680 source minutes required')
    events=[]
    for entry in fund:
        path=Path(entry['parquet_path']);expected_path=STATE/'v8-funding-mark-index-source-20261002-v1'/(
            'fundingRate-'+entry['symbol']+'-'+entry['month'])/'source.parquet'
        need(path==expected_path and not path.is_symlink() and sha(path)==entry['parquet_sha256'],'Accepted original funding bytes/path changed')
        rows=pq.read_table(path,columns=['calc_time_ms','last_funding_rate'],use_threads=False).to_pylist()
        need(len(rows)==entry['rows'],'Every original funding row must remain')
        lo,hi=reader.bounds(entry['month'])
        for row in rows:
            need(type(row['calc_time_ms']) is int and lo<=row['calc_time_ms']*1000<hi,'Original funding timestamp bounds differ')
            rate=row['last_funding_rate'];number(rate)
            events.append(dict(symbol=entry['symbol'],event_us=row['calc_time_ms']*1000,rate=rate))
        need(sha(path)==entry['parquet_sha256'],'Original funding changed during read')
    events.sort(key=lambda r:(r['event_us'],r['symbol']))
    need(len(events)==732 and len({(r['symbol'],r['event_us']) for r in events})==732,'All732 original events exactly once')
    need(all(sum(r['symbol']==s for r in events)==366 for s in SYMBOLS),'All366 original events per symbol')
    return prices,events,expected

def main():
    import pyarrow.parquet as pq
    bound=load(WORK/'ACTUAL_BINDING.json')
    need(sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and not OUT.exists()
         and sha(__file__)==bound['checker_sha256'],'Clean interpreter/new report/prebound checker required')
    report=dict(status='FAIL_CONDITIONAL_CARRY_DECIMAL_INDEPENDENT_AUDIT',binding=dict(task_id=os.environ['COIN_TASK_ID'],
        checker_sha256=sha(__file__),ACTUAL_BINDING_sha256=sha(WORK/'ACTUAL_BINDING.json')),
        independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),
        cash_absolute_tolerance_USDT=str(USDT_TOL),ratio_absolute_tolerance=str(RATIO_TOL),
        actual_HTTP_requests=0,orders_sent=0,models_fit=0,old_QA_or_green_tests_repeated=False,
        raw_ZIP_or_CRC_read=False,simulate_account_called=False,candidate_status='NO_QUALIFIED_CANDIDATE',
        funding_unit_certified=False,native_Bybit_settlement_proven=False,completed_minutes_verified=0)
    started=time.monotonic()
    try:
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Prebound small source changed:'+path)
        spec=load(ROOT/bound['protocol_path']);actual=load(ROOT/bound['actual_report_path']);summary=actual['summary']
        need(D(str(spec['independent_cash_absolute_tolerance_USDT']))==USDT_TOL
             and D(str(spec['independent_ratio_absolute_tolerance']))==RATIO_TOL,'Preregistered tolerances changed')
        need(actual['status']=='COMPLETE_CONDITIONAL_CARRY_PROXY_ACCOUNT_UNIT_UNCERTIFIED_NOT_NATIVE_OR_LONG_TERM_APR'
             and actual['source_bytes_unchanged'] is True and actual['binding']['task_id']==bound['actual_task_id'],
             'Actual report failed/partial/changed')
        need(actual['binding']==load(Path(actual['run_dir'])/'RUN_BINDING.json')
             and actual['binding']['protocol_sha256']==sha(ROOT/bound['protocol_path'])
             and actual['binding']['rules']==spec['rules'],'Exact actual rules/source/run binding required')
        need(spec['contract_id']=='CONDITIONAL_CARRY_ACCOUNT_V1' and spec['period_start']=='2025-08-01'
             and spec['period_end_exclusive']=='2025-12-01' and spec['symbols']==list(SYMBOLS)
             and spec['source_calendar']==list(MONTHS),'Only the frozen full122day window and fixed assets')
        rules=spec['rules']
        fixed_numbers=dict(initial_capital_USDT=10000,nominal_per_asset_per_leg_at_signal_USDT=1250,
            isolated_initial_margin_per_asset_USDT=1250,total_gross_stop_at_or_above=.6,
            asset_two_leg_gross_stop_at_or_above=.3,isolated_equity_stop_at_or_below_initial_margin_fraction=.5,
            spot_fee_bps_per_side=10,perp_fee_bps_per_side=5.5,each_leg_roundtrip_spread_bps=8,slippage_bps_per_side=4)
        need(all(rules[k]==v for k,v in fixed_numbers.items()) and rules['monthly_reset'] is False
             and rules['reentry'] is False and rules['real_lot_filters'] is False,'Fixed capital/cost/risk rules differ')
        need(all(actual['binding']['source_hashes'].get(k)==v for k,v in spec['frozen_sources'].items()),
             'Actual binding must cover every preregistered source byte')
        report['verified_source_hashes']=actual['binding']['source_hashes']
        for path,digest in report['verified_source_hashes'].items():need(sha(ROOT/path)==digest,'Frozen actual code/proof changed:'+path)
        need(sha(Path(bound['price_reader_path']))==bound['price_reader_sha256'],'Accepted independent reader changed')
        module_spec=importlib.util.spec_from_file_location('basis_source_reader',bound['price_reader_path'])
        reader=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(reader)
        report['actual_task']=reader.task(bound['actual_task_id'])
        smoke=load(ROOT/spec['required_smoke_receipt']);report['smoke_actual_task']=reader.task(smoke['binding']['task_id'])
        need(smoke['test_exit_code']==0 and smoke['source_bytes_unchanged'] is True
             and smoke['binding']['source_hashes']==actual['binding']['source_hashes']
             and actual['accepted_smoke_sha256']==sha(ROOT/spec['required_smoke_receipt']),'Closed same-source synthetic binding required')
        need(smoke['status']=='PASS_CONDITIONAL_CARRY_SYNTHETIC_ACCOUNTING_NOT_MARKET_RESULT'
             and smoke['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0)
             and smoke['price_arrays_read'] is False and smoke['funding_arrays_read'] is False,
             'Only the completed new synthetic receipt; no prior market replay')
        funding_spec=load(ROOT/spec['funding_contract_path']);probe=load(ROOT/funding_spec['unit_probe']['path'])
        failed_task_path=STATE/'task-progress'/('task-'+probe['binding']['task_id']+'.json')
        failed_task=load(failed_task_path)
        need(failed_task['id']==probe['binding']['task_id'] and failed_task['status']=='failed'
             and failed_task['exit_code']==1 and probe['unit_evidence']['matched_records']==0,
             'Preserve real failed1/zero-match unit evidence, never certify fraction assumptions')
        unit=actual['unit_interpretation']
        need(unit['raw_rate_unit']=='UNCONFIRMED' and unit['assumed_funding_rate_unit']=='FRACTION'
             and unit['bp_multiplier']==10000 and unit['conditional_fraction_assumption'] is True
             and unit['basis']=='EXPLICIT_UNVERIFIED_FRACTION_ASSUMPTION_AFTER_HTTP451'
             and unit['full_732_event_unit_certified'] is False and unit['sampled_API_unit_certified'] is False,
             'Conditional raw fraction mathematics only')
        report['unit_failure_task']=dict(id=failed_task['id'],status=failed_task['status'],exit_code=1,
            pid=failed_task['pid'],start_ticks=failed_task['start_ticks'],sha256=sha(failed_task_path))
        frames={}
        need({r['kind'] for r in actual['output_bindings']}=={'fill_ledger','funding_ledger','minute_nav','daily_nav'},'Exactly four real ledger artifacts')
        for row in actual['output_bindings']:
            path=Path(row['path']);need(path.parent==Path(actual['run_dir']) and sha(path)==row['sha256'],'Exact physical output bytes changed')
            file=pq.ParquetFile(path);need(file.metadata.num_rows==row['rows'],'Output physical row count differs')
            frames[row['kind']]=file
        fills=frames['fill_ledger'].read(use_threads=False).to_pylist();fundrows=frames['funding_ledger'].read(use_threads=False).to_pylist()
        daily=frames['daily_nav'].read(use_threads=False).to_pylist()
        need(len(fills)==8 and len(fundrows)==732 and len(daily)==122,'Complete8fills/732events/122days required')
        prices,events,inputs=original_inputs(spec,actual,reader)
        need([(r['symbol'],r['event_us'],r['raw_rate']) for r in fundrows]==[(e['symbol'],e['event_us'],e['rate']) for e in events],
             'Original event identities/rates/order changed or excluded rows dropped')
        entry=START+2*MINUTE_US+1;exit_time=END+1;exit_reason='PROTOCOL_TERMINAL';pending=None
        planned={s:RESERVE/number(prices[s]['spot'][0]) for s in SYMBOLS}
        need(summary['first_signal_us']==START+MINUTE_US and summary['entry_us']==entry,'First signal/next-minute entry differs')
        for s in SYMBOLS:
            close(summary['planned_quantity_from_first_signal'][s],planned[s],QTY_TOL)
            close(summary['matched_quantity_from_native_received_fill'][s],planned[s],QTY_TOL)
        expected_order=[(s,product,side) for s in SYMBOLS for product,side in [('SPOT','buy'),('PERP','sell')]]+[
            (s,product,side) for s in SYMBOLS for product,side in [('SPOT','sell'),('PERP','buy')]]
        need([(f['symbol'],f['product'],f['side']) for f in fills]==expected_order,'Eight fixed leg actions/order changed')
        wallet=Wallet();obs=Observations();held=False;fill_cursor=event_cursor=0;owned=0
        minute_peak=CAPITAL;minute_dd=ZERO;maximum_gross=ZERO;max_assets=dict.fromkeys(SYMBOLS,ZERO)
        min_equities=dict.fromkeys(SYMBOLS,RESERVE);day_ends={};month_ends={};breaches=[]
        asset_funding=dict.fromkeys(SYMBOLS,ZERO);asset_fees={s:dict(SPOT=ZERO,PERP=ZERO) for s in SYMBOLS};entry_notionals={}
        def source_values(index):
            return {s:(prices[s]['spot'][index],prices[s]['mark'][index]) if index>=0 else (0.,0.) for s in SYMBOLS}
        def observe(index):
            nonlocal maximum_gross
            values=wallet.valuation(source_values(index));nav,gross,assets,equities=values
            obs.record(0,*values,False,'OBSERVATION_ONLY')
            maximum_gross=max(maximum_gross,gross)
            for s in SYMBOLS:
                max_assets[s]=max(max_assets[s],assets[s])
                if wallet.p[s]['short']:min_equities[s]=min(min_equities[s],equities[s])
            return values
        def risk(index,stamp,cause):
            nonlocal pending,exit_time,exit_reason
            if not held:return
            nav,gross,assets,equities=observe(index)
            reasons=(['TOTAL_GROSS'] if gross>=D('.6') else [])
            reasons+=['ASSET_GROSS_'+s for s in SYMBOLS if assets[s]>=D('.3')]
            reasons+=['ISOLATED_EQUITY_'+s for s in SYMBOLS if equities[s]<=RESERVE/D(2)]
            if reasons:
                breaches.append(dict(signal_us=stamp,cause=cause,reasons=reasons,nav=nav,total_gross=gross,
                                     asset_two_leg_gross=assets,isolated_equity=equities))
                if pending is None:
                    following=(stamp-(START+MINUTE_US))//MINUTE_US+1
                    if following<175680:
                        pending=following;exit_time=START+(pending+1)*MINUTE_US+1;exit_reason='SELF_DEFINED_RISK_STOP'
                        obs.first_breach=dict(signal_us=stamp,cause=cause,reasons=reasons)
        for batch in frames['minute_nav'].iter_batches(batch_size=4096,use_threads=False):
            for row in batch.to_pylist():
                index=report['completed_minutes_verified'];closed=START+(index+1)*MINUTE_US;snapshot=closed+1
                need(row['close_us']==closed and row['valuation_us']==snapshot,'Whole exact minute NAV timeline differs')
                while event_cursor<len(events) and events[event_cursor]['event_us']<=snapshot:
                    event=events[event_cursor];ledger=fundrows[event_cursor];timestamp=event['event_us'];s=event['symbol']
                    previous=(timestamp-(START+MINUTE_US)-1)//MINUTE_US
                    before=observe(previous)[0];qual=held and entry<timestamp<exit_time
                    mark=prices[s]['mark'][previous] if previous>=0 else None
                    need(ledger['mark_close_us']==(START+(previous+1)*MINUTE_US if previous>=0 else None),
                         'Funding mark must be the last strictly past close')
                    if mark is None:need(ledger['mark_proxy'] is None,'No available pre-first-close mark')
                    else:need(ledger['mark_proxy']==mark and ledger['mark_close_us']<timestamp,'Funding source mark/availability differs')
                    close(ledger['held_short_quantity'],wallet.p[s]['short'],QTY_TOL);close(ledger['nav_before'],before)
                    prior_funding=wallet.funding
                    wallet.apply_funding(ledger,event['rate'],mark,qual);asset_funding[s]+=wallet.funding-prior_funding
                    after=observe(previous)[0];close(ledger['nav_after'],after)
                    need(ledger['ownership_rule']=='STRICT_ENTRY_LT_EVENT_LT_EXIT_UNCERTIFIED','Funding ownership claim differs')
                    close(ledger['prefix_peak_nav'],obs.peak);close(ledger['prefix_max_drawdown'],obs.max_dd,RATIO_TOL)
                    need(ledger['reason']==('CONDITIONAL_SIGNED_FUNDING' if qual else 'OUTSIDE_STRICT_HOLD_INTERVAL'),
                         'Funding excluded/owned reason differs')
                    need(ledger['distance_from_entry_us']==abs(timestamp-entry)
                         and ledger['distance_from_exit_us']==abs(timestamp-summary['exit_us']),'Boundary event witness differs')
                    owned+=qual;risk(previous,timestamp,'FUNDING_EVENT_AFTER_CASH');event_cursor+=1
                observe(index);risk(index,snapshot,'CLOSED_MINUTE_BEFORE_SCHEDULED_FILLS')
                while fill_cursor<len(fills) and fills[fill_cursor]['timestamp_us']==snapshot:
                    fill=fills[fill_cursor];s=fill['symbol'];opening=fill_cursor<4
                    need((opening and index==1) or (not opening and snapshot==exit_time),'Entry/first-stop/terminal fill timing differs')
                    signal=START+MINUTE_US if opening else (obs.first_breach['signal_us'] if obs.first_breach else END)
                    need(fill['price_close_us']==closed and fill['signal_us']==signal and fill['price_close_us']<snapshot
                         and (opening or fill['reason']==exit_reason),'Fill price availability/signal/reason differs')
                    q=planned[s]/(1-SPOT_RATE) if opening and fill['product']=='SPOT' else planned[s]
                    close(fill['gross_quantity'],q,QTY_TOL)
                    mid=prices[s]['spot' if fill['product']=='SPOT' else 'mark'][index]
                    close(fill['nav_before'],observe(index)[0]);prior_fees=wallet.fees;wallet.apply_fill(fill,mid)
                    asset_fees[s][fill['product']]+=wallet.fees-prior_fees
                    if opening:entry_notionals[s,fill['product']]=q*number(mid)
                    close(fill['nav_after'],observe(index)[0]);close(fill['prefix_peak_nav'],obs.peak)
                    close(fill['prefix_max_drawdown'],obs.max_dd,RATIO_TOL);fill_cursor+=1
                    if fill_cursor==4:held=True
                    if fill_cursor==8:held=False
                nav,gross,assets,equities=observe(index);minute_peak=max(minute_peak,nav)
                minute_dd=max(minute_dd,(minute_peak-nav)/minute_peak)
                risk(index,snapshot,'CLOSED_MINUTE_AFTER_FILLS')
                for field,value in [('nav',nav),('free_cash',wallet.cash),('cumulative_fees',wallet.fees),
                    ('cumulative_spread',wallet.spread),('cumulative_slippage',wallet.slippage),
                    ('cumulative_funding',wallet.funding),('all_observation_peak_nav',obs.peak)]:close(row[field],value)
                for field,value in [('total_gross',gross),('cumulative_turnover',wallet.turnover),
                                    ('all_observation_max_drawdown',obs.max_dd)]:close(row[field],value,RATIO_TOL)
                for s in SYMBOLS:
                    close(row[s+'_gross'],assets[s],RATIO_TOL);close(row[s+'_isolated_equity'],equities[s])
                    close(row[s+'_spot_and_short_q'],wallet.p[s]['spot'],QTY_TOL)
                    need(abs(wallet.p[s]['spot']-wallet.p[s]['short'])<=QTY_TOL,'Net inventory hedge mismatch at minute observation')
                date=datetime.fromtimestamp((closed-1)//1000000,timezone.utc).date()
                need(row['date']==date,'UTC daily attribution changed')
                totals=dict(nav=nav,fees=wallet.fees,spread=wallet.spread,slippage=wallet.slippage,
                            funding=wallet.funding,turnover=wallet.turnover)
                day_ends[date]=totals;month_ends[date.strftime('%Y-%m')]=totals
                report['completed_minutes_verified']+=1
                if index%43200==0:print(json.dumps(dict(verified_minutes=index+1,total=175680)),flush=True)
        need(report['completed_minutes_verified']==175680 and fill_cursor==8 and event_cursor==732
             and not held and all(p['spot']==p['short']==p['margin']==0 for p in wallet.p.values()),'Full minute/events/fills/terminal flat required')
        need(summary['exit_us']==exit_time and summary['exit_reason']==exit_reason
             and summary['stop_signal_us']==(obs.first_breach['signal_us'] if obs.first_breach else None),
             'First risk signal/next-close permanent exit differs')
        need(len(summary['risk_breach_witnesses'])==len(breaches),'Risk breach observations were omitted or invented')
        for saved,expected in zip(summary['risk_breach_witnesses'],breaches,strict=True):
            need(all(saved[k]==expected[k] for k in ('signal_us','cause','reasons')),'Risk reason/timing differs')
            close(saved['nav'],expected['nav']);close(saved['total_gross'],expected['total_gross'],RATIO_TOL)
            for s in SYMBOLS:
                close(saved['asset_two_leg_gross'][s],expected['asset_two_leg_gross'][s],RATIO_TOL)
                close(saved['isolated_equity'][s],expected['isolated_equity'][s])
        previous=dict(nav=CAPITAL,fees=ZERO,spread=ZERO,slippage=ZERO,funding=ZERO,turnover=ZERO);daily_nav=[]
        for row,(date,totals) in zip(daily,sorted(day_ends.items()),strict=True):
            need(row['date']==date,'Every UTC day required')
            for field,value in [('nav',totals['nav']),('fee_cumulative',totals['fees']),
                ('cost_cumulative',totals['spread']+totals['slippage']),('fees',totals['fees']-previous['fees']),
                ('execution_costs',totals['spread']+totals['slippage']-previous['spread']-previous['slippage'])]:close(row[field],value)
            close(row['turnover_cumulative'],totals['turnover'],RATIO_TOL)
            close(row['turnover'],totals['turnover']-previous['turnover'],RATIO_TOL)
            daily_nav.append(float(totals['nav']));previous=totals
        previous=dict(nav=CAPITAL,fees=ZERO,spread=ZERO,slippage=ZERO,funding=ZERO);months=[]
        need([r['month'] for r in summary['months']]==list(MONTHS),'All continuous four months required')
        for row,(month,totals) in zip(summary['months'],month_ends.items(),strict=True):
            net=totals['nav']-previous['nav'];fees=totals['fees']-previous['fees'];spread=totals['spread']-previous['spread']
            slip=totals['slippage']-previous['slippage'];funding=totals['funding']-previous['funding']
            expected=dict(start_NAV=previous['nav'],end_NAV=totals['nav'],net_PnL_USDT=net,
                gross_cost_addback_PnL_USDT=net+fees+spread+slip,fees_USDT=fees,spread_USDT=spread,
                slippage_USDT=slip,signed_funding_USDT=funding)
            need(row['month']==month and row['monthly_account_reset'] is False,'No monthly account reset or selection')
            for field,value in expected.items():close(row[field],value)
            months.append(dict(month=month,**{k:float(v) for k,v in expected.items()}));previous=totals
        total_cost=wallet.fees+wallet.spread+wallet.slippage;net=wallet.cash-CAPITAL
        price_gross=sum(planned[s]*(number(prices[s]['spot'][(exit_time-START-1)//MINUTE_US-1])-number(prices[s]['spot'][1])
            +number(prices[s]['mark'][1])-number(prices[s]['mark'][(exit_time-START-1)//MINUTE_US-1])) for s in SYMBOLS)
        bridge=CAPITAL+price_gross+wallet.funding-total_cost
        need(abs(bridge-wallet.cash)<=USDT_TOL,'Terminal net-quantity price/funding/cost NAV bridge failed')
        expected=dict(initial_capital_USDT=CAPITAL,final_nav_USDT=wallet.cash,net_PnL_USDT=net,
            gross_cost_addback_PnL_USDT=net+total_cost,fees_USDT=wallet.fees,assumed_spread_USDT=wallet.spread,
            assumed_slippage_USDT=wallet.slippage,signed_conditional_funding_USDT=wallet.funding)
        for field,value in expected.items():close(summary[field],value)
        for field,value in [('period_net_return',net/CAPITAL),('turnover',wallet.turnover),('minute_max_drawdown',minute_dd),
                            ('all_observation_max_drawdown',obs.max_dd),('maximum_total_gross',maximum_gross)]:close(summary[field],value,RATIO_TOL)
        for s in SYMBOLS:
            close(summary['maximum_asset_two_leg_gross'][s],max_assets[s],RATIO_TOL)
            close(summary['minimum_isolated_equity'][s],min_equities[s])
        need(summary['fills']==8 and summary['all_source_events']==732 and summary['owned_funding_events']==owned
             and summary['excluded_funding_events']==732-owned and summary['rows']==175680,'Financial counts differ')
        nearby=[r for r in fundrows if min(abs(r['event_us']-entry),abs(r['event_us']-exit_time))<=5000000]
        need(summary['events_within_5s_of_entry_or_exit']==len(nearby)
             and summary['near_boundary_event_witnesses']==nearby[:8]
             and summary['real_funding_ownership_within_5s_guaranteed'] is False,'Boundary uncertainty witnesses differ')
        need(summary['permanent_cash_after_exit'] is True and summary['caps_are_exit_triggers_not_guaranteed_execution_caps'] is True
             and summary['terminal_spot_quantity']==summary['terminal_short_quantity']==dict.fromkeys(SYMBOLS,0.)
             and summary['terminal_dust_proxy']==0. and summary['candidate_status']=='NO_QUALIFIED_CANDIDATE'
             and summary['unseen_qualification'] is False and summary['native_execution_or_margin_liquidation_proven'] is False,
             'Terminal flat/cash/conditional risk scope differs')
        close(summary['continuous_monthly_net_reconciliation_error_USDT'],ZERO)
        for saved in summary['per_asset']:
            s=saved['symbol'];need(s in SYMBOLS,'Unexpected asset summary')
            for field,value in [('signed_funding_USDT',asset_funding[s]),('spot_fee_USDT',asset_fees[s]['SPOT']),
                ('perp_fee_USDT',asset_fees[s]['PERP']),('actual_entry_spot_mid_notional_USDT',entry_notionals[s,'SPOT']),
                ('actual_entry_perp_mid_notional_USDT',entry_notionals[s,'PERP'])]:close(saved[field],value)
        need([r['symbol'] for r in summary['per_asset']]==list(SYMBOLS),'Both fixed asset summaries required')
        returns=[daily_nav[0]/10000-1]+[b/a-1 for a,b in zip(daily_nav,daily_nav[1:])]
        vol=statistics.stdev(returns)*math.sqrt(365);metrics=summary['daily_metrics'];peak=10000.;dd=0.
        for nav in daily_nav:peak=max(peak,nav);dd=max(dd,(peak-nav)/peak)
        ratio_metrics=dict(total_return=daily_nav[-1]/10000-1,annual_return=(daily_nav[-1]/10000)**(365/122)-1,
            annual_volatility=vol,sharpe=statistics.mean(returns)*365/vol if vol>0 else 0.,max_drawdown=dd)
        for field,value in ratio_metrics.items():close(metrics[field],number(value),RATIO_TOL)
        for field,value in [('initial_nav',CAPITAL),('final_nav',wallet.cash),('fees',wallet.fees),
                            ('execution_costs',wallet.spread+wallet.slippage)]:close(metrics[field],value)
        close(metrics['turnover'],wallet.turnover,RATIO_TOL)
        need(metrics['days']==122 and summary['capital_net_APR']==actual['capital_net_APR']=='NOT_EVALUABLE'
             and summary['funding_unit_certified'] is actual['funding_unit_certified'] is False
             and actual['native_Bybit_prices_or_filters'] is False and actual['real_liquidation_MMR_or_ADL_modeled'] is False,
             'Conditional accounting must not become native/candidate qualification')
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Bound small input changed during audit:'+path)
        for row in actual['output_bindings']:need(sha(row['path'])==row['sha256'],'Physical output changed during audit')
        for row in inputs:need(sha(row['parquet_path'])==row['parquet_sha256'],'Original input bytes changed during audit')
        need(time.monotonic()-started<=600 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=512000000,'Independent resource budget exceeded')
        report.update(status='PASS_CONDITIONAL_CARRY_DECIMAL_PROXY_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR',
            actual_report_path=bound['actual_report_path'],actual_report_sha256=sha(ROOT/bound['actual_report_path']),
            financial_scope='CONDITIONAL_FRACTION_AND_CLOSE_PROXY_ACCOUNT_MATH_ONLY_NO_NATIVE_OR_LONG_TERM_APR',
            completed_source_files_verified=32,completed_fills_verified=8,completed_original_funding_events_verified=732,
            owned_events=owned,excluded_events=732-owned,completed_days_verified=122,completed_months_verified=4,
            financial_summary={k:float(v) for k,v in expected.items()},months=months,
            first_risk_signal=obs.first_breach,exit_us=exit_time,permanent_cash_after_exit=True,
            terminal_bridge_error_USDT=str(bridge-wallet.cash),maximum_cash_error_USDT=float(MAX_USDT_ERROR),
            maximum_ratio_error=float(MAX_RATIO_ERROR),minute_max_drawdown=float(minute_dd),all_observation_max_drawdown=float(obs.max_dd),
            limitations=['Uncertified fractions, strict event ownership and past mark are conditional hypotheses',
                'Binance close proxies plus assumed Bybit fees; no native execution, capacity, MMR, ADL or financing proof',
                'Seen122day descriptive account and annualization, no long-term APR or candidate'])
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write_new(OUT,report)
    print(json.dumps(dict(status=report['status'],output=str(OUT),sha256=sha(OUT))))
if __name__=='__main__':main()
