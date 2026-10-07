"""Read-only actual episode comparison for the sole seen 2025H1 stop.

No hypothetical reentry, return curve editing, new wallet or threshold search.
"""
import argparse,gzip,hashlib,json,os,subprocess,time
from decimal import Decimal as D
from pathlib import Path
from scripts.research.run_public_momentum import ROOT,sha
from scripts.research.inspect_short_liquidation import save,utc

EXPECTED='c9ad33955cde8bad0beadc476a3b6e07b9e46ac0115499c160b4cd32a3bc9c1c'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--result',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();began=time.monotonic()
    assert os.uname().sysname=='Linux' and sha(a.result)==EXPECTED
    assert a.output.resolve().is_relative_to(Path('/home/ubuntu/coin/execution-state'))
    cg=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (cg/'memory.max').read_text().strip()!='max' and int((cg/'memory.max').read_text())<=8_000_000_000
    assert (cg/'memory.swap.max').read_text().strip()=='0'
    result=json.loads(a.result.read_text());sources={str(a.result):sha(a.result)};rows=[]
    for row in result['cases']:
        if row['window']!='fold3-2025-01-02':continue
        old=next(x for x in result['reused_controls'] if x['window']==row['window'] and x['funding_scale']==row['funding_scale'])
        def case(item):
            assert sha(item['result_path'])==item['result_sha256'];sources[item['result_path']]=item['result_sha256']
            return json.loads(Path(item['result_path']).read_text())
        newcase,oldcase=case(row),case(old)
        def artifact(c,name):
            e=c['artifacts'][name+'.json'];assert sha(e['path'])==e['sha256'];sources[e['path']]=e['sha256']
            raw=gzip.decompress(Path(e['path']).read_bytes());assert hashlib.sha256(raw).hexdigest()==e['uncompressed_sha256']
            return json.loads(raw)
        journal=artifact(newcase,'protection_journal');hits=[x for x in journal if x['kind']=='OBSERVED_SHORT_COLLATERAL_FLOOR']
        assert len(hits)==1;hit=hits[0];s,t=hit['symbol'],hit['event_us']
        reset=next(x for x in journal if x['kind']=='ORIGINAL_SHORT_SIGNAL_RESET' and x['symbol']==s and x['event_us']>t)
        def episode(c):
            trades=[x for x in artifact(c,'trades') if x['symbol']==s]
            start=max(i for i,x in enumerate(trades) if x['event_us']<=t and x['quantity_before']==0 and x['quantity_after']<0)
            end=next(i for i in range(start,len(trades)) if trades[i]['quantity_after']==0)
            held=trades[start:end+1];assert all(x['quantity_after']<0 for x in held[:-1])
            funding=[x for x in artifact(c,'funding') if x['symbol']==s and x['quantity']<0 and held[0]['event_us']<=x['event_us']<=held[-1]['event_us']]
            # Realized fill PnL already includes execution; do not subtract it twice.
            price=sum(x['realized_PnL'] for x in held);fees=sum(x['fee_USDT_mid'] for x in held)
            cash=sum(x['signed_funding_USDT'] for x in funding)
            after=[x for x in trades if t<x['event_us']<reset['event_us']]
            fields=('event_us','signal_us','leg','side','quantity_before','quantity_after','fill_price','realized_PnL','fee_USDT_mid','execution_cost')
            return dict(start_us=held[0]['event_us'],start_utc=utc(held[0]['event_us']),end_us=held[-1]['event_us'],end_utc=utc(held[-1]['event_us']),
                realized_fill_PnL=price,fees=fees,funding=cash,net_episode=price-fees+cash,
                last_fill={k:held[-1][k] for k in fields},fills_in_block_interval=[{k:x[k] for k in fields} for x in after]),held,trades
        before,oldfills,allold=episode(oldcase);after,newfills,allnew=episode(newcase)
        assert before['start_us']==after['start_us'] and after['end_us']<reset['event_us']
        pre=next(x for x in reversed(oldfills) if x['event_us']<=t)['decimal_strings']
        assert D(pre['quantity_after'])==D(hit['quantity']) and D(pre['entry_price_after'])==D(hit['entry_price'])
        assert not any(x['quantity_after']<0 for x in allnew if after['end_us']<x['event_us']<reset['event_us'])
        delta=row['contributions']['SHORT']['net_contribution']-old['contributions']['SHORT']['net_contribution']
        rows.append(dict(window=row['window'],funding_scale=row['funding_scale'],symbol=s,trigger=hit,trigger_utc=utc(t),reset=reset,
            reset_utc=utc(reset['event_us']),blocked_days=(reset['event_us']-t)/86_400_000_000,
            old_actual_episode=before,new_actual_episode=after,episode_net_change=after['net_episode']-before['net_episode'],
            total_SHORT_net_change=delta,other_SHORT_net_change=delta-(after['net_episode']-before['net_episode']),
            original_episode_ended_at_reset_decision=oldfills[-1]['signal_us']==reset['event_us'],
            later_original_short_opens_before_reset=sum(x['quantity_before']==0 and x['quantity_after']<0 for x in allold if after['end_us']<x['event_us']<reset['event_us'])))
        print(f'[EPISODE {len(rows)}/2] {s} funding_scale={row["funding_scale"]}',flush=True)
    assert len(rows)==2
    out=dict(status='COMPLETE_ACTUAL_STOP_EPISODE_DIAGNOSIS',source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),
        source_sha256=sha(__file__),source_hashes=sources,cases=rows,new_wallets=0,new_fits=0,qualification='NONE_CASH',locked_consumed=False,
        elapsed_seconds=time.monotonic()-began,limitations=['Chosen after observing failure: seen development diagnosis, not independent validation.',
            'Actual realized fill PnL includes execution; episode net subtracts fees once and adds recorded funding.',
            'Episode differences are descriptive. Shared capital changes other trades; they do not isolate causal benefit of hypothetical reentry.',
            'No simulated reentry, edited costs or new thresholds. Original failed decision remains unchanged.'])
    save(a.output,out)


if __name__=='__main__':main()
