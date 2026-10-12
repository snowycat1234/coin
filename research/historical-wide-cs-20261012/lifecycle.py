"""Post-score archive metadata annotations only, never strategy inputs."""
import argparse,hashlib,json,re,time,xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
import requests
from source import HERE,BUCKET,NS,save
def run(state):
 assert not state.exists();state.mkdir(parents=True);names=['MATICUSDT','REEFUSDT','KLAYUSDT','EOSUSDT','LITUSDT'];records=[];total=0;session=requests.Session();session.auth=lambda r:r
 for s in names:
  prefix=f'data/futures/um/monthly/klines/{s}/1d/';url=BUCKET+'?'+urlencode({'prefix':prefix,'max-keys':1000});r=session.get(url,timeout=20);r.raise_for_status();assert len(r.content)<=262144;total+=len(r.content);assert total<=1048576;path=state/(s+'.xml');path.write_bytes(r.content);root=ET.fromstring(r.content);assert root.findtext('s:Prefix',namespaces=NS)==prefix and root.findtext('s:IsTruncated',namespaces=NS)=='false';months=[]
  for node in root.findall('s:Contents',NS):
   key=node.findtext('s:Key',namespaces=NS);match=re.fullmatch(re.escape(prefix+s+'-1d-')+r'(\d{4}-\d{2})\.zip',key)
   if match:months.append(match[1])
  records.append(dict(symbol=s,official_directory_URL=url,XML_SHA256=hashlib.sha256(r.content).hexdigest(),XML_bytes=len(r.content),first_archived_month=min(months),last_archived_month=max(months),archived_month_count=len(months),role='POSTSELECTION_POSTSCORE_METADATA_ONLY_NOT_FEATURE_OR_FILTER',archive_cessation_is_not_delisting_or_settlement_certificate=True,official_delisting_time_and_price='UNKNOWN_NOT_INFERRED_FROM_ABSENCE'))
 save(state/'LIFECYCLE.json',dict(status='PASS_OFFICIAL_ARCHIVE_LIFECYCLE_METADATA_SCOPE_ONLY',records=records,total_bytes=total,new_metadata_GETs=len(names),new_price_ZIPs=0,new_fits=0,new_scores=0,source_role='NO_PRICE_BODY_READ_CURRENT_METADATA_NOT_ASOF_INPUT',full_historical_universe_certified=False,complete_retirement_disposal_evidence=False));print('ACTUAL_LIFECYCLE_METADATA_ONLY',[(r['symbol'],r['last_archived_month']) for r in records],total,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);a=p.parse_args();run(a.state)
