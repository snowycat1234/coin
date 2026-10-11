"""One already-public original month, signed quote fields only, no forecasts."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'research/joint-correlation-risk-20261011'))
from inputs import SOURCE,SOURCE_PREFIX,git,digest,save
from prepare import SourceReader,bind_current,decode


def imbalance(total,buy):
    total=np.asarray(total,dtype=float);buy=np.asarray(buy,dtype=float)
    if total.shape!=buy.shape or not np.isfinite(total).all() or not np.isfinite(buy).all():
        raise ValueError('Complete matched total/buy fields required')
    if np.any(total<0) or np.any(buy<0) or np.any(buy>total):
        raise ValueError('Taker buy cannot exceed total quote volume')
    out=np.full(total.shape,np.nan)
    valid=total>0;out[valid]=(2*buy[valid]-total[valid])/total[valid]
    return out


def run(output):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists()
    assert not git('status','--porcelain').strip()
    assert shutil.disk_usage('/workspace').free>=16106127360
    output.mkdir();start=time.monotonic()
    protocol=(HERE/'PROTOCOL.json').read_bytes()
    meta_raw=git('show',SOURCE+':'+SOURCE_PREFIX+'phases/Q12022/RECOVERY.json')
    metadata=bind_current(json.loads(meta_raw),SOURCE)
    source=next(r['source'] for r in metadata['sources'] if r['source']['symbol']=='BTCUSDT' and r['source']['month']=='2022-01')
    assert source['ZIP_bytes']<=8388608 and source['kind']=='NEW_PUBLIC_PARTS'
    reader=SourceReader({},output)
    raw,check=reader.read(source);reader.close()
    left=1640995200000;right=1643673600000
    frame,duplicates=decode(raw,check,'BTCUSDT-1m-2022-01.zip',output,left,right)
    assert duplicates==0 and len(frame)==44640
    np.testing.assert_array_equal(frame.timestamp_ms,np.arange(left,right,60000))
    total=frame.quote_volume.to_numpy(dtype=float);buy=frame.taker_buy_quote_volume.to_numpy(dtype=float)
    volume=frame.volume.to_numpy(dtype=float);buy_volume=frame.taker_buy_volume.to_numpy(dtype=float)
    if np.any(buy_volume>volume):raise ValueError('Takerbuy base exceeds totalbase')
    minute=imbalance(total,buy)
    total_daily=total.reshape(31,1440).sum(1);buy_daily=buy.reshape(31,1440).sum(1)
    daily=imbalance(total_daily,buy_daily)
    t=(left+np.arange(1,32)*86400000)*1000
    np.savez_compressed(output/'SOURCE_FLOW_SAMPLE.npz',symbol_order=np.asarray(['BTCUSDT']),available_us=t,
        total_quote_volume=total_daily,taker_buy_quote_volume=buy_daily,signed_quote_imbalance=daily)
    proof=dict(status='PASS_ONE_MONTH_AGGRESSOR_QUOTE_SOURCE_PREFLIGHT',source_commit=SOURCE,
        scientific_source_HEAD=git('rev-parse','HEAD').decode().strip(),phase='Q12022',symbol='BTCUSDT',month='2022-01',
        source_recovery_metadata_SHA256=digest(meta_raw),source=source,CRC_and_official_CHECKSUM_verified=True,
        dense_actual_minutes=len(frame),complete_source_feature_days=31,quote_unit='USDTnominal traded quote',
        minute_buyquote_le_totalquote=True,minute_buybase_le_totalbase=True,
        zero_quote_minutes=int((total==0).sum()),unknown_minute_imbalance=int(np.isnan(minute).sum()),
        minute_imbalance_range=np.nanquantile(minute,[0,1]).tolist(),daily_imbalance_range=np.nanquantile(daily,[0,1]).tolist(),
        daily_buyquote_sum=float(buy_daily.sum()),daily_totalquote_sum=float(total_daily.sum()),
        availability='FollowingUTC00:00 complete day; historical arrival UNKNOWN',
        source_original_bytes=len(raw),protocol_SHA256=digest(protocol),code_SHA256=digest(Path(__file__).read_bytes()),
        artifact_SHA256=digest((output/'SOURCE_FLOW_SAMPLE.npz').read_bytes()),
        source_attempts=1,fits=0,future_labels=0,predictive_scores=0,wallets=0,provider_downloads=0,
        large_original_wrapper_reads=0,elapsed_seconds=time.monotonic()-start,
        limitation='One BTCmonth only, not completeCORE5flow recovery or price prediction. No trade-sign event order/L2/midprice/limit-order meanreversion information in kline. Old unsigned volume selector differs but research novelty outside narrow source scope UNKNOWN.',
        next='Separate complete-source extraction protocol required before forecasting; no new model recipe/parameter search or current STOP reopening')
    assert proof['elapsed_seconds']<120 and sum(p.stat().st_size for p in output.iterdir())<16000000
    save(output/'SOURCE_PREFLIGHT.json',proof)
    print(json.dumps({k:v for k,v in proof.items() if k!='source'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
