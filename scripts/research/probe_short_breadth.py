"""One frozen, read-only conditional SHORT-information probe; not a wallet."""
import argparse, hashlib, json, os, resource, shutil, time
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import polars as pl

DAY=86_400_000_000
COLS=['dt','symbol','close','decision_available_at','feature_ready','mom20','dist50','sma_signal']

def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def panel_features(close, ready, minimum_peers=4):
    """Read-only adapter of existing breadth20, excluding self and unready peers."""
    n,a=close.shape; mom=np.full_like(close,np.nan); own50=np.full_like(close,np.nan)
    sma=np.full_like(close,np.nan)
    for i in range(n):
        for length,out in ((20,mom),(49,own50),(199,sma)):
            if i<length: continue
            z=close[i-length:i+1]; valid=np.isfinite(z).all(0)&(z>0).all(0)
            value=close[i]/z[0]-1 if length==20 else close[i]/z.mean(0)-1
            out[i,valid]=value[valid]
    peers=ready&np.isfinite(mom); pos=peers&(mom>0)
    count=peers.sum(1)[:,None]-peers.astype(int)
    up=pos.sum(1)[:,None]-pos.astype(int)
    breadth=np.divide(up,count,out=np.full_like(close,np.nan),where=count>=minimum_peers)
    return dict(mom20=mom,distance50=own50,sma_signal=np.sign(sma),breadth=breadth,peer_count=count)

def forward_short(close,horizon,cost):
    label=np.full_like(close,np.nan)
    for i in range(len(close)-horizon):
        valid=np.isfinite(close[i:i+horizon+1]).all(0)&(close[i:i+horizon+1]>0).all(0)
        label[i,valid]=1-close[i+horizon,valid]/close[i,valid]-cost
    return label

def group_metric(y,mask):
    observations=np.where(mask,y,np.nan); dates=np.any(np.isfinite(observations),1)
    sums=np.nansum(observations,1); counts=np.isfinite(observations).sum(1)
    daily=np.divide(sums,counts,out=np.full(len(y),np.nan),where=counts>0)
    values=daily[dates]
    return dict(asset_labels=int(np.isfinite(observations).sum()),distinct_market_blocks=int(dates.sum()),
        mean_short_price_edge_after_roundtrip=float(values.mean()) if len(values) else None,
        median_short_price_edge_after_roundtrip=float(np.median(values)) if len(values) else None,
        positive_market_block_fraction=float(np.mean(values>0)) if len(values) else None,
        market_block_edges=[None if not np.isfinite(v) else float(v) for v in daily])

