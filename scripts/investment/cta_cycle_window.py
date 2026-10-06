"""Fixed older-cycle input adapter; existing CTA account and costs are reused."""
import json
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT, STATE
from scripts.investment.cta_cycle_source import sha
from scripts.investment.public_sma_perpetual import symbol_order

DAY=86_400_000_000
MINUTE=60_000_000
STATUS='PASS_FIXED_BTC_ETH_CYCLE_SOURCE_BINDING_NOT_ECONOMICS'


def month(t):
    return datetime.fromtimestamp(t/1e6,UTC).strftime('%Y-%m')


def minute_blocks(records,symbols,start,end,*,trade_ranges=False):
    """Read one synchronized day, retaining all assets and missing-data errors."""
    table={(r['kind'],r['symbol'],r['month']):r for r in records}
    assert len(table)==len(records) and start<end and start%DAY==end%DAY==0
    for day in range(start,end,DAY):
        times=np.arange(day,day+DAY,MINUTE,dtype=np.int64);market={}
        for s in symbols:
            t=pl.scan_parquet(table['klines',s,month(day)]['normalized_path']).filter(
                (pl.col('open_us')>=day)&(pl.col('open_us')<day+DAY)).sort('open_us').collect(engine='streaming')
            m=pl.scan_parquet(table['markPriceKlines',s,month(day)]['normalized_path']).filter(
                (pl.col('timestamp_ms')*1000>=day)&(pl.col('timestamp_ms')*1000<day+DAY)).sort('timestamp_ms').collect(engine='streaming')
            assert np.array_equal(t['open_us'].to_numpy(),times) and np.array_equal(m['timestamp_ms'].to_numpy()*1000,times)
            assert t['available_us'].eq(t['open_us']+MINUTE).all() and m['close_time_ms'].eq(m['timestamp_ms']+59999).all()
            v=t.select('open','close','quote_volume').to_numpy();mark=m['close'].to_numpy()
            assert np.isfinite(v).all() and np.all(v[:,:2]>0) and np.all(v[:,2]>=0) and np.isfinite(mark).all() and np.all(mark>0)
            market[s]=dict(open=v[:,0],close=v[:,1],quote_volume=v[:,2],mark=mark)
            if trade_ranges:
                extra=t.select('high','low','volume').to_numpy()
                assert np.isfinite(extra).all() and np.all(extra[:,:2]>0) and np.all(extra[:,2]>=0)
                market[s].update(high=extra[:,0],low=extra[:,1],volume=extra[:,2])
        yield dict(times=times,market=market)


def daily_from_minutes(record):
    frame=pl.scan_parquet(record['normalized_path']).with_columns((pl.col('open_us')//DAY*DAY).alias('day')).group_by('day').agg(
        pl.col('open').sort_by('open_us').first(),pl.col('high').max(),pl.col('low').min(),
        pl.col('close').sort_by('open_us').last(),pl.col('volume').sum(),pl.col('quote_volume').sum(),
        pl.len().alias('rows'),pl.col('open_us').min().alias('first'),pl.col('open_us').max().alias('last'),
        pl.col('available_us').max().alias('available')).sort('day').collect(engine='streaming')
    assert frame['rows'].eq(1440).all() and frame['first'].eq(frame['day']).all()
    assert frame['last'].eq(frame['day']+DAY-MINUTE).all() and frame['available'].eq(frame['day']+DAY).all()
    return frame.select('open','high','low','close','volume','quote_volume').with_columns(
        pl.Series('open_us',frame['day']),pl.Series('close_us',frame['day']+DAY),
        pl.Series('available_us',frame['day']+DAY),pl.lit(record['symbol']).alias('symbol'),pl.lit('1d').alias('interval'))


def load_window(path,symbols,preparation_start,end):
    p=Path(path).resolve();assert p.is_relative_to(STATE) and not p.is_symlink()
    manifest=json.loads(p.read_bytes());symbols=symbol_order(symbols)
    assert manifest['status']==STATUS and tuple(manifest['symbols'])==symbols and symbols in (('BTCUSDT',),('BTCUSDT','ETHUSDT'))
    start=manifest['start_us'];assert preparation_start<=start<end==manifest['end_us']
    for ref in manifest['source_reports']:
        source_path=ROOT/ref['path'];assert sha(source_path)==ref['sha256']
        source=json.loads(source_path.read_bytes())
        assert source['status']==ref['producer_status']
        task=json.loads((STATE/'task-progress'/('task-'+source['binding']['task_id']+'.json')).read_bytes())
        assert task['status']==('completed' if ref['expected_exit_code']==0 else 'failed') and task['exit_code']==ref['expected_exit_code']
    records=manifest['market_records'];warm=manifest['daily_records'];frames=[];events=[]
    for row in [*records,*warm]:
        file=Path(row['normalized_path']).resolve()
        assert file.is_relative_to(STATE) and not file.is_symlink() and file.stat().st_size==row['normalized_bytes'] and sha(file)==row['normalized_sha256']
        if row in warm:frames.append(pl.read_parquet(file).select('open','high','low','close','volume','quote_volume','open_us','close_us','available_us','symbol','interval'))
        elif row['kind']=='klines':frames.append(daily_from_minutes(row))
        elif row['kind']=='fundingRate':
            for v in pl.read_parquet(file).iter_rows(named=True):
                assert start<=v['calc_time_ms']*1000<end and np.isfinite(v['last_funding_rate'])
                events.append(dict(symbol=row['symbol'],event_us=v['calc_time_ms']*1000,
                    raw_rate=v['last_funding_rate'],reported_interval_hours=v['funding_interval_hours']))
    daily=pl.concat(frames).sort(['symbol','open_us'])
    for s in symbols:
        times=daily.filter(pl.col('symbol')==s)['open_us'].to_numpy()
        assert np.array_equal(times,np.arange(manifest['warmup_start_us'],end,DAY,dtype=np.int64))
    assert daily['available_us'].eq(daily['close_us']).all() and daily.select(pl.struct('symbol','open_us').n_unique()).item()==daily.height
    assert len(events)==manifest['funding_events'] and len({(r['symbol'],r['event_us']) for r in events})==len(events)
    events.sort(key=lambda r:(r['event_us'],r['symbol']))
    return dict(start=start,end=end,symbols=symbols,daily=daily,events=events,input_proofs=records,
        minute_blocks=lambda begin=start,stop=end,**kw:minute_blocks(records,symbols,begin,stop,**kw),
        source_scope='FIXED_COMPLETE_'+str(len(symbols))+'_ASSET_OLD_CYCLE_NOT_10COIN_POOL_OR_NATIVE_BYBIT')
