"""Explain saved continuous wallets by signal state, without a counterfactual replay."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import numpy as np
import polars as pl
from quant import resources
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event

MINUTE = 60_000_000
DAY = 1440*MINUTE
GROUPS = ('BOTH_FLAT', 'OLD_LONG_NEW_FLAT', 'OLD_FLAT_NEW_LONG', 'BOTH_LONG', 'INELIGIBLE')
FIELDS_MONEY = ('gross_USDT', 'fees_USDT', 'execution_USDT', 'funding_USDT', 'net_USDT', 'fill_legs', 'filled_notional_USDT')

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def receipt_path(receipt):
    path = Path(receipt['path']).resolve()
    assert path.is_relative_to(STATE) or path.is_relative_to(ROOT/'reports')
    assert sha(path)==receipt['sha256'], str(path)
    return path

def read(receipt): return json.loads(receipt_path(receipt).read_bytes())
def exact(row, key): return float(Decimal(row.get('decimal_strings', {}).get(key, str(row[key]))))
def stamp(value): return datetime.fromtimestamp(value/1e6, UTC).isoformat()

def assets_ledger(case, symbol, times, trades, funding):
    path = Path(case['artifacts']['minute_nav_inventory.parquet']['path'])
    frame = pl.read_parquet(path, columns=['close_us', symbol+'_quantity', symbol+'_isolated_equity', symbol+'_isolated_balance'])
    assert np.array_equal(frame['close_us'].to_numpy(), times)
    q = frame[symbol+'_quantity'].to_numpy()
    unrealized = frame[symbol+'_isolated_equity'].to_numpy()-frame[symbol+'_isolated_balance'].to_numpy()
    assert np.isfinite(q).all() and np.isfinite(unrealized).all() and (q>=0).all()
    legs = [r for r in trades if r['symbol']==symbol]
    events = [r for r in funding if r['symbol']==symbol]
    def bins(rows, key):
        indices = np.searchsorted(times, np.array([r['event_us'] for r in rows], dtype=np.int64), side='left')
        assert all(times[0]-MINUTE <= r['event_us'] <= times[-1] for r in rows)
        assert (indices < len(times)).all()
        weights = [1. if key=='count' else exact(r, 'quantity')*exact(r, 'fill_price')
                   if key=='notional' else exact(r, key) for r in rows]
        return np.bincount(indices, weights=weights, minlength=len(times))
    realized = bins(legs, 'realized_PnL')
    fee, execution = bins(legs, 'fee_USDT_mid'), bins(legs, 'execution_cost')
    fund = bins(events, 'signed_funding_USDT')
    gross = np.diff(np.r_[0., unrealized])+realized+execution
    values = np.vstack((gross, fee, execution, fund, gross-fee-execution+fund,
                        bins(legs,'count'), bins(legs,'notional')))
    return values, q, legs

def totals(values, selector):
    out = dict(zip(FIELDS_MONEY, values[:, selector].sum(axis=1).tolist(), strict=True))
    assert abs(out['net_USDT']-(out['gross_USDT']-out['fees_USDT']-out['execution_USDT']+out['funding_USDT'])) < 1e-7
    return out

def paired(left, right, selector):
    a, b = totals(left, selector), totals(right, selector)
    return dict(baseline=a, challenger=b, increment={key:b[key]-a[key] for key in FIELDS_MONEY})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.protocol.resolve().is_relative_to(ROOT/'protocols')
    assert args.output.resolve().is_relative_to(ROOT/'reports') and not args.output.exists()
    p = json.loads(args.protocol.read_bytes())
    assert p['git_parent']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert p['full_capital_USDT']==10000 and p['classification']==list(GROUPS)
    for name, digest in p['source_hashes'].items(): assert sha(ROOT/name)==digest, name
    began = time.monotonic(); before = resources.status(); peak = before['ram_current_bytes']
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=p['experiment_id'],git_commit=p['git_parent'],data_manifest_hash='EXACT_SAVED_WALLETS_TARGETS_FILLS_FUNDING',
        protocol_hash=sha(args.protocol),model_family='NONE',fits=0,all_folds='SEEN_CONTINUOUS303_POST_SELECTION',
        reason_for_next_experiment=p['question'],result_influenced_later_choice='NONE_BEFORE_RUN')
    append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=p['experiment_id']+':START',
        event_type='OPERATIONAL_RESEARCH_START',success_failure='START_SAVED_EXIT_WAIT_MECHANISM'))
    result = dict(status='FAILED_SAVED_EXIT_WAIT_MECHANISM', task_id=os.environ['COIN_TASK_ID'], protocol_sha256=sha(args.protocol),
        cases=[], market_replays=0, models_fit=0, HPO=0, candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE',
        causal_counterfactual=False, actual_risk_matched=False, funding_unit_certified=False, native_venue_certified=False)
    try:
        old, new = read(p['baseline_report']), read(p['challenger_report'])
        assert read(p['accepted_pair_diagnostic'])['status']=='COMPLETE_EXIT10_SAVED_PAIRED_DIAGNOSTIC_NOT_APR'
        times = np.arange(p['start_us']+MINUTE,p['end_us']+1,MINUTE,dtype=np.int64)
        decisions = np.arange(p['start_us'],p['end_us'],DAY,dtype=np.int64)
        assert len(times)==436320 and len(decisions)==303 and len(old['cases'])==len(new['cases'])==4
        month_ids = np.array([datetime.fromtimestamp(t/1e6,UTC).strftime('%Y-%m') for t in decisions])
        for current in new['cases']:
            control = next(c for c in old['cases'] if c['id']==current['id'])
            assert control['symbols']==current['symbols'] and control['cost_id']==current['cost_id'] and control['unit_id']==current['unit_id']
            loaded = []
            for c in (control,current):
                assert c['summary']['terminal_cash_realized'] and c['summary']['completed_minutes']==len(times)
                for key in ('minute_nav_inventory.parquet','targets.parquet','trades.json','funding.json'):
                    receipt_path(c['artifacts'][key])
                loaded.append((pl.read_parquet(c['artifacts']['targets.parquet']['path']),
                    read(c['artifacts']['trades.json']),read(c['artifacts']['funding.json'])))
                assert len({(r['fill_id'],r['leg']) for r in loaded[-1][1]})==len(loaded[-1][1])
                assert len({(r['symbol'],r['event_us']) for r in loaded[-1][2]})==len(loaded[-1][2])
            record = dict(case_id=current['id'], symbols=current['symbols'], assets=[], episodes=[], months={}, state_totals={},
                decomposition='DELTA_UNREALIZED_PLUS_REALIZED_FILL_PNL; GROSS_ADDS_EXECUTION; NET_SUBTRACTS_FEE_EXECUTION_ADDS_FUND',
                classification_scope='LATEST_RAW_SIGNAL_AT_MINUTE_OPEN_NOT_ACTUAL_INVENTORY_NOT_FILL_CAUSE',
                event_bucket='FIRST_SAVED_MINUTE_CLOSE_GREATER_OR_EQUAL_EVENT_INCLUDES_SAME_BOUNDARY_FUNDING',
                source_artifacts=[{k:c['artifacts'][k] for k in ('minute_nav_inventory.parquet','targets.parquet','trades.json','funding.json')} for c in (control,current)])
            account_arrays = [np.zeros((7,len(times))),np.zeros((7,len(times)))]
            for symbol in current['symbols']:
                targets = [data[0].filter(pl.col('symbol')==symbol).sort('available_us') for data in loaded]
                assert all(np.array_equal(t['available_us'].to_numpy(),decisions) for t in targets)
                assert targets[0]['eligibility_reason'].equals(targets[1]['eligibility_reason'])
                raw = [t['raw_signed_target'].to_numpy() for t in targets]
                assert all(np.isfinite(x).all() and (x>=0).all() for x in raw)
                eligible = targets[0]['eligibility_reason'].to_numpy()=='ELIGIBLE'
                oldlong, newlong = raw[0]>0, raw[1]>0
                daily_groups = oldlong.astype(np.int8)+2*newlong.astype(np.int8)
                daily_groups[~eligible] = 4
                ledgers = [assets_ledger(c,symbol,times,data[1],data[2]) for c,data in zip((control,current),loaded,strict=True)]
                a,b = [x[0] for x in ledgers]
                for i,values in enumerate((a,b)): account_arrays[i] += values
                da,db = [values.reshape(7,303,1440).sum(axis=2) for values in (a,b)]
                groups = {label:paired(da,db,daily_groups==i) for i,label in enumerate(GROUPS)}
                months = {str(month):paired(da,db,month_ids==month)['increment'] for month in dict.fromkeys(month_ids)}
                record['assets'].append(dict(symbol=symbol,total=paired(a,b,slice(None)),signal_state_groups=groups,monthly_increments=months))
                for month in dict.fromkeys(month_ids):
                    states = record.setdefault('monthly_state_increments',{}).setdefault(str(month),{})
                    for i,label in enumerate(GROUPS):
                        value = paired(da,db,(month_ids==month)&(daily_groups==i))['increment']
                        aggregate = states.setdefault(label,{key:0. for key in FIELDS_MONEY})
                        for key in FIELDS_MONEY: aggregate[key] += value[key]
                # Enumerate every contiguous OLD_LONG_NEW_FLAT raw-state episode.
                starts = np.flatnonzero((daily_groups==1)&np.r_[True,daily_groups[:-1]!=1])
                for start in starts:
                    endings = np.flatnonzero(daily_groups[start:]!=1)
                    end = int(start+endings[0]) if len(endings) else len(decisions)
                    observed_exit = start>0 and daily_groups[start-1]==3 and newlong[start-1] and not newlong[start]
                    signal = int(decisions[start]); first = int(start*1440); stop = int(end*1440)
                    reentries = np.flatnonzero(newlong[start+1:])+start+1
                    next_signal = int(decisions[reentries[0]]) if len(reentries) else None
                    sells = [r for r in ledgers[1][2] if r['signal_us']==signal and exact(r,'position_delta')<0]
                    opens = [r for r in ledgers[1][2] if r['event_us']>=signal and r['leg']=='OPEN' and exact(r,'quantity_before')==0]
                    flat = np.flatnonzero(ledgers[1][1][first:stop]==0)
                    record['episodes'].append(dict(symbol=symbol, signal_exit_us=signal, start=stamp(signal),
                        end_exclusive=stamp(p['start_us']+end*DAY), classification_days=end-int(start),
                        exit_transition=('OBSERVED_BOTH_LONG_TO_OLD_LONG_NEW_FLAT' if observed_exit else 'UNKNOWN_OR_LEFT_CENSORED'),
                        end_signal_state=GROUPS[daily_groups[end]] if end<len(decisions) else 'RIGHT_CENSORED_EVALUATION_END',
                        next_new_long_signal_us=next_signal,
                        days_to_next_new_long_signal=(next_signal-signal)//DAY if next_signal is not None else None,
                        next_new_long_signal_censored=next_signal is None,
                        next_actual_flat_to_open_us=min((r['event_us'] for r in opens),default=None),
                        exit_signal_sell_legs=len(sells), exit_signal_sell_quantity=sum(exact(r,'quantity') for r in sells),
                        actual_new_quantity_before_signal=float(ledgers[1][1][first-1]) if first else 0.,
                        actual_exit_status=('ALREADY_FLAT_BEFORE_SIGNAL' if not first or ledgers[1][1][first-1]==0
                                            else 'MATCHED_SIGNAL_REDUCTION_LEGS' if sells else 'NO_MATCHED_SIGNAL_SELL_UNKNOWN'),
                        first_observed_new_flat_close_us=int(times[first+flat[0]]) if len(flat) else None,
                        old_positive_inventory_minutes=int((ledgers[0][1][first:stop]>0).sum()),
                        new_positive_inventory_minutes=int((ledgers[1][1][first:stop]>0).sum()),
                        paired_asset_money=paired(a,b,slice(first,stop)),
                        scope='TWO_ACTUAL_WALLET_ASSET_FLOWS_NOT_CANCEL_EXIT_COUNTERFACTUAL_OR_ORDER_REASON_PROFIT'))
                for label, value in groups.items():
                    aggregate = record['state_totals'].setdefault(label,{key:0. for key in FIELDS_MONEY})
                    for key in FIELDS_MONEY: aggregate[key] += value['increment'][key]
                peak = max(peak,resources.status()['ram_current_bytes'])
                assert time.monotonic()-began<=p['budget']['wall_seconds']
                assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=p['budget']['RSS_bytes']
            bridge_errors = []
            for c,values in zip((control,current),account_arrays,strict=True):
                checks = pl.read_parquet(c['artifacts']['minute_nav_inventory.parquet']['path'],
                    columns=['nav','cumulative_fees','cumulative_execution_costs','cumulative_funding','cumulative_turnover'])
                nav = checks['nav'].to_numpy()
                error = float(np.max(np.abs(values[4]-np.diff(np.r_[10000.,nav]))))
                assert error<1e-7
                event_errors = {column:float(np.max(np.abs(values[index]-np.diff(np.r_[0.,checks[column].to_numpy()]))))
                    for column,index in (('cumulative_fees',1),('cumulative_execution_costs',2),('cumulative_funding',3),('cumulative_turnover',6))}
                assert all(value<1e-7 for value in event_errors.values()),event_errors
                record.setdefault('minute_event_bridge_max_errors_USDT',[]).append(event_errors)
                summary = c['summary']; measured = totals(values,slice(None))
                for key,saved in dict(gross_USDT='gross_PnL_same_quantities',fees_USDT='fees_USDT',execution_USDT='execution_cost_USDT',funding_USDT='funding_USDT',net_USDT='net_PnL').items():
                    assert abs(measured[key]-summary[saved])<1e-7,(key,measured[key],summary[saved])
                bridge_errors.append(error)
            record['minute_NAV_bridge_max_errors_USDT'] = bridge_errors
            record['total'] = paired(*account_arrays,slice(None))
            for month in dict.fromkeys(month_ids): record['months'][str(month)] = paired(*account_arrays,np.repeat(month_ids==month,1440))
            for month in record['months']:
                for key in FIELDS_MONEY:
                    assert abs(sum(g[key] for g in record['monthly_state_increments'][month].values())-record['months'][month]['increment'][key])<1e-7
            for key in FIELDS_MONEY:
                assert abs(sum(g[key] for g in record['state_totals'].values())-record['total']['increment'][key])<1e-7
            result['cases'].append(record)
        result['status']='COMPLETE_SAVED_EXIT_WAIT_MECHANISM_NOT_CAUSAL_ALPHA'
    except Exception as error:
        result.update(error_type=type(error).__name__,reason=str(error)); raise
    finally:
        result.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-began,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,shared_RAM_sampled_peak_bytes=peak,
            resources_before=before,resources_after=resources.status())
        encoded = json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        assert len(encoded.encode())<=p['budget']['output_bytes']
        with args.output.open('x') as writer: writer.write(encoded)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=p['experiment_id']+':RESULT',
            event_type='OPERATIONAL_RESEARCH_RESULT',success_failure=result['status'],artifact_path=args.output.relative_to(ROOT).as_posix(),artifact_sha256=sha(args.output)))
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),episodes=[len(c['episodes']) for c in result['cases']])))

if __name__=='__main__': main()
