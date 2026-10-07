"""Read-only asset/side cash bridge for the four already completed wallets."""
import argparse,json,os,time
from pathlib import Path
from modules.transformer_v3.storage import hydrated_account
from scripts.research.diagnose_short_routing import journal_bridge,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    began=time.monotonic();state=a.state.resolve();assert os.uname().sysname=='Linux' and state.is_relative_to(Path('/home/ubuntu/coin/execution-state'))
    source=state/'RESULTS.json';r=json.loads(source.read_text());rows=[];max_error=0.
    assert r['actual_new_wallets']==4 and r['actual_new_fits']==0
    for summary in r['cases']:
        path=Path(summary['result_path']);assert sha(path)==summary['result_sha256']
        c=json.loads(path.read_text());assert c['summary']['liquidation_count']==0 and c['summary']['terminal_cash_realized']
        for e in c['artifacts'].values():assert sha(e['path'])==e['sha256']
        per_asset=[];totals={s:{k:0. for k in ('gross','fees','execution_cost','funding','net')} for s in ('LONG','SHORT')}
        with hydrated_account(Path(c['summary_path']).parent,state/'diagnostic-scratch') as account:
            trades=json.loads((account/'trades.json').read_text());funds=json.loads((account/'funding.json').read_text())
            for symbol in c['summary']['symbols']:
                t=[x for x in trades if x['symbol']==symbol];f=[x for x in funds if x['symbol']==symbol]
                v,episodes=journal_bridge(t,f,'RAW_AS_FRACTION' if summary['funding_scale']==1 else 'RAW_AS_PERCENT','BASE27')
                per_asset.append(dict(symbol=symbol,sides=v,short_episodes=episodes,trade_legs=len(t)))
                for side in totals:
                    for key in totals[side]:totals[side][key]+=v[side][key]
        for side in totals:
            expected=c['summary']['long_short_marked_contribution'][side]
            for key,value in totals[side].items():
                error=abs(value-expected['net_contribution' if key=='net' else key]);max_error=max(max_error,error);assert error<1e-7
        assert abs(sum(v['net'] for v in totals.values())-c['summary']['net_PnL'])<1e-7
        rows.append(dict(window=summary['window'],funding_scale=summary['funding_scale'],assets=per_asset,totals=totals))
    out=state/'ASSET_DIAGNOSIS.json';assert not out.exists()
    out.write_text(json.dumps(dict(status='PASS_READ_ONLY_PER_ASSET_CLOSED_CASH_BRIDGE',source_sha256=sha(__file__),input_sha256=sha(source),
        maximum_error_USDT=max_error,cases=rows,new_wallets=0,new_fits=0,elapsed_seconds=time.monotonic()-began),indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status='PASS_READ_ONLY_PER_ASSET_CLOSED_CASH_BRIDGE',maximum_error_USDT=max_error)),flush=True)

if __name__=='__main__':main()