def contrast(y,base,breadth):
    down=group_metric(y,base&(breadth<.5)); up=group_metric(y,base&(breadth>=.5))
    a=down['mean_short_price_edge_after_roundtrip']; b=up['mean_short_price_edge_after_roundtrip']
    return dict(broad_down=down,broad_up_or_tie=up,spread=None if a is None or b is None else a-b)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    began=time.monotonic();p=json.loads(a.protocol.read_bytes());out=a.output.resolve()
    assert os.uname().sysname=='Linux' and str(out).startswith('/home/ubuntu/coin/execution-state/') and not out.exists()
    assert shutil.disk_usage(out.parent).free>=p['budget']['reserve_bytes']
    manifest_path=Path(p['manifest']['path']); assert sha(manifest_path)==p['manifest']['sha256']
    manifest=json.loads(manifest_path.read_bytes()); assert manifest['source_manifest_sha256']==p['source_manifest_sha256']
    assert sha(Path(p['source_manifest_path']))==p['source_manifest_sha256']
    assert manifest['scenario']=='raw_fraction'
    symbols=p['symbols']; assert [r['symbol'] for r in manifest['files']]==symbols
    frames=[]; refs=[]; dates=None; coverage=[]
    for k,ref in enumerate(manifest['files']):
        path=Path(ref['path']).resolve(); assert path.parent==manifest_path.parent.resolve() and sha(path)==ref['sha256']
        f=pl.read_parquet(path,columns=COLS).sort('dt'); dt=f['dt'].dt.epoch('us').to_numpy()
        available=f['decision_available_at'].dt.epoch('us').to_numpy()
        assert dt.max()<p['locked_start_us'] and np.all(available==dt+DAY)
        assert len(dt)==len(np.unique(dt)) and np.all(np.diff(dt)==DAY)
        assert f['symbol'].eq(ref['symbol']).all()
        if dates is None: dates=dt
        else: assert np.array_equal(dates,dt), 'One common development calendar'
        ready=f['feature_ready'].to_numpy(); close=f['close'].to_numpy()
        for i in np.flatnonzero(ready):
            assert i>=255 and np.isfinite(close[i-255:i+1]).all() and (close[i-255:i+1]>0).all()
        coverage.append(dict(symbol=ref['symbol'],observed_days=int(np.isfinite(close).sum()),ready_days=int(ready.sum()),
            first_ready_us=int(available[np.flatnonzero(ready)[0]]) if ready.any() else None))
        frames.append(f);refs.append(dict(path=str(path),sha256=ref['sha256'],bytes=path.stat().st_size))
        print(f'[DATA] {k+1}/{len(symbols)} {ref["symbol"]}',flush=True)
    close=np.column_stack([f['close'].to_numpy() for f in frames]); ready=np.column_stack([f['feature_ready'].to_numpy() for f in frames])
    feature=panel_features(close,ready,p['minimum_peers']); errors={}
    for cache,key in (('mom20','mom20'),('dist50','distance50'),('sma_signal','sma_signal')):
        original=np.column_stack([f[cache].to_numpy() for f in frames]); valid=ready&np.isfinite(original)
        err=float(np.max(np.abs(original[valid]-feature[key][valid]))); assert err<1e-9
        errors[cache]=err
    # Every block uses a completed close; execution at this exact close is NOT assumed.
    decisions=dates+DAY; ix=np.flatnonzero((decisions>=p['anchor_us'])&((decisions-p['anchor_us'])%(p['horizon_days']*DAY)==0)&(decisions+p['horizon_days']*DAY<=p['locked_start_us']))
    h=p['horizon_days']; assert np.all(np.diff(decisions[ix])==h*DAY)
    labels=forward_short(close,h,p['roundtrip_price_cost']); y=labels[ix]
    usable=ready[ix]&np.isfinite(y)&np.isfinite(feature['breadth'][ix])
    short=usable&(feature['sma_signal'][ix]<0)
    own50=short&(feature['distance50'][ix]<0)
    breadth=feature['breadth'][ix]; primary=contrast(y,own50,breadth)
    print('[FEATURES/LABELS] 1/1 causal features and nonoverlap30d labels',flush=True)
    eras={}; era_masks=[]
    for name,start,end in p['eras']:
        era=(decisions[ix]>=start)&(decisions[ix]<end);era_masks.append(era)
        eras[name]=dict(own50=group_metric(y[era],own50[era]),conditioned=contrast(y[era],own50[era],breadth[era]))
    yearly={}
    for year in range(2022,2027):
        mask=np.array([datetime.fromtimestamp(int(t)/1e6,UTC).year==year for t in decisions[ix]])
        if mask.any():yearly[str(year)]=contrast(y[mask],own50[mask],breadth[mask])
    rng=np.random.default_rng(p['seed']);scores=[]
    for repeat in range(p['placebo_replicates']):
        fake=breadth.copy()
        for era in era_masks:
            rows=np.flatnonzero(era);fake[rows]=breadth[rng.permutation(rows)]
        metric=contrast(y,own50,fake); scores.append(metric['spread'])
        if (repeat+1)%16==0:print(f'[PLACEBO] {repeat+1}/{p["placebo_replicates"]}',flush=True)
    values=[v for v in scores if v is not None]; assert len(values)==p['placebo_replicates']
    lag=np.full_like(breadth,np.nan);lag[2:]=breadth[:-2]
    lagged=contrast(y,own50&np.isfinite(lag),lag)
    checks=dict(pooled_spread_at_least_2pct=primary['spread'] is not None and primary['spread']>=.02,
        spread_gt_joint_date_shuffle95=primary['spread'] is not None and primary['spread']>float(np.quantile(values,.95)),
        each_era_positive_spread=all(v['conditioned']['spread'] is not None and v['conditioned']['spread']>0 for v in eras.values()),
        each_era_positive_retained_short_edge=all(v['conditioned']['broad_down']['mean_short_price_edge_after_roundtrip'] is not None and v['conditioned']['broad_down']['mean_short_price_edge_after_roundtrip']>0 for v in eras.values()),
        each_state_each_era_at_least4blocks=all(v['conditioned'][s]['distinct_market_blocks']>=4 for v in eras.values() for s in ('broad_down','broad_up_or_tie')))
    records=[]
    for j,i in enumerate(ix):
        for k,symbol in enumerate(symbols):
            valid=bool(usable[j,k]); reason='ELIGIBLE' if valid else 'NO_READY_HISTORY' if not ready[i,k] else 'FUTURE_PATH_GAP_OR_INCOMPLETE' if not np.isfinite(y[j,k]) else 'INSUFFICIENT_READY_PEERS'
            val=lambda v:float(v) if np.isfinite(v) else None
            records.append(dict(symbol=symbol,decision_us=int(decisions[i]),feature_available_us=int(decisions[i]),label_end_us=int(decisions[i]+h*DAY),
                eligibility=reason,sma_signal=val(feature['sma_signal'][i,k]),own_distance50=val(feature['distance50'][i,k]),
                peer_count=int(feature['peer_count'][i,k]),breadth20_ex_self=val(breadth[j,k]),short_price_cost_proxy=val(y[j,k])))
    assert time.monotonic()-began<p['budget']['wall_seconds'] and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<p['budget']['RAM_bytes']
    result=dict(status='COMPLETE_READ_ONLY_BREADTH_SHORT_INFORMATION_PROBE',created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(__file__),protocol_sha256=sha(a.protocol),
        protocol=p,inputs=refs,coverage=coverage,cached_feature_scalar_max_errors=errors,nonoverlap_market_blocks=len(ix),
        all_negative_SMA200=group_metric(y,short),own50_reference=group_metric(y,own50),primary=primary,era_results=eras,year_results=yearly,
        lag60d=lagged,shuffle=dict(scores=values,percentile95=float(np.quantile(values,.95)),empirical_upper_tail=(1+sum(v>=primary['spread'] for v in values))/(1+len(values)) if primary['spread'] is not None else None,
            scope='Noncausal diagnostic, joint date vectors within era; not a deployable strategy or exact independence test'),
        checks=checks,decision='REGISTER_ONE_SHARED_WALLET_CONFIRMATION' if all(checks.values()) else 'DO_NOT_RUN_NEW_CONTROLLER_OR_ACCOUNT_FROM_THIS_FACTOR',
        observations=records,new_models_fit=0,new_accounts=0,locked_consumed=False,qualification='NONE_CASH',
        elapsed_seconds=time.monotonic()-began,peak_process_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        limitations=['Fixed retrospective ten-symbol panel; not a point-in-time whole-market universe',
            'Seen development; 30d nonoverlap labels still share serial regimes and correlated assets',
            'Complete-close price proxy minus27bp only; funding, intraday risk, sizing and real execution NOT included',
            'No portfolio NAV/return/Sharpe/APR; means weight each market block equally, never sum independent accounts',
            'Past breadth was already in old models; this is conditional interpretation, not a novel feature claim'])
    out.mkdir();(out/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'],checks=checks,decision=result['decision'],spread=primary['spread'])),flush=True)

if __name__=='__main__':main()
