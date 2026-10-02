"""Independent pair-trim audit entry; preparation until actual closed0.
Reuse accepted Decimal/source/valuation primitives; no account simulator,
old-control array replay, rawZIP/CRC QA, API, model or parameter search.
"""
import hashlib, importlib.util, json, math, os, resource, statistics, sys, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
WORK=STATE/'test-conditional-carry-pair-trim-independent-audit-20261003-v1'
OUT=ROOT/'reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json'
SYMBOLS=('BTCUSDT','ETHUSDT');MONTHS=('2025-08','2025-09','2025-10','2025-11')
START=1754006400000000;END=1764547200000000;STEP=60000000;COUNT=175680

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def imported(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def main():
    bound=load(WORK/'ACTUAL_BINDING.json')
    delta=imported('independent_pair_delta',WORK/'audit_delta.py')
    core=delta.load_primitives(bound['core_sha256'])
    need,close,number,D,Z=(core.need,core.close,core.number,core.D,core.ZERO)
    need(sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and os.environ.get('COIN_TASK_ID')
         and not OUT.exists() and sha(__file__)==bound['checker_sha256']
         and sha(WORK/'audit_delta.py')==bound['delta_sha256'],'New bounded audit/code binding required')
    report=dict(status='FAIL_CONDITIONAL_CARRY_PAIR_TRIM_DECIMAL_INDEPENDENT_AUDIT',
        binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),delta_sha256=sha(WORK/'audit_delta.py'),
            ACTUAL_BINDING_sha256=sha(WORK/'ACTUAL_BINDING.json')),
        independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),
        reused_independent_core_sha256=bound['core_sha256'],old_control_math_replayed=False,
        cash_absolute_tolerance_USDT=str(core.USDT_TOL),ratio_absolute_tolerance=str(core.RATIO_TOL),
        completed_minutes_verified=0,actual_HTTP_requests=0,orders_sent=0,models_fit=0,
        raw_ZIP_or_CRC_read=False,old_QA_or_green_tests_repeated=False,simulate_account_called=False,
        candidate_status='NO_QUALIFIED_CANDIDATE',funding_unit_certified=False,native_Bybit_settlement_proven=False)
    started=time.monotonic()
    try:
        import pyarrow.parquet as pq
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Small source changed:'+path)
        spec=load(ROOT/bound['protocol_path']);actual=load(ROOT/bound['actual_report_path']);summary=actual['summary']
        need(spec['contract_id']=='CONDITIONAL_CARRY_PAIR_TRIM_ACCOUNT_V1' and spec['symbols']==list(SYMBOLS)
             and spec['source_calendar']==list(MONTHS) and spec['period_start']=='2025-08-01'
             and spec['period_end_exclusive']=='2025-12-01','Fixed entire122day source calendar')
        need(D(str(spec['independent_cash_absolute_tolerance_USDT']))==core.USDT_TOL
             and D(str(spec['independent_ratio_absolute_tolerance']))==core.RATIO_TOL,'Preregistered tolerances changed')
        need(actual['status']=='COMPLETE_CONDITIONAL_CARRY_PAIR_TRIM_PROXY_UNIT_UNCERTIFIED_NOT_NATIVE_OR_LONG_TERM_APR'
             and actual['source_bytes_unchanged'] is True and actual['binding']['task_id']==bound['actual_task_id'],
             'New actual account must be complete/unchanged')
        need(actual['binding']==load(Path(actual['run_dir'])/'RUN_BINDING.json')
             and actual['binding']['protocol_sha256']==sha(ROOT/bound['protocol_path'])
             and actual['binding']['rules']==spec['rules'],'Exact actual source/rules/run binding')
        report['verified_source_hashes']=actual['binding']['source_hashes']
        for path,digest in spec['frozen_sources'].items():need(report['verified_source_hashes'].get(path)==digest,'Frozen dependency missing')
        for path,digest in report['verified_source_hashes'].items():need(sha(ROOT/path)==digest,'Frozen dependency changed:'+path)
        fixed=dict(initial_capital_USDT=10000,nominal_per_asset_per_leg_at_signal_USDT=1250,
            isolated_initial_margin_per_asset_USDT=1250,total_gross_stop_at_or_above=.6,asset_two_leg_gross_stop_at_or_above=.3,
            isolated_equity_stop_at_or_below_initial_margin_fraction=.5,pair_trim_target_two_leg_gross=.25,
            spot_fee_bps_per_side=10,perp_fee_bps_per_side=5.5,each_leg_roundtrip_spread_bps=8,slippage_bps_per_side=4)
        need(all(spec['rules'][k]==v for k,v in fixed.items()) and spec['rules']['monthly_reset'] is False
             and spec['rules']['reentry'] is False,'Same capital/cost/caps and reduce-only')
        reader=imported('accepted_source_clock_reader',bound['price_reader_path'])
        need(sha(bound['price_reader_path'])==bound['price_reader_sha256'],'Accepted reader binding')
        report['actual_task']=reader.task(bound['actual_task_id'])
        smoke=load(ROOT/spec['required_smoke_receipt']);report['smoke_actual_task']=reader.task(smoke['binding']['task_id'])
        need(smoke['status']=='PASS_CONDITIONAL_CARRY_PAIR_TRIM_SYNTHETIC_NOT_MARKET_RESULT'
             and smoke['test_exit_code']==0 and smoke['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0)
             and smoke['source_bytes_unchanged'] is True and smoke['price_arrays_read'] is False
             and smoke['funding_arrays_read'] is False and smoke['binding']['source_hashes']==actual['binding']['source_hashes']
             and actual['accepted_smoke_sha256']==sha(ROOT/spec['required_smoke_receipt']),'Closed new synthetic evidence')
        fundspec=load(ROOT/spec['funding_contract_path']);probe=load(ROOT/fundspec['unit_probe']['path'])
        failed_path=STATE/'task-progress'/('task-'+probe['binding']['task_id']+'.json');failed=load(failed_path)
        unit=actual['unit_interpretation']
        need(failed['id']==probe['binding']['task_id'] and failed['status']=='failed' and failed['exit_code']==1
             and probe['unit_evidence']['matched_records']==0 and unit['raw_rate_unit']=='UNCONFIRMED'
             and unit['assumed_funding_rate_unit']=='FRACTION' and unit['bp_multiplier']==10000
             and unit['conditional_fraction_assumption'] is True and unit['full_732_event_unit_certified'] is False
             and unit['sampled_API_unit_certified'] is False,'Uncertified unit/failed1 preserved')
        report['unit_failure_task']=dict(id=failed['id'],status='failed',exit_code=1,pid=failed['pid'],start_ticks=failed['start_ticks'],sha256=sha(failed_path))
        control=load(ROOT/spec['fixed_control_path'])
        need(sha(ROOT/spec['fixed_control_path'])==spec['fixed_control_sha256'] and spec['control_replayed'] is False
             and control['status']=='COMPLETE_CONDITIONAL_CARRY_PROXY_ACCOUNT_UNIT_UNCERTIFIED_NOT_NATIVE_OR_LONG_TERM_APR'
             and control['source_bytes_unchanged'] is True,'Frozen all-flat reference summary only')
        report['control_report_sha256']=sha(ROOT/spec['fixed_control_path'])
        frames={}
        need({r['kind'] for r in actual['output_bindings']}=={'minute_nav','fill_ledger','funding_ledger','daily_nav'},'Four artifacts')
        for row in actual['output_bindings']:
            path=Path(row['path']);need(path.parent==Path(actual['run_dir']) and sha(path)==row['sha256'],'Physical output changed')
            file=pq.ParquetFile(path);need(file.metadata.num_rows==row['rows'],'Artifact row count');frames[row['kind']]=file
        fills=frames['fill_ledger'].read(use_threads=False).to_pylist();fundrows=frames['funding_ledger'].read(use_threads=False).to_pylist()
        daily=frames['daily_nav'].read(use_threads=False).to_pylist()
        prices,events,inputs=core.original_inputs(spec,actual,reader)
        need(len(fundrows)==732 and len(daily)==122 and [(r['symbol'],r['event_us'],r['raw_rate']) for r in fundrows]
             ==[(e['symbol'],e['event_us'],e['rate']) for e in events],'Original event identities/rates/order')
        wallet=delta.wallet_class(core)();obs=core.Observations();held=False;entered=False;pending={};full_pending=None
        entry=START+2*STEP+1;exit_time=END+1;exit_reason='PROTOCOL_TERMINAL';stop_signal=None
        planned={s:core.RESERVE/number(prices[s]['spot'][0]) for s in SYMBOLS}
        max_gross=Z;max_assets=dict.fromkeys(SYMBOLS,Z);min_equities=dict.fromkeys(SYMBOLS,core.RESERVE)
        minute_peak=core.CAPITAL;minute_dd=Z;fill_cursor=event_cursor=owned=0;breaches=[];reductions=[]
        day_ends={};month_ends={};asset_funding=dict.fromkeys(SYMBOLS,Z);asset_fees={s:dict(SPOT=Z,PERP=Z) for s in SYMBOLS}
        entry_notionals={};price_gross=Z
        def values(index):return {s:(prices[s]['spot'][index],prices[s]['mark'][index]) if index>=0 else (0.,0.) for s in SYMBOLS}
        def observe(index):
            nonlocal max_gross
            result=wallet.valuation(values(index));nav,gross,assets,equities=result
            obs.record(0,*result,False,'OBSERVATION_ONLY');max_gross=max(max_gross,gross)
            for s in SYMBOLS:
                max_assets[s]=max(max_assets[s],assets[s])
                if wallet.p[s]['short']:min_equities[s]=min(min_equities[s],equities[s])
            return result
        def risk(index,timestamp,cause):
            nonlocal full_pending,exit_time,exit_reason,stop_signal
            if not held:return
            nav,gross,assets,equities=observe(index)
            margin=[s for s in SYMBOLS if equities[s]<=core.RESERVE/D(2)]
            breached=[s for s in SYMBOLS if assets[s]>=D('.3')]
            reasons=(['TOTAL_GROSS'] if gross>=D('.6') else [])+['ASSET_GROSS_'+s for s in breached]+['ISOLATED_EQUITY_'+s for s in margin]
            if not reasons:return
            breaches.append(dict(signal_us=timestamp,cause=cause,reasons=reasons,nav=nav,total_gross=gross,asset_two_leg_gross=assets,isolated_equity=equities))
            if full_pending is not None:return
            following=(timestamp-(START+STEP))//STEP+1
            if following>=COUNT:return
            if margin:
                full_pending=following;stop_signal=timestamp;exit_time=START+(following+1)*STEP+1
                exit_reason='SELF_DEFINED_ISOLATED_MARGIN_ALL_FLAT';return
            if gross>=D('.6') and not breached:breached=[max(SYMBOLS,key=lambda s:assets[s])]
            for s in breached:
                if s in pending:continue
                q=wallet.p[s]['short'];keep=delta.frozen_keep(core,nav,prices[s]['spot'][index],prices[s]['mark'][index],q)
                need(q>keep>0,'Positive reduce-only cap reduction')
                pending[s]=dict(signal_us=timestamp,signal_price_close_us=START+(index+1)*STEP,
                    signal_NAV=nav,signal_spot_close=number(prices[s]['spot'][index]),signal_mark_close=number(prices[s]['mark'][index]),
                    signal_two_leg_gross=assets[s],fill_index=following,signal_held_quantity=q,keep_quantity=keep,
                    reduce_quantity=q-keep,target_two_leg_gross=D('.25'))
        def action(index,s,product,side,quantity,signal,reason,partial=False):
            nonlocal fill_cursor,price_gross
            need(fill_cursor<len(fills),'Scheduled fill missing')
            row=fills[fill_cursor];closed=START+(index+1)*STEP;stamp=closed+1
            need((row['symbol'],row['product'],row['side'])==(s,product,side) and row['timestamp_us']==stamp
                 and row['price_close_us']==closed and row['signal_us']==signal and row['reason']==reason,'Action/order/next-close timing')
            close(row['gross_quantity'],quantity,core.QTY_TOL)
            mid=prices[s]['spot' if product=='SPOT' else 'mark'][index]
            close(row['nav_before'],observe(index)[0]);prior_fee=wallet.fees
            if partial:wallet.apply_partial_close(row,mid,quantity)
            else:
                wallet.apply_fill(row,mid)
                for key in ('partial_realized_free_cash_credit','partial_realized_free_cash_debit','partial_realized_isolated_balance_debit'):close(row[key],Z)
                need(row['partial_realized_fields_scope']=='PARTIAL_CLOSE_ONLY','Explicit partial-only scope')
            asset_fees[s][product]+=wallet.fees-prior_fee
            if reason in ('FIXED_INITIAL_HEDGE','MATCH_ACTUAL_NET_BASE'):entry_notionals[s,product]=quantity*number(mid)
            else:
                price_gross+=quantity*((number(mid)-number(prices[s]['spot'][1])) if product=='SPOT'
                    else (number(prices[s]['mark'][1])-number(mid)))
            close(row['nav_after'],observe(index)[0]);close(row['prefix_peak_nav'],obs.peak)
            close(row['prefix_max_drawdown'],obs.max_dd,core.RATIO_TOL);fill_cursor+=1
            return row
        for batch in frames['minute_nav'].iter_batches(batch_size=4096,use_threads=False):
            for row in batch.to_pylist():
                index=report['completed_minutes_verified'];closed=START+(index+1)*STEP;stamp=closed+1
                need(row['close_us']==closed and row['valuation_us']==stamp,'Exact175680 minute calendar')
                while event_cursor<len(events) and events[event_cursor]['event_us']<=stamp:
                    event=events[event_cursor];saved=fundrows[event_cursor];t=event['event_us'];s=event['symbol'];previous=(t-(START+STEP)-1)//STEP
                    before=observe(previous)[0];current=wallet.p[s]['short'];mark=prices[s]['mark'][previous] if previous>=0 else None
                    qual=held and entry<t<exit_time;scheduled=pending.get(s)
                    tie=(dict(execution_us=START+(scheduled['fill_index']+1)*STEP+1,frozen_keep=scheduled['keep_quantity']) if scheduled else None)
                    eligible=delta.eligible_quantity(core,t,entry,exit_time,current,tie) if held else Z
                    closing=current if t==exit_time else (current-eligible if qual else Z)
                    need(saved['mark_close_us']==(START+(previous+1)*STEP if previous>=0 else None)
                         and saved['mark_proxy']==mark and (previous<0 or saved['mark_close_us']<t),'Strictly past source mark/clock')
                    close(saved['held_short_quantity'],current,core.QTY_TOL);close(saved['qualified_short_quantity'],eligible,core.QTY_TOL)
                    close(saved['closing_at_same_stamp_excluded_quantity'],closing,core.QTY_TOL)
                    need(saved['ownership_qualified'] is qual and saved['ownership_rule']=='STRICT_ENTRY_PER_CHUNK_EXIT_UNCERTIFIED','Chunk ownership')
                    close(saved['nav_before'],before);prior_fund=wallet.funding
                    wallet.apply_owned_funding_slice(saved,event['rate'],mark,eligible);asset_funding[s]+=wallet.funding-prior_fund
                    close(saved['nav_after'],observe(previous)[0]);close(saved['prefix_peak_nav'],obs.peak)
                    close(saved['prefix_max_drawdown'],obs.max_dd,core.RATIO_TOL)
                    need(saved['reason']==('CONDITIONAL_SIGNED_FUNDING' if qual else 'OUTSIDE_STRICT_HOLD_INTERVAL')
                         and saved['distance_from_entry_us']==abs(t-entry) and saved['distance_from_exit_us']==abs(t-summary['exit_us']),
                         'Funding full-boundary witnesses/reason')
                    owned+=qual;risk(previous,t,'FUNDING_EVENT_AFTER_CASH');event_cursor+=1
                observe(index);risk(index,stamp,'CLOSED_MINUTE_BEFORE_SCHEDULED_FILLS')
                if index==1 and not entered:
                    for s in SYMBOLS:
                        action(index,s,'SPOT','buy',planned[s]/(1-core.SPOT_RATE),START+STEP,'FIXED_INITIAL_HEDGE')
                        action(index,s,'PERP','sell',planned[s],START+STEP,'MATCH_ACTUAL_NET_BASE')
                    held=entered=True
                if held and (index==full_pending or index==COUNT-1):
                    for s in SYMBOLS:
                        q=wallet.p[s]['spot'];need(abs(q-wallet.p[s]['short'])<=core.QTY_TOL,'Matched full exit')
                        action(index,s,'SPOT','sell',q,stop_signal if stop_signal is not None else END,exit_reason)
                        action(index,s,'PERP','buy',q,stop_signal if stop_signal is not None else END,exit_reason)
                    held=False;pending.clear()
                elif held:
                    for s in SYMBOLS:
                        schedule=pending.get(s)
                        if schedule is None or schedule['fill_index']!=index:continue
                        pending.pop(s);q=wallet.p[s]['spot'];amount=schedule['reduce_quantity']
                        need(abs(q-wallet.p[s]['short'])<=core.QTY_TOL and amount<q,'Matched surviving reduction')
                        reserve=wallet.p[s]['margin'];before=observe(index)[0]
                        action(index,s,'SPOT','sell',amount,schedule['signal_us'],'MATCHED_PAIR_CAP_TRIM',True)
                        leg=action(index,s,'PERP','buy',amount,schedule['signal_us'],'MATCHED_PAIR_CAP_TRIM',True)
                        after,gross,assets,equities=observe(index)
                        need(abs(wallet.p[s]['spot']-schedule['keep_quantity'])<=core.QTY_TOL
                             and abs(wallet.p[s]['spot']-wallet.p[s]['short'])<=core.QTY_TOL,'Signal-frozen keep cannot resize at fill')
                        need(leg['partial_close'] is True,'Partial close witness')
                        for key,value in [('isolated_balance_released_USDT',Z),('isolated_balance_before',reserve),
                            ('isolated_balance_after',wallet.p[s]['margin']),('remaining_spot_quantity',wallet.p[s]['spot']),
                            ('remaining_short_quantity',wallet.p[s]['short'])]:close(leg[key],value,core.QTY_TOL if 'quantity' in key else core.USDT_TOL)
                        reductions.append(dict(schedule,symbol=s,fill_us=stamp,fill_price_close_us=closed,spot_mid=number(prices[s]['spot'][index]),
                            mark_mid=number(prices[s]['mark'][index]),remaining_quantity=wallet.p[s]['spot'],isolated_balance_before=reserve,
                            isolated_balance_after=wallet.p[s]['margin'],isolated_equity_after=equities[s],NAV_before=before,NAV_after=after,
                            asset_two_leg_gross_after=assets[s],total_gross_after=gross,target_is_signal_not_future_fill=True))
                nav,gross,assets,equities=observe(index);minute_peak=max(minute_peak,nav);minute_dd=max(minute_dd,(minute_peak-nav)/minute_peak)
                risk(index,stamp,'CLOSED_MINUTE_AFTER_FILLS')
                for key,value in [('nav',nav),('free_cash',wallet.cash),('cumulative_fees',wallet.fees),('cumulative_spread',wallet.spread),
                    ('cumulative_slippage',wallet.slippage),('cumulative_funding',wallet.funding),('all_observation_peak_nav',obs.peak)]:close(row[key],value)
                for key,value in [('total_gross',gross),('cumulative_turnover',wallet.turnover),('all_observation_max_drawdown',obs.max_dd)]:close(row[key],value,core.RATIO_TOL)
                for s in SYMBOLS:
                    close(row[s+'_gross'],assets[s],core.RATIO_TOL);close(row[s+'_isolated_equity'],equities[s])
                    close(row[s+'_spot_and_short_q'],wallet.p[s]['spot'],core.QTY_TOL)
                    need(abs(wallet.p[s]['spot']-wallet.p[s]['short'])<=core.QTY_TOL,'Matched inventory each minute')
                date=datetime.fromtimestamp((closed-1)//1000000,timezone.utc).date();need(row['date']==date,'UTC daily attribution')
                totals=dict(nav=nav,fees=wallet.fees,spread=wallet.spread,slippage=wallet.slippage,funding=wallet.funding,turnover=wallet.turnover)
                day_ends[date]=totals;month_ends[date.strftime('%Y-%m')]=totals;report['completed_minutes_verified']+=1
                if index%43200==0:print(json.dumps(dict(verified_minutes=index+1,total=COUNT)),flush=True)
        need(report['completed_minutes_verified']==COUNT and event_cursor==732 and fill_cursor==len(fills)==8+2*len(reductions)
             and not held and all(p['spot']==p['short']==p['margin']==0 for p in wallet.p.values()),'Complete single account/terminal flat')
        need(summary['exit_us']==exit_time and summary['stop_signal_us']==stop_signal and summary['exit_reason']==exit_reason,
             'Margin/full priority and terminal timing')
        need(len(summary['risk_breach_witnesses'])==len(breaches),'Every risk observation required')
        for saved,expected in zip(summary['risk_breach_witnesses'],breaches,strict=True):
            need(all(saved[k]==expected[k] for k in ('signal_us','cause','reasons')),'First/pending risk signal differs')
            close(saved['nav'],expected['nav']);close(saved['total_gross'],expected['total_gross'],core.RATIO_TOL)
            for s in SYMBOLS:
                close(saved['asset_two_leg_gross'][s],expected['asset_two_leg_gross'][s],core.RATIO_TOL)
                close(saved['isolated_equity'][s],expected['isolated_equity'][s])
        need(len(summary['pair_reductions'])==len(reductions)==summary['completed_pair_reductions'],'All scheduled reductions')
        for saved,expected in zip(summary['pair_reductions'],reductions,strict=True):
            need(set(saved)==set(expected),'Reduction witness schema')
            for k,v in expected.items():
                if k in ('symbol','signal_us','signal_price_close_us','fill_index','fill_us','fill_price_close_us','target_is_signal_not_future_fill'):
                    need(saved[k]==v,'Reduction date/order/causality differs')
                else:close(saved[k],v,core.QTY_TOL if 'quantity' in k else core.RATIO_TOL if 'gross' in k else core.USDT_TOL)
        previous=dict(nav=core.CAPITAL,fees=Z,spread=Z,slippage=Z,funding=Z,turnover=Z);daily_nav=[]
        for saved,(date,totals) in zip(daily,sorted(day_ends.items()),strict=True):
            need(saved['date']==date,'Every consecutive UTC day')
            expected=dict(nav=totals['nav'],fee_cumulative=totals['fees'],cost_cumulative=totals['spread']+totals['slippage'],
                fees=totals['fees']-previous['fees'],execution_costs=totals['spread']+totals['slippage']-previous['spread']-previous['slippage'])
            for k,v in expected.items():close(saved[k],v)
            close(saved['turnover_cumulative'],totals['turnover'],core.RATIO_TOL)
            close(saved['turnover'],totals['turnover']-previous['turnover'],core.RATIO_TOL)
            daily_nav.append(float(totals['nav']));previous=totals
        previous=dict(nav=core.CAPITAL,fees=Z,spread=Z,slippage=Z,funding=Z);months=[]
        need([r['month'] for r in summary['months']]==list(MONTHS),'All four continuous months')
        for saved,(month,totals) in zip(summary['months'],month_ends.items(),strict=True):
            amounts={k:totals[k]-previous[k] for k in ('fees','spread','slippage','funding')};net=totals['nav']-previous['nav']
            output=dict(start_NAV=previous['nav'],end_NAV=totals['nav'],net_PnL_USDT=net,
                gross_cost_addback_PnL_USDT=net+amounts['fees']+amounts['spread']+amounts['slippage'],fees_USDT=amounts['fees'],
                spread_USDT=amounts['spread'],slippage_USDT=amounts['slippage'],signed_funding_USDT=amounts['funding'])
            need(saved['month']==month and saved['monthly_account_reset'] is False,'No monthly reset/selection')
            for k,v in output.items():close(saved[k],v)
            months.append(dict(month=month,**{k:float(v) for k,v in output.items()}));previous=totals
        costs=wallet.fees+wallet.spread+wallet.slippage;net=wallet.cash-core.CAPITAL;bridge=core.CAPITAL+price_gross+wallet.funding-costs
        need(abs(bridge-wallet.cash)<=core.USDT_TOL,'Partial-realized/final remaining-quantity NAV bridge')
        financial=dict(initial_capital_USDT=core.CAPITAL,final_nav_USDT=wallet.cash,net_PnL_USDT=net,gross_cost_addback_PnL_USDT=net+costs,
            fees_USDT=wallet.fees,assumed_spread_USDT=wallet.spread,assumed_slippage_USDT=wallet.slippage,signed_conditional_funding_USDT=wallet.funding)
        for k,v in financial.items():close(summary[k],v)
        for k,v in [('period_net_return',net/core.CAPITAL),('turnover',wallet.turnover),('minute_max_drawdown',minute_dd),
            ('all_observation_max_drawdown',obs.max_dd),('maximum_total_gross',max_gross)]:close(summary[k],v,core.RATIO_TOL)
        for s in SYMBOLS:
            close(summary['maximum_asset_two_leg_gross'][s],max_assets[s],core.RATIO_TOL);close(summary['minimum_isolated_equity'][s],min_equities[s])
            close(summary['planned_quantity_from_first_signal'][s],planned[s],core.QTY_TOL)
            close(summary['matched_quantity_from_native_received_fill'][s],planned[s],core.QTY_TOL)
        for saved in summary['per_asset']:
            s=saved['symbol'];need(s in SYMBOLS,'Fixed asset summaries')
            for k,v in [('signed_funding_USDT',asset_funding[s]),('spot_fee_USDT',asset_fees[s]['SPOT']),('perp_fee_USDT',asset_fees[s]['PERP']),
                ('actual_entry_spot_mid_notional_USDT',entry_notionals[s,'SPOT']),('actual_entry_perp_mid_notional_USDT',entry_notionals[s,'PERP'])]:close(saved[k],v)
        need([r['symbol'] for r in summary['per_asset']]==list(SYMBOLS) and summary['all_source_events']==732
             and summary['owned_funding_events']==owned and summary['excluded_funding_events']==732-owned
             and summary['fills']==fill_cursor and summary['rows']==COUNT and summary['first_signal_us']==START+STEP
             and summary['entry_us']==entry,'Full counts/first signal/fractional entry')
        nearby=[r for r in fundrows if min(abs(r['event_us']-entry),abs(r['event_us']-exit_time))<=5000000]
        trim_nearby=[dict(event_us=r['event_us'],symbol=r['symbol'],fill_us=t['fill_us'],distance_us=abs(r['event_us']-t['fill_us']))
            for r in fundrows for t in reductions if r['symbol']==t['symbol'] and abs(r['event_us']-t['fill_us'])<=5000000]
        need(summary['near_boundary_event_witnesses']==nearby[:8] and summary['events_within_5s_of_entry_or_exit']==len(nearby)
             and summary['events_within_5s_of_any_pair_reduction']==len({(r['symbol'],r['event_us']) for r in trim_nearby})
             and summary['pair_reduction_funding_boundary_witnesses']==trim_nearby[:8],'Full/partial boundary uncertainty witnesses')
        returns=[daily_nav[0]/10000-1]+[b/a-1 for a,b in zip(daily_nav,daily_nav[1:])];vol=statistics.stdev(returns)*math.sqrt(365)
        peak=10000.;dd=0.
        for nav in daily_nav:peak=max(peak,nav);dd=max(dd,(peak-nav)/peak)
        metrics=summary['daily_metrics'];ratios=dict(total_return=daily_nav[-1]/10000-1,annual_return=(daily_nav[-1]/10000)**(365/122)-1,
            annual_volatility=vol,sharpe=statistics.mean(returns)*365/vol if vol>0 else 0.,max_drawdown=dd,turnover=float(wallet.turnover))
        for k,v in ratios.items():close(metrics[k],number(v),core.RATIO_TOL)
        for k,v in [('initial_nav',core.CAPITAL),('final_nav',wallet.cash),('fees',wallet.fees),('execution_costs',wallet.spread+wallet.slippage)]:close(metrics[k],v)
        close(summary['continuous_monthly_net_reconciliation_error_USDT'],Z)
        need(metrics['days']==122 and summary['permanent_cash_after_exit'] is True and summary['no_extra_capital_or_collateral_topups'] is True
             and summary['paired_signal_quantity_only_reduces'] is True and summary['terminal_spot_quantity']==summary['terminal_short_quantity']==dict.fromkeys(SYMBOLS,0.)
             and summary['terminal_dust_proxy']==0. and summary['real_funding_ownership_within_5s_guaranteed'] is False
             and summary['caps_are_exit_triggers_not_guaranteed_execution_caps'] is True and actual['capital_net_APR']==summary['capital_net_APR']=='NOT_EVALUABLE'
             and summary['funding_unit_certified'] is actual['funding_unit_certified'] is False and actual['native_Bybit_prices_or_filters'] is False
             and actual['real_liquidation_MMR_or_ADL_modeled'] is False and summary['unseen_qualification'] is False,'Conditional scope/no topup/reset/native/APR claim')
        receipt=summary['derivation_receipt']
        need(summary['original_all_flat_source_sha256']==spec['base_account_sha256']==receipt['base_sha256']
             and receipt['adapter_sha256']==spec['frozen_sources']['scripts/investment/conditional_carry_reduce_adapter.py']
             and receipt['expected_exact_anchor_matches']==len(receipt['changes'])==11
             and all(r['matches']==1 for r in receipt['changes']) and receipt['original_all_flat_bytes_preserved'] is True,
             'Frozen original base/adapter source and exact anchored derivation record')
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Small source changed during audit:'+path)
        for r in inputs:need(sha(r['parquet_path'])==r['parquet_sha256'],'Original accepted32 input changed')
        for r in actual['output_bindings']:need(sha(r['path'])==r['sha256'],'Physical output changed during audit')
        need(time.monotonic()-started<=600 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=512000000,'Independent resource budget')
        report.update(status='PASS_CONDITIONAL_CARRY_PAIR_TRIM_DECIMAL_PROXY_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR',
            actual_report_path=bound['actual_report_path'],actual_report_sha256=sha(ROOT/bound['actual_report_path']),
            financial_scope='CONDITIONAL_FRACTION_CLOSE_PROXY_ACCOUNT_ONLY_NO_NATIVE_OR_LONG_TERM_APR',
            completed_source_files_verified=32,completed_original_funding_events_verified=732,completed_fills_verified=fill_cursor,
            completed_days_verified=122,completed_months_verified=4,completed_pair_reductions_verified=len(reductions),owned_events=owned,excluded_events=732-owned,
            financial_summary={k:float(v) for k,v in financial.items()},months=months,first_margin_signal_us=stop_signal,exit_us=exit_time,
            independent_pair_reductions=[{k:float(v) if isinstance(v,D) else v for k,v in r.items()} for r in reductions],
            terminal_bridge_error_USDT=str(bridge-wallet.cash),maximum_cash_error_USDT=float(core.MAX_USDT_ERROR),maximum_ratio_error=float(core.MAX_RATIO_ERROR),
            all_observation_max_drawdown=float(obs.max_dd),minute_max_drawdown=float(minute_dd),
            paired_control_summary=control['summary'],paired_net_PnL_delta_USDT=float(net-number(control['summary']['net_PnL_USDT'])),
            limitations=['Seen fixed window mechanism control; no old control arrays replayed','Uncertified fraction/event ownership/charge mark hypotheses',
                'Binance close proxies/assumed costs/fractional size/no native capacity, MMR, ADL, financing or long-term APR'])
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        core.write_new(OUT,report)
    print(json.dumps(dict(status=report['status'],output=str(OUT),sha256=sha(OUT))))
if __name__=='__main__':main()
