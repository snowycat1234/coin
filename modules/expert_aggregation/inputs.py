"""Byte-exact relocation, existing targets and accepted calendar; no old receipt fabrication."""
from pathlib import Path
import numpy as np
import polars as pl
from .common import DAY,MINUTE,atomic,read,sha

def prepare(repo,state,reuse):
    from scripts.investment.cta_cycle_window import daily_from_minutes
    index=read(reuse/'RELOCATION_INDEX.json');mapping={};protocol=read(repo/'modules/expert_aggregation/protocol.json')
    if index['manifest_sha256']!=protocol['original_manifest_sha256'] or index['expert_report_sha256']!=protocol['original_expert_report_sha256']:raise ValueError('Original published report/manifest identity anchor changed')
    for r in index['entries']:
        p=(reuse/r['relative_path']).resolve()
        if not p.is_relative_to(reuse.resolve()) or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:
            raise ValueError('Relocation SHA/size/path disagreement: '+r['original_path'])
        mapping[r['original_path']]=p
    if sha(mapping[index['manifest_original_path']])!=index['manifest_sha256']:raise ValueError('Original manifest bytes changed')
    manifest=read(mapping[index['manifest_original_path']])
    if manifest['status']!='PASS_FIXED_BTC_ETH_CYCLE_SOURCE_BINDING_NOT_ECONOMICS' or manifest['symbols']!=['BTCUSDT']:
        raise ValueError('Exact accepted BTC input scope required')
    report=read(repo/index['expert_report_relative_path'])
    if sha(repo/index['expert_report_relative_path'])!=index['expert_report_sha256']:raise ValueError('Original expert report changed')
    for r in manifest['market_records']+manifest['daily_records']:
        if sha(mapping[r['normalized_path']])!=r['normalized_sha256'] or mapping[r['normalized_path']].stat().st_size!=r['normalized_bytes'] or sha(mapping[r['receipt_path']])!=r['receipt_sha256']:
            raise ValueError('Relocation must match original manifest source/receipt identity')
    for entry in report['library']:
        for ref in entry['artifacts'].values():
            if sha(mapping[ref['path']])!=ref['sha256'] or mapping[ref['path']].stat().st_size!=ref['bytes']:raise ValueError('Relocation must match original expert artifact identity')
    # Bind original project reports without demanding the old machine's task paths.
    evidence=[]
    for ref in manifest['source_reports']+report['producers']:
        if sha(repo/ref['path'])!=ref['sha256']:raise ValueError('Original producer bytes changed')
        evidence.append(dict(path=ref['path'],sha256=ref['sha256'],role='ORIGINAL_PRODUCER_SCOPE_RETAINED'))
    cache=state/'cache';cache.mkdir(exist_ok=True)
    daily=[];trade=[];marks=[];events=[]
    for original in manifest['market_records']+manifest['daily_records']:
        r={**original,'normalized_path':str(mapping[original['normalized_path']])}
        if original in manifest['daily_records']:
            daily.append(pl.read_parquet(r['normalized_path']).select('open','high','low','close','volume','quote_volume','open_us','close_us','available_us','symbol','interval'))
        elif r['kind']=='klines':
            daily.append(daily_from_minutes(r));trade.append(pl.read_parquet(r['normalized_path']))
        elif r['kind']=='markPriceKlines':marks.append(pl.read_parquet(r['normalized_path']))
        elif r['kind']=='fundingRate':
            for v in pl.read_parquet(r['normalized_path']).iter_rows(named=True):
                events.append(dict(symbol=r['symbol'],event_us=int(v['calc_time_ms'])*1000,
                    raw_rate=float(v['last_funding_rate']),reported_interval_hours=float(v['funding_interval_hours'])))
    bars=pl.concat(daily).sort('open_us')
    if not np.array_equal(bars['open_us'].to_numpy(),np.arange(manifest['warmup_start_us'],manifest['end_us'],DAY)):
        raise ValueError('Incomplete real past daily calendar')
    if not bars['available_us'].eq(bars['close_us']).all():raise ValueError('Daily visibility disagreement')
    bars.write_parquet(cache/'daily.parquet',compression='zstd')
    t=pl.concat(trade).sort('open_us');m=pl.concat(marks).sort('timestamp_ms')
    times=np.arange(manifest['start_us'],manifest['end_us'],MINUTE,dtype=np.int64)
    if not np.array_equal(t['open_us'].to_numpy(),times) or not np.array_equal(m['timestamp_ms'].to_numpy()*1000,times):raise ValueError('No dropped or imputed minutes allowed')
    if not t['available_us'].eq(t['open_us']+MINUTE).all() or not m['close_time_ms'].eq(m['timestamp_ms']+59999).all():raise ValueError('Minute closure disagreement')
    start=1672531200000000;end=1704067200000000 # 2023 UTC, registered seen evaluation
    mask=(times>=start)&(times<end)
    for col,arr in [('open',t['open'].to_numpy()),('close',t['close'].to_numpy()),('quote_volume',t['quote_volume'].to_numpy()),('mark',m['close'].to_numpy())]:
        if not np.isfinite(arr).all() or np.any(arr<0) or col!='quote_volume' and np.any(arr==0):raise ValueError('Observed finite prices/capacity required')
        np.save(cache/(col+'.npy'),arr[mask],allow_pickle=False)
    event_list=sorted(events,key=lambda r:(r['event_us'],r['symbol']))
    if len(event_list)!=manifest['funding_events'] or len({(r['symbol'],r['event_us']) for r in event_list})!=len(event_list):raise ValueError('Funding event exact-once completeness')
    atomic(cache/'events.json',[r for r in event_list if start<=r['event_us']<end])
    feedback={};targets={}
    for entry in report['library']:
        key=entry['unit'];name=entry['expert']
        nav=pl.read_parquet(mapping[entry['artifacts']['daily_nav.parquet']['path']])
        frame=pl.read_parquet(mapping[entry['artifacts']['targets.parquet']['path']])
        if nav.height!=730 or frame.height!=730:raise ValueError('Only complete continuous old experts')
        if not np.array_equal(nav['day_end_us'].to_numpy(),np.arange(manifest['start_us']+DAY,manifest['end_us']+DAY,DAY)):raise ValueError('Shadow feedback full daily calendar')
        values=nav['nav'].to_numpy();previous=np.r_[10000.,values[:-1]]
        if np.any(values<=0) or not np.isfinite(values).all():raise ValueError('Positive complete original NAV required')
        feedback.setdefault(key,{})[name]=(values-previous)/previous
        targets.setdefault(key,{})[name]=frame
    names=report['protocol']['experts']
    for unit in feedback:
        np.save(cache/(unit+'-feedback.npy'),np.column_stack([feedback[unit][n] for n in names]),allow_pickle=False)
        for name in names:targets[unit][name].write_parquet(cache/(unit+'-'+name+'-targets.parquet'),compression='zstd')
    proof=dict(status='PASS_BYTE_EXACT_RELOCATED_SELECTED_ACCEPTED_BTC_AND_16_CONTINUOUS_SHADOW_EXPERTS',
        original_manifest_sha256=index['manifest_sha256'],original_expert_report_sha256=index['expert_report_sha256'],
        relocation_index_sha256=sha(reuse/'RELOCATION_INDEX.json'),original_reports=evidence,
        original_paths_and_byte_identities_preserved=True,old_task_receipts_fabricated=False,old_files_modified=False,
        reused_source_references=len(index['entries']),calendar_minutes=len(times),evaluation_minutes=int(mask.sum()),
        start=start,end=end,names=names,funding_original_events=len(events),funding_unit_certified=False,
        scope='Selected accepted BTC records only; no promotion of overall failed source producer; historical Binance execution proxy',
        files=[dict(path=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(cache.iterdir()) if p.is_file() and p.name!='INPUT_BINDING.json'])
    atomic(cache/'INPUT_BINDING.json',proof)
    return proof

def window(state):
    cache=state/'cache';proof=read(cache/'INPUT_BINDING.json')
    return dict(start=proof['start'],end=proof['end'],symbols=('BTCUSDT',),
        daily=pl.read_parquet(cache/'daily.parquet'),events=read(cache/'events.json'),
        market={'BTCUSDT':{c:np.load(cache/(c+'.npy'),mmap_mode='r',allow_pickle=False) for c in ('open','close','quote_volume','mark')}},
        input_proofs=[proof],source_scope=proof['scope'])
