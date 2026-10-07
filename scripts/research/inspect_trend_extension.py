"""Read-only current-source check for frozen trend stage extension; no labels."""
import argparse,json,os,time
from datetime import UTC,datetime
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import polars as pl

from modules.transformer_v3.market_binding import prepare_binding,verify_binding
from scripts.research.run_public_momentum import ROOT,sha,save

DAY=86_400_000_000
CORE=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']


def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp()*1_000_000)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    began=time.monotonic();state=a.state.resolve()
    assert os.uname().sysname=='Linux' and state.parent==Path('/home/ubuntu/coin/execution-state')
    state.mkdir(exist_ok=False)
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8_000_000_000
    assert (group/'memory.swap.max').read_text().strip()=='0'
    parent_path=ROOT/'protocols/PUBLIC_CROSS_SECTION_MOMENTUM_20261008.json';p=json.loads(parent_path.read_text())
    work=Path(p['work']);manifest=work/'reports/DATASET_MANIFEST.json'
    assert sha(manifest)==p['data_manifest_sha256']
    plan_path=Path('/home/ubuntu/coin/execution-state/automation/server-complete-20261007-hardware/VALIDATION_PLAN.json')
    plan=json.loads(plan_path.read_text());assert plan['dataset_sha256']==p['data_manifest_sha256'] and plan['symbols']==p['symbols']
    windows=[dict(w,active_symbols=CORE) for w in plan['windows'] if w['fold'] in (2,4)]
    assert [(w['fold'],w['days']) for w in windows]==[(2,41),(2,142),(4,184)]
    assert [(w['start'],w['end']) for w in windows]==[(stamp('2024-07-02'),stamp('2024-08-12')),(stamp('2024-08-13'),stamp('2025-01-02')),(stamp('2025-07-02'),stamp('2026-01-02'))]
    assert all(w['end']<p['locked_start_us'] for w in windows)
    excluded=[x for x in plan['excluded_gap_days'] if x['fold']==2]
    assert [x['day_us'] for x in excluded]==[stamp('2024-08-12')]
    gap=dict(id='known-source-gap-2024-08-12',fold=2,start=stamp('2024-08-12'),end=stamp('2024-08-13'),days=1,active_symbols=CORE)
    from modules.collector_research.validation import runtime
    runtime.configure(SimpleNamespace(collector_root=p['collector_root'],collector_work=work,source_run=p['source_run'],run_dir=state/'read-only-runtime',resource_policy='server',workers=1,minimum_days=30,publish_source_report=False,audit_device='cpu'))
    from modules.collector_research.validation import data
    cases=[]
    for i,w in enumerate(windows+[gap]):
        save(state/'progress.json',dict(status='running',phase='核对实际行情/mark/资金时钟',stage='DATA',completed=i,total=4,unit='窗口',updated_at=time.time()))
        binding=prepare_binding(state,w,p['symbols'],work,expected_manifest_sha256=p['data_manifest_sha256'])
        verified=verify_binding(binding,sha(binding))
        inputs=data.market_window(CORE,w['start'],w['end'])
        missing={s:[] for s in CORE};count={s:0 for s in CORE};invalid={s:0 for s in CORE};seen=0
        for block in inputs['minute_blocks']():
            times=block['times'];assert np.array_equal(times,np.arange(w['start']+seen*60_000_000,w['start']+(seen+len(times))*60_000_000,60_000_000))
            seen+=len(times)
            for s in CORE:
                if s not in block['market']:
                    missing[s].extend(int(t) for t in times);continue
                v=block['market'][s];count[s]+=len(times)
                good=np.isfinite(v['open'])&np.isfinite(v['close'])&np.isfinite(v['mark'])&(v['open']>0)&(v['close']>0)&(v['mark']>0)&np.isfinite(v['quote_volume'])&(v['quote_volume']>=0)
                invalid[s]+=int((~good).sum())
        assert seen==w['days']*1440
        flags={}
        for s in CORE:
            d=inputs['daily'].filter((pl.col('symbol')==s)&(pl.col('open_us')>=w['start'])&(pl.col('open_us')<w['end']))
            assert d.height==w['days'] and np.array_equal(d['open_us'].to_numpy(),np.arange(w['start'],w['end'],DAY))
            assert np.all(d['available_us'].to_numpy()==d['close_us'].to_numpy())
            flags[s]=dict(daily_rows=d.height,funding_events=sum(x['symbol']==s for x in inputs['events']))
        complete=all(not missing[s] and not invalid[s] for s in CORE)
        cases.append(dict(window=w,complete_trade_mark=complete,required_minutes=seen,observed_minutes=count,invalid_observed_minutes=invalid,missing_minutes=missing,source_daily_and_event_counts=flags,market_binding_path=str(binding),market_binding_sha256=sha(binding),market_files=verified['files']))
        print('[DATA] '+str(i+1)+'/4 '+w['id']+' missing='+str({s:len(missing[s]) for s in CORE}),flush=True)
    assert all(c['complete_trade_mark'] for c in cases[:3])
    assert cases[-1]['missing_minutes']['BTCUSDT']==[stamp('2024-08-12')+(10*60+2)*60_000_000,stamp('2024-08-12')+(10*60+3)*60_000_000]
    assert all(not cases[-1]['missing_minutes'][s] for s in CORE[1:])
    result=dict(status='PASS_COMPLETE_EXISTING_EXTENSION_WINDOWS_WITH_EXPLICIT_GAP',source_sha256=sha(__file__),parent_protocol_sha256=sha(parent_path),source_manifest_sha256=sha(manifest),plan_path=str(plan_path),plan_sha256=sha(plan_path),selected_windows=windows,excluded_gap_days=excluded,cases=cases,role='SEEN_DEVELOPMENT_ONLY; source-defined segments, no PnL selection, no account splicing',new_wallets=0,new_fits=0,new_downloads=0,locked_consumed=False,elapsed_seconds=time.monotonic()-began,limitations=['Current minute join/price positivity and actual event counts verified; funding unit/publication and instantaneous risk guarantees not certified','41day window is short diagnostic; no stable APR or complete2024H2 performance','MissingAug12 stays explicit and cannot be free navigation between positions'])
    save(state/'RESULTS.json',result);save(state/'progress.json',dict(status='completed',phase='完成',stage='DATA',completed=4,total=4,unit='窗口',updated_at=time.time()))
    print(json.dumps(dict(status=result['status'],seconds=result['elapsed_seconds'])),flush=True)


if __name__=='__main__':main()
