"""Bounded ex-post liquidity probe at the previously recorded half-collateral witness.

Not a wallet or counterfactual PnL: retain the original account/source bytes.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_DOWN, localcontext
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import polars as pl
from quant.execution_contract import ExecutionContractV2
from scripts.research.inspect_short_liquidation import sha, save

ROOT=Path(__file__).resolve().parents[2]
MINUTE=60_000_000
FORENSIC='77c44b9b8430cf096518fa5bee8a7d45d629fe2de36a0181a9bab24132d67a6c'
EXTENSION='8e034c498ac50847b5130408d8f17a0d95b6975711023b37de0f9b0eca46bc3f'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args();began=time.monotonic()
    assert os.uname().sysname=='Linux' and a.state.resolve().parent==Path('/home/ubuntu/coin/execution-state')
    cg=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (cg/'memory.max').read_text().strip()!='max' and int((cg/'memory.max').read_text())<=8_000_000_000
    assert (cg/'memory.swap.max').read_text().strip()=='0';a.state.mkdir(exist_ok=False)
    fp=ROOT/'reports/SHORT_LIQUIDATION_FORENSIC_20261008.json';ep=ROOT/'reports/FIXED_TREND_EXTENSION_20261008.json'
    assert sha(fp)==FORENSIC and sha(ep)==EXTENSION
    forensic=json.loads(fp.read_text());extension=json.loads(ep.read_text());sources={str(fp):sha(fp),str(ep):sha(ep)}
    rows=[]
    for i,f in enumerate(forensic['cases'],1):
        source=next(x for x in extension['cases'] if x['family']==f['family'] and x['funding_scale']==f['funding_scale'] and x['window']=='fold2-2024-08-13')
        assert sha(source['result_path'])==source['result_sha256'];sources[source['result_path']]=source['result_sha256']
        case=json.loads(Path(source['result_path']).read_text());symbol=f['witness']['symbol']
        crossing=next(x for x in f['descriptive_equity_crossings'] if x['fraction']==.5)
        obs=crossing['observation'];signal=int(obs['close_us']);liquidation=int(f['witness']['event_us'])
        assert signal%MINUTE==0 and signal+11*MINUTE<liquidation
        def artifact(name):
            e=case['artifacts'][name+'.json'];assert sha(e['path'])==e['sha256'];sources[e['path']]=e['sha256']
            raw=gzip.decompress(Path(e['path']).read_bytes());assert hashlib.sha256(raw).hexdigest()==e['uncompressed_sha256']
            return json.loads(raw)
        trades=artifact('trades');rejections=artifact('rejections');breaches=artifact('breaches')
        prior=[x for x in trades if x['symbol']==symbol and x['event_us']<=signal]
        exact=prior[-1]['decimal_strings'];q=D(exact['quantity_after']);entry=D(exact['entry_price_after'])
        assert q<0 and float(q)==obs[symbol+'_quantity']
        c=case['summary']['contract'];step=D(c['quantity_step_assumption'])
        assert step==D('1e-8') and c['taker_fee_bps_per_side']==5.5 and c['closing_min_notional_exempt']
        # Bound only the required existing monthly source, not an unrelated scan.
        bp=Path(case['task']['native_market_binding_path'])
        assert sha(bp)==case['task']['native_market_binding_sha256'];sources[str(bp)]=sha(bp)
        binding=json.loads(bp.read_text());month=datetime.fromtimestamp(signal/1e6,timezone.utc).strftime('%Y-%m')
        source_path=Path(binding['work'])/'data/normalized/minute'/symbol/'klines'/(month+'.parquet')
        admitted=next(x for x in binding['files'] if x['path']==str(source_path));assert admitted['exists'] and sha(source_path)==admitted['sha256']
        sources[str(source_path)]=admitted['sha256']
        frame=pl.read_parquet(source_path).filter(pl.col('open_us').is_between(signal,signal+10*MINUTE)).sort('open_us')
        assert frame['open_us'].to_list()==list(range(signal,signal+11*MINUTE,MINUTE))
        assert frame['available_us'].eq(frame['open_us']+MINUTE).all()
        bars={x['open_us']:x for x in frame.iter_rows(named=True)};first=ExecutionContractV2().earliest_execution_us(signal)
        remaining=abs(q);fills=[];cost=D(0)
        with localcontext() as ctx:
            ctx.prec=40
            for t in range(first,signal+11*MINUTE,MINUTE):
                row=bars[t];previous=bars[t-MINUTE]
                assert previous['available_us']==t
                mid=D(str(row['open']));capacity=D(str(previous['quote_volume']))*D('.001')/mid
                amount=(min(remaining,capacity)/step).to_integral_value(rounding=ROUND_DOWN)*step
                if not amount:continue
                fill=mid*D('1.0008');fee=amount*fill*D('.00055');execution=amount*(fill-mid)
                remaining-=amount;cost+=fee+execution
                fills.append(dict(event_us=t+1,signal_us=signal,quote_available_us=t,capacity_bar_close_us=previous['available_us'],
                    quantity=str(amount),remaining=str(remaining),mid=str(mid),fill=str(fill),fee=str(fee),execution=str(execution)))
                if remaining==0:break
        actual_conflicts=[{k:x.get(k) for k in ('event_us','signal_us','leg','fill_id','quantity')} for x in trades
            if x['symbol']==symbol and signal<=x['event_us']<=signal+11*MINUTE]
        risk_conflicts=[x for x in breaches if signal-5*MINUTE<=x['signal_us']<=signal+11*MINUTE]
        order_events=[x for x in rejections if x.get('symbol')==symbol and signal-5*MINUTE<=x['event_us']<=signal+11*MINUTE]
        rows.append(dict(id=f['id'],family=f['family'],funding_scale=f['funding_scale'],signal_us=signal,
            observation=obs,original_entry=str(entry),hours_to_original_liquidation=crossing['hours_before_liquidation'],
            first_legal_execution_us=first+1,probe_fills=fills,full_quantity_cleared=remaining==0,remaining_quantity=str(remaining),
            seconds_to_clear=(fills[-1]['event_us']-signal)/1e6 if remaining==0 else None,
            close_fee_execution_USDT=str(cost),original_actual_trades_in_probe=actual_conflicts,
            original_risk_signals_near_probe=risk_conflicts,original_order_events_near_probe=order_events))
        print(f'[CAPACITY {i}/4] {f["id"]} full_quantity_cleared={remaining==0}',flush=True)
    out=dict(status='COMPLETE_EXISTING_SHORT_EXIT_CAPACITY_PROBE',source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),
        source_sha256=sha(__file__),cases=rows,source_hashes=sources,new_wallets=0,new_fits=0,market_downloads=0,
        locked_consumed=False,qualification='NONE_CASH',elapsed_seconds=time.monotonic()-began,
        limitations=['Ex-post fixed half-collateral witness liquidity probe only; no new threshold search or counterfactual return.',
            'Original quantity close with unchanged fees/latency/step and previous completed quote capacity; no new wallet/funding/NAV path.',
            'Existing actual order/risk conflicts are reported, not assumed to vanish; complete shared-wallet scheduler must test any protection.',
            'No intraminute liquidation, native Bybit execution/filter/risk-tier or funding-unit certification. Gaps can defeat stops.'])
    save(a.state/'RESULTS.json',out);print(json.dumps(dict(status=out['status'],seconds=out['elapsed_seconds'])),flush=True)


if __name__=='__main__':main()
