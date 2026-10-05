"""Read-only paired economics; no account replay or removal of costs."""
import argparse,json
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT
from scripts.investment.run_cta_leaderboard import sha,write
from scripts.investment.turtle_turnover_diagnostic import asset_attribution

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--result',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();r=json.loads(a.result.read_bytes());assert len(r['cases'])==4
    oldpath=ROOT/r['protocol']['original_result']['path'];assert sha(oldpath)==r['protocol']['original_result']['sha256']
    old=json.loads(oldpath.read_bytes());pairs=[]
    for c in sorted(r['cases'],key=lambda v:v['id']):
        for art in c['artifacts'].values():assert sha(art['path'])==art['sha256']
        base=next(v for v in old['cases'] if v['strategy']=='TSMOM12M' and v['mode']=='LONG_SHORT' and v['cost']==c['cost'] and v['unit']==c['unit'])
        def checked_frame(v):
            art=v['artifacts']['minute_nav_inventory.parquet'];assert sha(art['path'])==art['sha256'];return pl.read_parquet(art['path'])
        f=checked_frame(c);b=checked_frame(base);cut=min(int(f['close_us'][-1]),int(b['close_us'][-1]))
        fp=f.filter(pl.col('close_us')<=cut);bp=b.filter(pl.col('close_us')<=cut)
        assert fp['close_us'].equals(bp['close_us'])
        def prefix(fr):
            nav=np.r_[10000.,fr['nav'].to_numpy()]
            return dict(minutes=fr.height,net=float(nav[-1]-10000.),max_drawdown=float(np.max(1-nav/np.maximum.accumulate(nav))),
                fees=float(fr['cumulative_fees'][-1]),execution_cost=float(fr['cumulative_execution_costs'][-1]),
                funding=float(fr['cumulative_funding'][-1]),turnover=float(fr['cumulative_turnover'][-1]),
                mean_gross=float(fr['gross_weight'].mean()),mean_net=float(fr['net_signed_weight'].mean()))
        x=prefix(fp);y=prefix(bp);s=c['summary'];journal=json.loads(Path(c['artifacts']['protection_journal.json']['path']).read_bytes())
        trigger=[v for v in journal if v['kind']=='OBSERVED_STOP_TRIGGER'];fills=[v for v in journal if v['kind']=='PROTECTIVE_FILL']
        arm=[v for v in journal if v['kind']=='ARM'];assert all(v['source_available_us']<=v['event_us'] for v in arm)
        trades=json.loads(Path(c['artifacts']['trades.json']['path']).read_bytes())
        funding=json.loads(Path(c['artifacts']['funding.json']['path']).read_bytes())
        assets=asset_attribution(trades,funding,s)
        known={(v['symbol'],v['signal_us']) for v in fills}
        reasons={}
        for trade in trades:
            reason='PROTECTIVE_STOP' if (trade['symbol'],trade['signal_us']) in known else (
                'TERMINAL' if trade['signal_us']==1_751_328_000_000_000-6*60_000_000 else 'UNKNOWN')
            total=reasons.setdefault(reason,dict(legs=0,notional=0.,fees=0.,execution_cost=0.))
            total['legs']+=1;total['notional']+=trade['quantity']*trade['mid_price']
            total['fees']+=trade['fee_USDT_mid'];total['execution_cost']+=trade['execution_cost']
        assert all(v['armed_us']<=v['minute_open_us'] and v['event_us']==v['minute_open_us']+60_000_000 for v in trigger)
        assert all(v['event_us']>=v['signal_us']+60_000_001 and abs(v['quantity_after'])<abs(v['quantity_before']) for v in fills)
        controls={}
        for family,mode in [('TSMOM12M','LONG_ONLY'),('HOLD','LONG_ONLY'),('DC_TSMOM_ENSEMBLE','LONG_SHORT'),('CASH','CASH')]:
            v=next(v for v in old['cases'] if v['strategy']==family and v['mode']==mode and v['cost']==c['cost'] and v['unit']==c['unit'])
            controls[family+'_'+mode]=dict(net=v['summary']['net_PnL'],minute_DD=v['summary']['minute_max_drawdown'],
                daily_vol=v['summary']['daily_metrics']['annual_volatility'],
                cost=v['summary']['fees_USDT']+v['summary']['execution_cost_USDT'],
                residual=v['summary']['terminal_marked_notional'])
        pairs.append(dict(id=c['id'],complete=s['completed_minutes']==s['required_minutes'],summary=s,
            shared_prefix=dict(last_close_us=cut,protected=x,original=y,net_delta=x['net']-y['net'],scope='COMMON_RECORDED_MINUTE_ENDPOINT_NOT_STOP_SUMMARY_OR_FULL122D'),
            controls=controls,observed_stop_count=len(trigger),protective_fill_count=len(fills),
            stop_assets=sorted(set(v['symbol'] for v in trigger)),
            protective_cost=sum(v['fees']+v['execution_cost'] for v in fills),
            asset_attribution=assets,reliable_order_reason_costs=reasons,
            original_case_id=base['id'],original_minute_sha256=base['artifacts']['minute_nav_inventory.parquet']['sha256']))
    write(a.output,dict(status='PASS_READ_ONLY_PAIRED_STOP_AND_ECONOMIC_DIAGNOSTIC',result_sha256=sha(a.result),cases=pairs,
        complete_accounts=sum(v['complete'] for v in pairs),models_fit=0,accounts_replayed=0,
        claim_limits='Seen122D crossvenue proxy, funding unknown, MMR assumed, risk unmatched. Frozen alpha targets unchanged; cooldown executed zeros in journal. No long-term APR or investment promotion.'))
    print(json.dumps(dict(status='DIAGNOSTIC_WRITTEN',cases=len(pairs))))

if __name__=='__main__':main()
