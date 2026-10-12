"""Recover only the pre-fixed continuous price/rate path from public Git objects."""
import argparse,hashlib,importlib.util,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from core import DAY,SYMBOLS
from reference import save,sha
npth=ROOT/'research/short-native-activity-20261012';sys.path.insert(0,str(npth))
spec=importlib.util.spec_from_file_location('native_source_api',npth/'run.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);b=native.bridge
cpth=ROOT/'research/composite-mark-replay-20261011';sys.path.insert(0,str(cpth))
from composite_bars import composite_bars
from replay import phase

def verify():
    for line in (HERE/'NATIVE_SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p

def build(state,source,expected=None):
    assert not state.exists() and not b.git('status','--porcelain')
    if not expected:assert b.git('rev-parse','HEAD').decode().strip()==source
    verify();state.mkdir();(state/'months').mkdir();started=time.monotonic();b.configure(state,'REUSE_2021_JAN_NOV');proto=json.loads((HERE/'PROTOCOL.json').read_text());start,end=map(native.utc,proto['native_calendar']);d=np.arange(start,end,DAY)
    with np.load(ROOT/proto['source']['daily_cube'],allow_pickle=False) as z:t=z['close_available_us'];price=z['close']
    tp={};mp={};cert=[]
    for name in ('Y2021','Q12022','Q22022'):
        p,c=phase(proto['source']['trade_commit'],b.TRADE,name);tp.update({(r['source']['month'],r['source']['symbol']):r for r in p['sources']});cert.append(dict(domain='klines',phase=name,**c))
    for name in ('REUSE_2021_JAN_NOV','DEC2021','Q12022','Q22022'):
        p,c=phase(proto['source']['mark_commit'],b.MARK,name);mp.update({(r['source']['month'],r['source']['symbol']):r for r in p['sources']});cert.append(dict(domain='markPriceKlines',phase=name,**c))
    inv,*_=b.inventories();reader=b.SourceReader(inv,state,local=False);records=[];daily=[];previous={}
    from modules.collector_research.pipeline.normalize import month_limits
    months=pd.period_range('2021-04','2022-06',freq='M')
    for month in months:
        stamp=str(month);left,right=month_limits(month.year,month.month);arrays=dict(times=np.arange(left*1000,right*1000,60_000_000,dtype=np.int64));sr=[]
        for asset,s in enumerate(SYMBOLS):
            tr,mr=tp[stamp,s],mp[stamp,s];domain={}
            for record,family in ((tr,'klines'),(mr,'markPriceKlines')):
                row=dict(record['source']);row.setdefault('source_period',row['month'])
                # Older monthly trade descriptors lack this redundant key;
                # official URL/month/checksum still bind the exact same body.
                companions=[r for r in inv['reusable_price_archives'] if r['symbol']==s and r['family']==family and r['month']==stamp and r['frequency']=='daily']
                bars,frame=composite_bars(reader,row,left,right,companions)
                assert len(bars.open_us)==len(arrays['times']) and np.array_equal(bars.open_us,arrays['times']) and not len(bars.provenance['missing_open_ms'])
                assert record['past_boundary']['available_us']==left*1000
                if (s,family) in previous:assert record['past_boundary']['close']==previous[s,family],'Actual previous-month source boundary'
                previous[s,family]=float(bars.values['close'][-1]);domain[family]=bars
                sr.append(dict(symbol=s,family=family,manifest_SHA256=bars.provenance['manifest_SHA256'],manifest=json.loads(bars.provenance['manifest_json']),observed_minutes=len(bars.open_us),source_owner_SHA256=hashlib.sha256(bars.provenance['minute_owner_index'].tobytes()).hexdigest(),source_support_SHA256=hashlib.sha256(bars.provenance['minute_support_bits'].tobytes()).hexdigest()))
            trade,mark=domain['klines'],domain['markPriceKlines']
            for key in ('open','close','quote_volume'):arrays[s+'_'+key]=trade.values[key]
            arrays[s+'_mark']=mark.values['close']
            for at in range(left*1000,right*1000,DAY):
                idx=(at-left*1000)//60_000_000;actual=float(tr['past_boundary']['close']) if idx==0 else float(trade.values['close'][idx-1]);k=int(np.searchsorted(t,at));assert k<len(t) and t[k]==at
                assert abs(price[k,asset]-actual)<=1e-12*abs(actual),'True daily risk close vs complete minute source'
                daily.append(dict(symbol=s,close_us=at,close=actual))
            del frame,domain,trade,mark,bars
        dest=state/'months'/(stamp+'.npz');np.savez_compressed(dest,**arrays);records.append(dict(month=stamp,source_NPZ_SHA256=sha(dest),source_NPZ_bytes=dest.stat().st_size,minutes=len(arrays['times']),sources=sr));del arrays
        print('CONTINUOUS_SOURCE_MONTH_VERIFIED',stamp,len(records),15,flush=True);assert time.monotonic()-started<180
    # Same reader/year wrapper reused for original actual2021 funding members.
    yi=json.loads(b.git('show','94fe13c494c82bb6e6868e6614eb7298fb15b3c3:research/core5-2021-economic-data/Y2021/INDEX.json'));ym={r['name']:r for r in yi['members']};year=reader.wrapper('Y2021')
    spec=importlib.util.spec_from_file_location('actual_rate_source',ROOT/'research/short-funding-residual-20261011/experiment.py');fund=importlib.util.module_from_spec(spec);spec.loader.exec_module(fund);raw=fund.source_archive(ROOT,state);events=[];fundproof=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        for s in SYMBOLS:
            name='derived/economics/'+s+'_funding_events.parquet';old=year.read(name);assert hashlib.sha256(old).hexdigest()==ym[name]['SHA256']
            name2='source_tables_not_model_inputs/economics/'+s+'_funding_events.parquet';recent=z.read(name2);assert hashlib.sha256(recent).hexdigest()==members[name2]['SHA256']
            columns=['calc_time_ms','last_funding_rate','funding_interval_hours']
            past=pq.read_table(io.BytesIO(old),columns=columns,filters=[('calc_time_ms','>=',start//1000),('calc_time_ms','<',min(end,native.utc('2022-01-01'))//1000)]).to_pandas()
            new=pq.read_table(io.BytesIO(recent),columns=columns,filters=[('calc_time_ms','>=',native.utc('2022-01-01')//1000),('calc_time_ms','<',end//1000)]).to_pandas()
            f=pd.concat([past,new],ignore_index=True).sort_values('calc_time_ms');ts=f.calc_time_ms.to_numpy(np.int64)*1000;hours=f.funding_interval_hours.to_numpy(float)
            assert len(f)==456*3 and not f.calc_time_ms.duplicated().any() and np.isfinite(f.to_numpy()).all() and ts[0]>=start and ts[-1]<end
            delta=np.diff(ts);assert ((np.abs(delta-hours[:-1]*3600000000)<=1000000)|(np.abs(delta-hours[1:]*3600000000)<=1000000)).all(),'Actual fund coverage/spacing'
            for r in f.itertuples(index=False):events.append(dict(symbol=s,event_us=int(r.calc_time_ms)*1000,raw_rate=float(r.last_funding_rate),reported_interval_hours=float(r.funding_interval_hours)))
            fundproof.append(dict(symbol=s,events=len(f),actual2021_member_SHA256=hashlib.sha256(old).hexdigest(),actual2022_member_SHA256=hashlib.sha256(recent).hexdigest()))
    reader.close();events.sort(key=lambda r:(r['event_us'],r['symbol']));save(state/'EVENTS.json',events);save(state/'DAILY.json',daily)
    report=dict(status='PASS_EXACT_FIXED456DAY_CONTINUOUS_SOURCE',science_source_commit=source,calendar=[start,end],days=456,minutes_per_asset=456*1440,symbol_order=list(SYMBOLS),months=records,source_certificates=cert,funding=fundproof,funding_events=len(events),daily_price_parity=True,provider_downloads=0,new_models=0,new_wallets=0,native_authority='CONDITIONAL_RAWFRACTION_PRIOR_MARK_ASSUMED_MMR_FEE_ARRIVAL_NOT_NATIVE_CERTIFIED')
    report['files']={name:dict(SHA256=sha(state/name),bytes=(state/name).stat().st_size) for name in ('EVENTS.json','DAILY.json')}
    save(state/'SOURCE_INDEX.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-started));assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<2_000_000_000
    if expected:
        old=json.loads(b.git('show',expected+':research/cs-continuous-economics-20261012/source-result/SOURCE_INDEX.json'));assert report==old,'Exact public source proof restoration'
        save(state/'PUBLIC_SOURCE_RESTORE.json',dict(status='PASS_EXACT_PUBLIC456DAY_SOURCE_PROOF',artifact_commit=expected,provider_downloads=0,new_models=0,new_wallets=0))
    print('CONTINUOUS_SOURCE_READY',456,456*1440,len(events),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();build(a.state,a.source_commit,a.expected_commit)
