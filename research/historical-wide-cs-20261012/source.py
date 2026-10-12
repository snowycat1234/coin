"""Bounded historical 1d archive intake; existing checksum/CSV parsers reused."""
import argparse,concurrent.futures,hashlib,json,math,os,re,threading,time,xml.etree.ElementTree as ET,zipfile
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
import numpy as np
import pandas as pd
import requests
from modules.collector_research.pipeline.download import check_zip,parse_checksum
from modules.collector_research.pipeline.normalize import numeric_csv
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];NS={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
BUCKET='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision';BASE='https://data.binance.vision/'
CORE5=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');DAY=86400000000
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def protocol():return json.loads((HERE/'SOURCE_PROTOCOL.json').read_text())
def archive_key(symbol,period,daily=False):
 assert re.fullmatch('[A-Z0-9]{2,24}USDT',symbol)
 at=date.fromisoformat(period if daily else period+'-01');assert date(2022,8,1)<=at<date(2024,1,1),'Only admitted source2022Aug-2023Dec'
 return f'data/futures/um/{"daily" if daily else "monthly"}/klines/{symbol}/1d/{symbol}-1d-{period}.zip'
def frame(path,period,daily=False):
 with zipfile.ZipFile(path) as z:
  a=z.infolist();assert len(a)==1 and a[0].file_size<=protocol()['source_budget']['single_CSV_bytes']
 check_zip(path);f=numeric_csv(path);assert not f.timestamp_ms.duplicated().any();f=f.sort_values('timestamp_ms').reset_index(drop=True)
 left=int(pd.Timestamp(period if daily else period+'-01',tz='UTC').value//1000000);right=left+86400000 if daily else int((pd.Timestamp(period+'-01',tz='UTC')+pd.offsets.MonthBegin(1)).value//1000000)
 t=f.timestamp_ms.to_numpy(float);c=f.close_time_ms.to_numpy(float)
 assert np.equal(t,np.floor(t)).all() and ((t>=left)&(t<right)&(t%86400000==0)).all() and np.array_equal(c,t+86400000-1)
 assert (f[['open','high','low','close']]>0).all().all() and ((f.low<=f[['open','close']].min(axis=1))&(f.high>=f[['open','close']].max(axis=1))&(f.low<=f.high)).all()
 assert (f[['volume','quote_volume','trades','taker_buy_volume','taker_buy_quote_volume']]>=0).all().all() and np.equal(f.trades,np.floor(f.trades)).all()
 return f,bool(np.array_equal(t,np.arange(left,right,86400000)))

class Intake:
 def __init__(self,state):
  self.state=state;self.B=protocol()['source_budget'];self.started=time.monotonic();self.lock=threading.RLock();self.stop=threading.Event();self.local=threading.local();self.rows=[];self.count={'metadata':0,'archive':0};self.bytes={'metadata':0,'archive':0}
 def get(self,url,kind,limit):
  assert not self.stop.is_set() and time.monotonic()-self.started<self.B['phase_wall_seconds']
  assert url.startswith(BUCKET+'?') if kind=='metadata' else url.startswith(BASE+'data/futures/um/')
  with self.lock:
   self.count[kind]+=1;assert self.count[kind]<=self.B['metadata_GETs' if kind=='metadata' else 'archive_and_checksum_GETs']
  if not hasattr(self.local,'session'):
   self.local.session=requests.Session();self.local.session.auth=lambda request:request
  began=time.monotonic();raw=bytearray()
  try:
   with self.local.session.get(url,timeout=self.B['timeout_seconds'],stream=True,allow_redirects=False) as r:
    for chunk in r.iter_content(8192):raw.extend(chunk);assert len(raw)<=limit
    with self.lock:
     self.bytes[kind]+=len(raw);assert self.bytes[kind]<=self.B['metadata_bytes' if kind=='metadata' else 'archive_and_checksum_bytes'];row=dict(url=url,kind=kind,status=r.status_code,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest(),seconds=time.monotonic()-began,headers={k:v for k,v in r.headers.items() if k.lower() in ('date','last-modified','etag','content-length','content-type')});self.rows.append(row);save(self.state/'HTTP.json',self.rows)
    if r.status_code in (403,451,418,429):self.stop.set();raise PermissionError('Officialaccessblocked; noalternative orretry')
    r.raise_for_status();return bytes(raw),row
  except Exception:
   self.stop.set();raise
 def acquire(self,symbol,period,daily=False):
  key=archive_key(symbol,period,daily);p=self.state/'raw'/symbol/key.rsplit('/',1)[-1];directory=p.parent;directory.mkdir(parents=True,exist_ok=True)
  receipt=directory/(p.name+'.SOURCE.json');listing=directory/(p.name+'.LIST.xml')
  if receipt.exists():
   old=json.loads(receipt.read_text());assert old['key']==key and old['symbol']==symbol and old['period']==period and old['daily']==daily
   if 'path' in old:
    assert sha(p)==old['ZIP_SHA256'] and sha(Path(str(p)+'.CHECKSUM'))==old['CHECKSUM_SHA256'];f,complete=frame(p,period,daily);assert len(f)==old['rows'] and complete==old['full_period']
   assert sha(listing)==old['listing_SHA256'];return old
  url=BUCKET+'?'+urlencode({'prefix':key,'max-keys':4})
  if listing.exists():
   body=listing.read_bytes();http=next(r for r in reversed(self.rows) if r['url']==url and r['status']==200);assert hashlib.sha256(body).hexdigest()==http['SHA256']
  else:
   body,http=self.get(url,'metadata',self.B['single_metadata_bytes']);listing.write_bytes(body)
  assert b'<!DOCTYPE' not in body.upper() and b'<!ENTITY' not in body.upper();root=ET.fromstring(body);assert root.tag=='{'+NS['s']+'}ListBucketResult' and root.findtext('s:Name',namespaces=NS)=='data.binance.vision' and root.findtext('s:Prefix',namespaces=NS)==key and root.findtext('s:IsTruncated',namespaces=NS)=='false'
  items={a.findtext('s:Key',namespaces=NS):a for a in root.findall('s:Contents',NS)}
  if key not in items:
   absent=dict(symbol=symbol,period=period,daily=daily,status='UNKNOWN_ARCHIVE_ABSENT_FROM_CURRENT_OFFICIAL_LISTING',historical_nontradable=False,key=key,listing_SHA256=hashlib.sha256(body).hexdigest(),http=http);save(receipt,absent);return absent
  assert key+'.CHECKSUM' in items and set(items)<={key,key+'.CHECKSUM'};announced=int(items[key].findtext('s:Size',namespaces=NS));assert 0<announced<=self.B['single_ZIP_bytes']
  cp=Path(str(p)+'.CHECKSUM')
  if cp.exists():check=cp.read_bytes()
  else:check,ch=self.get(BASE+key+'.CHECKSUM','archive',4096);cp.write_bytes(check)
  expected=parse_checksum(check.decode('ascii'),p.name)
  if p.exists():raw=p.read_bytes();zh=next(r for r in reversed(self.rows) if r['url']==BASE+key and r['status']==200)
  else:raw,zh=self.get(BASE+key,'archive',self.B['single_ZIP_bytes']);p.write_bytes(raw)
  assert len(raw)==announced and hashlib.sha256(raw).hexdigest()==expected
  f,complete=frame(p,period,daily);out=dict(symbol=symbol,period=period,daily=daily,status='PASS_ACTUAL_1D_SOURCE' if complete else 'PARTIAL_ACTUAL_1D_SOURCE_RETAINED_NOT_NONTRADABILITY',key=key,path=str(p.relative_to(self.state)),ZIP_SHA256=expected,ZIP_bytes=len(raw),CHECKSUM_SHA256=hashlib.sha256(check).hexdigest(),listing_SHA256=hashlib.sha256(body).hexdigest(),object_LastModified=items[key].findtext('s:LastModified',namespaces=NS),retrieved_source_headers=zh['headers'],rows=len(f),full_period=complete,first_open_ms=int(f.timestamp_ms.iloc[0]),last_close_ms=int(f.close_time_ms.iloc[-1]),actual_quote_volume_USDT=math.fsum(f.quote_volume.to_list()),actual_trades=int(f.trades.sum()),archive_historical_arrival_certified=False)
  save(directory/(p.name+'.SOURCE.json'),out);return out

def select(state,inventory):
 assert not state.exists();state.mkdir(parents=True);P=protocol();names=json.loads(inventory.read_text())['symbols'];intake=Intake(state);records=[];ranks=[];unknown=[];checks=[]
 with concurrent.futures.ThreadPoolExecutor(P['source_budget']['network_threads']) as pool:
  jobs={pool.submit(intake.acquire,s,P['ranking_month']):s for s in names}
  for completed,job in enumerate(concurrent.futures.as_completed(jobs),1):
   r=job.result();records.append(r)
   if r['status']=='PASS_ACTUAL_1D_SOURCE':ranks.append(dict(symbol=r['symbol'],quote_volume_USDT=r['actual_quote_volume_USDT']))
   else:unknown.append(dict(symbol=r['symbol'],phase='OCTOBER_RANK',status=r['status'],not_evidence_of_nontradability=True))
   if completed%50==0:print('ACTUAL_PRE2023_CANDIDATE_SOURCE',completed,len(names),'rankable',len(ranks),'unknown',len(unknown),flush=True)
 assert len(ranks)<=P['source_budget']['maximum_October_present_archives'];ranks.sort(key=lambda r:(-r['quote_volume_USDT'],r['symbol']));by={(r['symbol'],r['period'],r['daily']):r for r in records};selected=[]
 for i,r in enumerate(ranks[:P['maximum_qualification_candidates']]):
  s=r['symbol'];parts=[]
  for period in P['qualification_months']:
   k=(s,period,False)
   if k not in by:by[k]=intake.acquire(s,period);records.append(by[k])
   parts.append(by[k])
  current=intake.acquire(s,P['presence_day'],True);records.append(current)
  good=all(q.get('full_period',False) for q in parts) and current.get('full_period',False) and current.get('actual_quote_volume_USDT',0)>0 and current.get('actual_trades',0)>0
  status='ELIGIBLE_92_ACTUAL_PRESELECTION_DAYS_AND_POSITIVE_PRESENCE' if good else 'UNKNOWN_PRESELECTION_HISTORY_OR_PRESENCE_NOT_NONTRADABLE';checks.append(dict(symbol=s,historical_liquidity_rank=i+1,status=status,source_periods=[q['period'] for q in parts]+[current['period']]))
  if good:selected.append(s)
  else:unknown.append(dict(symbol=s,phase='QUALIFICATION',status=status,not_evidence_of_nontradability=True))
  print('ACTUAL_PRE2023_POOL_QUALIFICATION',i+1,'selected',len(selected),s,status,flush=True)
  if len(selected)==P['desired_assets']:break
 out=dict(status='FROZEN_HISTORICAL_TOP20_WITH_ARCHIVE_COVERAGE_LIMITS' if len(selected)==20 else 'STOP_INSUFFICIENT_PRESELECTION_EVIDENCE',selection_available_UTC=P['selection_available_UTC'],ranking_month=P['ranking_month'],symbols=selected,full_candidate_archive_symbols=names,ranked_candidates=ranks,qualification_checks=checks,unknown_candidates=unknown,source_records=sorted(records,key=lambda r:(r['symbol'],r['period'],r['daily'])),full_historical_universe_certified=False,selection_complete_within_supplied_historical_universe=False,old_July_pool_used=False,current_exchangeInfo_used=False,new_fits=0,new_wallets=0,evaluation_price_payloads_read=0,HTTP_counts=intake.count,HTTP_body_bytes=intake.bytes,seconds=time.monotonic()-intake.started)
 save(state/'POOL.json',out);print('ACTUAL_PRE2023_FROZEN_POOL',out['status'],selected,intake.count,intake.bytes,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);a=p.parse_args();select(a.state,a.inventory)
