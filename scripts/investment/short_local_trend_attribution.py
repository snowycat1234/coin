"""Saved-wallet diagnosis: own SMA200 versus lagged global BTC labels."""
import json,os
from pathlib import Path
import polars as pl
from quant.paths import ROOT
from scripts.investment.cta_cycle_source import sha,save
from scripts.investment.cta_classics import DAY
from scripts.research_v7.oracle_flow_ceiling import Progress

p=ROOT/'reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json';raw=json.loads(p.read_bytes())
c=next(v for v in raw['cases'] if v['unit']=='RAW_AS_PERCENT');symbols=raw['protocol']['symbols']
gold=raw['protocol']['legacy_signal_golden'];assert sha(gold['path'])==gold['sha256']
signals=pl.read_parquet(gold['path']);own={(r['close_us'],r['symbol']):r['SMA200_SIGNED'] for r in signals.iter_rows(named=True)}
for k in ('minute_nav_inventory.parquet','trades.parquet','funding.parquet'):assert sha(c['artifacts'][k]['path'])==c['artifacts'][k]['sha256']
nav=pl.scan_parquet(c['artifacts']['minute_nav_inventory.parquet']['path']).filter(pl.col('close_us')%DAY==0).collect()
snaps={v['close_us']:v for v in nav.iter_rows(named=True)}
trades=pl.read_parquet(c['artifacts']['trades.parquet']['path']);fund=pl.read_parquet(c['artifacts']['funding.parquet']['path'])
dates=sorted(int(t) for t in raw['descriptive_past_states']);groups={};rows=[];progress=Progress()
for i,begin in enumerate(dates):
    end=begin+DAY;before=snaps.get(begin);after=snaps[end]
    if before is None:
        assert i==0;before={s+'_signed_marked_notional':0. for s in symbols}
    for s in symbols:
        fills=trades.filter((pl.col('symbol')==s)&(pl.col('event_us')>begin)&(pl.col('event_us')<=end)&((pl.col('quantity_before')<0)|(pl.col('quantity_after')<0)))
        assert fills.filter(pl.col('quantity_before')*pl.col('quantity_after')<0).is_empty()
        funding=fund.filter((pl.col('symbol')==s)&(pl.col('event_us')>begin)&(pl.col('event_us')<=end)&(pl.col('quantity')<0))
        gross=-(fills['position_delta']*fills['mid_price']).sum()+min(0.,after[s+'_signed_marked_notional'])-min(0.,before[s+'_signed_marked_notional'])
        fee=fills['fee_USDT_mid'].sum();execution=fills['execution_cost'].sum();cash=funding['signed_funding_USDT'].sum()
        state=own[(begin,s)];assert state in (-1.,0.,1.)
        own_label={-1.:'BELOW_OWN_SMA200',0.:'EQUAL_OWN_SMA200',1.:'ABOVE_OWN_SMA200'}[state]
        global_label=raw['descriptive_past_states'][str(begin)];key=global_label+'/'+own_label
        v=groups.setdefault(key,dict(asset_days=0,short_exposed_asset_days=0,gross=0.,fees=0.,execution=0.,funding=0.,net=0.))
        net=gross+cash-fee-execution;v['asset_days']+=1
        v['short_exposed_asset_days']+=int(before[s+'_signed_marked_notional']<0 or after[s+'_signed_marked_notional']<0 or not fills.is_empty())
        for k,x in [('gross',gross),('fees',fee),('execution',execution),('funding',cash),('net',net)]:v[k]+=x
        rows.append(dict(day_start_us=begin,symbol=s,past_BTC_label=global_label,past_own_SMA200=own_label,short_net=net))
    if i%30==0:progress.update('已保存空头损益与单币趋势核对',i+1,len(dates),'日期')
expected=c['summary']['long_short_marked_contribution']['SHORT']['net_contribution'];error=abs(sum(v['net'] for v in groups.values())-expected);assert error<1e-7
out=dict(status='PASS_SAVED_SHORT_LOCAL_TREND_PNL_BRIDGE_NOT_NEW_STRATEGY',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    producer_sha256=sha(p),signal_proof=gold,groups=groups,asset_days=len(rows),actual_SHORT=expected,bridge_error=error,
    new_accounts=0,fits=0,scope='POST_RESULT_DIAGNOSTIC_ONLY; OWN_PAST_PRICE_VS_SMA200_NOT_CERTIFIED_TRUE_BEAR; BTC_LABEL_NOT_EACH_ASSET_STATE; NO_NEW_GATE_OR_REMOVED_COSTS',rows=rows)
save(ROOT/'reports/SHORT_LOCAL_TREND_ATTRIBUTION_20261006_V1.json',out);progress.stop.set();progress.thread.join(timeout=3)
print(json.dumps(dict(status=out['status'],SHORT=expected,bridge_error=error,groups=groups)))
