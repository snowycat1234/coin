"""Explicit v3 supplementary data release; original formal v2 N/E never changes.

Recover actual June29 mark/premium minutes from verified official daily archives.
Admit only the three preregistered June24 funding estimates in separate workdirs.
"""
import argparse,json,os,platform,sys
from pathlib import Path
import numpy as np
import pandas as pd
from modules.transformer_v2.train import atomic,sha
from modules.transformer_v2.locked_data import actual_funding_coverage
from .funding_bridge import SCENARIOS

START=pd.Timestamp('2026-03-01',tz='UTC');END=pd.Timestamp('2026-09-01',tz='UTC')
RECOVERY_DAY=pd.Timestamp('2026-06-29',tz='UTC');EVENT_MS=1782273600000
GAPS=('WIFUSDT','1000SATSUSDT','ORDIUSDT')

def require_freeze(state):
    path=Path(state)/'LOCKED_DEVELOPMENT_FREEZE.json';release=json.loads(path.read_text())
    if release['status']!='FROZEN_DEVELOPMENT_WEIGHTS_AND_RISK_BEFORE_LOCKED_ECONOMICS' or release['funding_bridges']!=list(SCENARIOS):raise ValueError('Complete frozen development release required')
    proto=Path(__file__).resolve().parents[2]/'reports/transformer_v3/TRANSFORMER_V3_PROTOCOL.json'
    if sha(proto)!=release['protocol_sha256']:raise ValueError('Frozen development protocol changed')
    for e in release['frozen_weights_and_scalers']:
        if sha(e['path'])!=e['sha256']:raise ValueError('Frozen development weight/scaler changed')
    return path,release

