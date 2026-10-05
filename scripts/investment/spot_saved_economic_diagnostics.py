"""Attribute saved Spot inventory/cash economics; no new counterfactual trades."""
import argparse
from collections import defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import time

import polars as pl
from scripts.investment.spot_perpetual_product_comparison import read, sha, write
from quant.paths import STATE


def diagnose(case):
    trades_art=case['artifacts']['trades']; daily_art=case['artifacts']['daily_nav']
    for receipt in (trades_art,daily_art): assert sha(receipt['path'])==receipt['sha256']
    trades=pl.read_parquet(trades_art['path']); daily=pl.read_parquet(daily_art['path'])
    groups=defaultdict(lambda:dict(count=0,notional=0.,fees=0.,execution=0.))
    per_asset=[]; monthly=defaultdict(float)
    for symbol in case['symbols']:
        tape=trades.filter(pl.col('symbol')==symbol)
        q=0.; first=True
        for row in tape.iter_rows(named=True):
            # Only labels that can be reconstructed unambiguously are used.
            reason='UNKNOWN_REBALANCE_OR_SIGNAL_COMPONENT'
            if row.get('target_reason','UNKNOWN')!='UNKNOWN':reason=row['target_reason']
            if first and row['side']=='buy':reason='FIRST_ENTRY';first=False
            terminal_signal=case['config']['end_us']-(case['config']['terminal_exit_minutes']+case['config']['latency_minutes'])*60_000_000
            if row['signal_us']==terminal_signal and row['target_weight']==0:reason='TERMINAL_EXIT'
            key=(symbol,row['side'],reason);g=groups[key]
            g['count']+=1;g['notional']+=row['notional'];g['fees']+=row['fee'];g['execution']+=row['execution_cost']
            q+=row['position_delta']
        cash_delta=float(tape['cash_delta'].sum());fees=float(tape['fee'].sum());execution=float(tape['execution_cost'].sum())
        terminal=q*case['terminal_marks'][symbol]['price'];net=cash_delta+terminal
        assert abs(q-case['summary']['open_positions'][symbol])<1e-10
        per_asset.append(dict(symbol=symbol,net_USDT=net,gross_cost_addback_USDT=net+fees+execution,
            fees_USDT=fees,execution_USDT=execution,terminal_inventory_value_USDT=terminal,
            filled_notional_USDT=float(tape['notional'].sum()),trades=tape.height))
        cash_by_month=defaultdict(float)
        for row in tape.iter_rows(named=True):
            month=datetime.fromtimestamp(row['execution_us']/1e6,UTC).strftime('%Y-%m')
            cash_by_month[month]+=row['cash_delta']
        ends={}
        for row in daily.iter_rows(named=True):
            month=datetime.fromtimestamp((row['day_end_us']-1)/1e6,UTC).strftime('%Y-%m')
            ends[month]=row['quantity_'+symbol]*row['mark_'+symbol]
        previous=0.
        for month,value in ends.items():
            monthly[month]+=cash_by_month[month]+value-previous;previous=value
    net=case['summary']['final_nav']-case['config']['initial_cash']
    assert abs(sum(x['net_USDT'] for x in per_asset)-net)<1e-7
    assert abs(sum(monthly.values())-net)<1e-7
    nav=daily['nav'].to_list();blocks=[];before=case['config']['initial_cash']
    assert len(nav)==303
    for i in range(3):
        end=nav[(i+1)*101-1];blocks.append(dict(block=i+1,days=101,start_NAV=before,end_NAV=end,
            net_change_USDT=end-before,return_on_actual_start_NAV=end/before-1));before=end
    return dict(id=case['id'],net_USDT=net,assets=per_asset,
        trade_groups=[dict(symbol=k[0],side=k[1],reason=k[2],**v) for k,v in sorted(groups.items())],
        monthly_net_contributions_USDT=dict(monthly),continuous_101_day_blocks=blocks,
        reason_scope='Saved explicit target intent if present, plus first/terminal; unlabelled others UNKNOWN. Labels do not causally attribute whole-trade PnL.',
        gross_scope=case['summary'].get('gross_pnl_definition'),independent_accounts_not_combined=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    began=time.monotonic();v=json.loads(a.input.read_bytes());control=read(v['spot_control'])
    assert a.output.resolve().is_relative_to(STATE) and not a.output.exists()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    cases=dict(BLEND=[diagnose(c) for c in v['cases']],HOLD8=[diagnose(c) for c in control['cases']])
    pairs=[]
    for s,h in zip(cases['BLEND'],cases['HOLD8'],strict=True):
        assert s['id']==h['id']
        pairs.append(dict(cost_id=s['id'],monthly_net_deltas_USDT={m:s['monthly_net_contributions_USDT'][m]-h['monthly_net_contributions_USDT'][m]
            for m in s['monthly_net_contributions_USDT']},continuous_block_net_deltas_USDT=[x['net_change_USDT']-y['net_change_USDT']
                for x,y in zip(s['continuous_101_day_blocks'],h['continuous_101_day_blocks'],strict=True)]))
    write(a.output,dict(status='PASS_SAVED_SPOT_ASSET_MONTH_NET_AND_COST_BRIDGES',input_sha256=sha(a.input),
        control=v['spot_control'],cases=cases,pairs=pairs,elapsed_seconds=time.monotonic()-began,
        new_market_replays=0,scope='Descriptive saved-account bridge, not causal reason attribution or independent OOS'))
    print(json.dumps(dict(status='PASS_SAVED_SPOT_ASSET_MONTH_NET_AND_COST_BRIDGES',pairs=pairs)))


if __name__=='__main__':main()