def write_table(frame,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp.parquet')
    frame.to_parquet(temp,index=False,compression='zstd');temp.replace(path)

def link_file(source,destination):
    source=Path(source).resolve();destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        if destination.resolve()!=source:raise ValueError('Existing linked source identity changed')
    else:destination.symlink_to(source)

def merge_recovered_day(original,recovered):
    if len(recovered)!=1440 or not np.array_equal(recovered.timestamp_ms.to_numpy(),np.arange(RECOVERY_DAY.value//1_000_000,(RECOVERY_DAY+pd.Timedelta(days=1)).value//1_000_000,60000)):
        raise ValueError('Exactly1440 actual recovered June29 minutes required')
    common=np.intersect1d(original.timestamp_ms,recovered.timestamp_ms)
    if len(common):
        cols=['open','high','low','close']
        a=original.set_index('timestamp_ms').loc[common,cols].to_numpy();b=recovered.set_index('timestamp_ms').loc[common,cols].to_numpy()
        if not np.array_equal(a,b):raise ValueError('Official monthly/daily source conflict; do not silently pick an outcome')
    result=pd.concat([original,recovered.loc[~recovered.timestamp_ms.isin(original.timestamp_ms)]],ignore_index=True).sort_values('timestamp_ms').reset_index(drop=True)
    if result.timestamp_ms.duplicated().any():raise ValueError('Duplicate recovered minute')
    return result

def insert_estimated_event(events,row):
    if row['symbol'] not in GAPS or row['event_us']!=EVENT_MS*1000 or row['scenario'] not in SCENARIOS or row['exact_Binance_settlement']:
        raise ValueError('Only frozen imputed event allowed')
    if ((events.calc_time_ms-EVENT_MS).abs()<1000).any():raise ValueError('An actual exact event exists; do not substitute an estimate')
    frame=events.copy();frame['event_source_role']='OFFICIAL_ARCHIVE_RATE_UNIT_UNCONFIRMED';frame['event_observed']=True
    value={c:np.nan for c in frame.columns}
    value.update(symbol=row['symbol'],calc_time_ms=EVENT_MS,funding_interval_hours=4,last_funding_rate=row['engine_raw_rate'],raw_rate_unit='UNCONFIRMED',
                 event_source_role=row['role']+':'+row['scenario'],event_observed=False)
    frame=pd.concat([frame,pd.DataFrame([value])],ignore_index=True).sort_values('calc_time_ms').reset_index(drop=True)
    frame['calc_time_ms']=frame.calc_time_ms.astype('int64');frame['funding_interval_hours']=frame.funding_interval_hours.astype('int64')
    if frame.calc_time_ms.duplicated().any():raise ValueError('Duplicate funding event')
    return frame

def prepare_base(state,v2,collector_root,development_work,source_run):
    state=Path(state);v2=Path(v2);manifest=json.loads((v2/'LOCKED_DATA_MANIFEST.json').read_text());original=Path(manifest['work'])/'data/normalized'
    work=state/'bridge-base-work';base=work/'data/normalized';receipt=state/'BRIDGE_BASE_MANIFEST.json'
    # Configure even on resume: cached base does not mean normalizer modules have
    # been imported in this fresh process before the next incomplete scenario.
    binding=json.loads(Path(source_run,'BINDING.json').read_text());os.environ.update(binding['config'])
    os.environ.update(WORK_DIR=str(development_work),CONFIG_FILE=str(Path(collector_root)/'config.env'));sys.path.insert(0,str(collector_root))
    if receipt.exists():
        saved=json.loads(receipt.read_text())
        for e in saved['artifacts']:
            if sha(e['path'])!=e['sha256']:raise ValueError('Protected supplementary base changed')
        return saved
    for e in manifest['artifacts']:
        if sha(e['path'])!=e['sha256']:raise ValueError('Original formal data changed')
    from pipeline import normalize as norm,download
    symbols=json.loads((Path(__file__).resolve().parents[2]/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json').read_text())['data']['symbols']
    artifacts=[];recovery=[];daily_by_symbol={}
    for e in manifest['artifacts']:
        source=Path(e['path']);relative=source.relative_to(original)
        patch=source.name.endswith(('_daily.parquet','_funding_events.parquet')) or source.name=='2026-06.parquet' and relative.parts[-2] in ('markPriceKlines','premiumIndexKlines')
        if not patch:link_file(source,base/relative)
    for symbol in symbols:
        daily=pd.read_parquet(original/(symbol+'_daily.parquet'))
        for family in ('markPriceKlines','premiumIndexKlines'):
            archive=v2/'gap-source-work/data/raw'/family/symbol/(symbol+'-1m-2026-06-29.zip')
            proof=download.verify_local(archive);raw=norm.numeric_csv(archive)
            day_ms=RECOVERY_DAY.value//1_000_000
            raw,duplicates=norm.validate_price(raw,family,day_ms,day_ms+86400000)
            recovered=norm.canonical(raw,family,symbol)
            source=original/'minute'/symbol/family/'2026-06.parquet';merged=merge_recovered_day(pd.read_parquet(source),recovered)
            dest=base/'minute'/symbol/family/'2026-06.parquet';write_table(merged,dest)
            aggregate=norm.aggregate_price(recovered,family).loc[RECOVERY_DAY]
            if not aggregate['complete']:raise ValueError('Recovered exact market day incomplete')
            which=daily.dt.eq(RECOVERY_DAY)
            if which.sum()!=1:raise ValueError('Causal daily calendar changed')
            daily.loc[which,'mark' if family=='markPriceKlines' else 'premium']=aggregate['close']
            daily.loc[which,'complete_mark' if family=='markPriceKlines' else 'complete_premium']=True
            recovery.append(dict(symbol=symbol,family=family,date='2026-06-29',source_path=str(archive),source_sha256=sha(archive),proof=proof,
                                 actual_minutes=1440,identical_duplicates_removed=duplicates,output_sha256=sha(dest),role='EXACT_OFFICIAL_DAILY_PRICE_RECOVERY'))
        funds=pd.read_parquet(original/(symbol+'_funding_events.parquet'))
        marks=pd.concat([pd.read_parquet(Path(development_work)/'data/normalized/minute'/symbol/'markPriceKlines/2026-02.parquet').tail(2)]+
                        [pd.read_parquet(base/'minute'/symbol/'markPriceKlines'/f'2026-{m:02d}.parquet') for m in range(3,9)],ignore_index=True).sort_values('available_us')
        mask=(funds.calc_time_ms*1000>=START.value//1000)&(funds.calc_time_ms*1000<END.value//1000)
        recalculated=norm.mark_funding(funds.loc[mask],marks)
        funds.loc[mask,recalculated.columns]=recalculated.to_numpy()
        write_table(funds,base/(symbol+'_funding_events.parquet'));write_table(daily,base/(symbol+'_daily.parquet'))
        daily_by_symbol[symbol]=daily
    for path in base.rglob('*.parquet'):artifacts.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size))
    saved=dict(status='EXACT_MARK_PREMIUM_RECOVERY_FUNDING_ESTIMATES_NOT_YET_ADMITTED',work=str(work),artifacts=artifacts,recovery=recovery,
               original_formal_manifest_sha256=sha(v2/'LOCKED_DATA_MANIFEST.json'),original_formal_N_E_sha256=sha(v2/'TRANSFORMER_V2_LOCKED_RESULTS.json'),
               source_sha256=sha(__file__),protected_original_modified=False,no_model_or_portfolio_result=True)
    atomic(receipt,saved);return saved

def prepare_scenario(state,base_manifest,scenario,scale,collector_root,source_run):
    state=Path(state);base=Path(base_manifest['work'])/'data/normalized';tag='raw_fraction' if scale==1. else 'raw_percent'
    work=state/'bridge-work'/scenario/tag;dest=work/'data/normalized';path=work/'INPUT_MANIFEST.json'
    if path.exists():
        saved=json.loads(path.read_text())
        for e in saved['artifacts']:
            if sha(e['path'])!=e['sha256']:raise ValueError('Admitted bridge data changed')
        return saved
    if scenario not in SCENARIOS or scale not in (1.,.01):raise ValueError('Only preregistered bridge and funding interpretation')
    prereg=json.loads((state/'LOCKED_BRIDGE_PREREGISTRATION.json').read_text());rows=[r for r in prereg['rows'] if r['scenario']==scenario and r['funding_scale']==scale]
    if len(rows)!=3:raise ValueError('Exactly three frozen estimates required')
    from pipeline import normalize as norm
    for p in base.rglob('*.parquet'):
        if not p.name.endswith(('_daily.parquet','_funding_events.parquet')):link_file(p,dest/p.relative_to(base))
    symbols=[p.name.removesuffix('_daily.parquet') for p in base.glob('*_daily.parquet')];audits=[];artifacts=[]
    for symbol in symbols:
        events=pd.read_parquet(base/(symbol+'_funding_events.parquet'));daily=pd.read_parquet(base/(symbol+'_daily.parquet'))
        row=next((r for r in rows if r['symbol']==symbol),None)
        if row:
            events=insert_estimated_event(events,row)
            marks=pd.read_parquet(base/'minute'/symbol/'markPriceKlines/2026-06.parquet')
            synthetic=norm.mark_funding(events.loc[events.calc_time_ms.eq(EVENT_MS)],marks)
            events.loc[events.calc_time_ms.eq(EVENT_MS),synthetic.columns]=synthetic.to_numpy()
        else:events['event_source_role']='OFFICIAL_ARCHIVE_RATE_UNIT_UNCONFIRMED';events['event_observed']=True
        days=pd.DatetimeIndex(daily.dt);windows=norm.funding_windows(events,days)
        for col in windows:daily[col]=windows[col].to_numpy()
        daily['funding_calendar_role']='ASSUMED_COMPLETE_WITH_PREREGISTERED_ESTIMATE' if row else 'ORIGINAL_OBSERVED_EVENT_CALENDAR'
        locked=daily.loc[(daily.dt>=START)&(daily.dt<END)]
        complete=locked[['complete_kline','complete_mark','complete_premium','complete_funding']].all(axis=1)
        coverage=actual_funding_coverage(events)
        if len(locked)!=184 or not complete.all() or not coverage:raise ValueError('Bridge must preserve all184 real execution/feature days; other gaps cannot be imputed')
        audits.append(dict(symbol=symbol,complete_conditional_days=int(complete.sum()),required_days=184,actual_event_exactness=False if row else True,
                           funding_calendar_complete_under_assumed_event=coverage,inserted_estimates=1 if row else 0))
        write_table(events,dest/(symbol+'_funding_events.parquet'));write_table(daily,dest/(symbol+'_daily.parquet'))
    for p in dest.rglob('*.parquet'):artifacts.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size))
    saved=dict(status='IMPUTED184DAY_INPUT_CALENDAR_READY',work=str(work),scenario=scenario,funding_scale=scale,artifacts=artifacts,audit=audits,estimates=rows,
               exact_funding_recovered=False,no_settlement_confirmation=False,source_sha256=sha(__file__),preregistration_sha256=sha(state/'LOCKED_BRIDGE_PREREGISTRATION.json'),
               recovered_price_base_sha256=sha(state/'BRIDGE_BASE_MANIFEST.json'),original_v2_formal_N_E_unchanged=True,no_future_training_labels=True)
    atomic(path,saved);return saved

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--v2-state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);a=p.parse_args()
    if platform.system()!='Linux' or os.environ.get('WSL_DISTRO_NAME'):raise RuntimeError('Independent Linux server only')
    require_freeze(a.state);base=prepare_base(a.state,a.v2_state,a.collector_root,a.work,a.source_run)
    results=[]
    for scenario in SCENARIOS:
        for scale in (1.,.01):results.append(prepare_scenario(a.state,base,scenario,scale,a.collector_root,a.source_run))
    atomic(Path(a.state)/'BRIDGE_INPUTS.json',dict(scenarios=results,total=10,all_five_registered_bridges=True,original_formal_v2_N_E_preserved=True))
    print('BRIDGE INPUTS10/10; all184 real market days, exactly3 estimates each',flush=True)

if __name__=='__main__':main()
