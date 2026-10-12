"""Small official archive page discovery; no prices, outcomes or credentials."""
import argparse,hashlib,json,re,time
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests
HERE=Path(__file__).resolve().parent
def discover(state):
 assert not state.exists();state.mkdir(parents=True);p=json.loads((HERE/'DIRECTORY_PROTOCOL.json').read_text());budget=p['directory_budget'];rows=[];total=0
 def get(url):
  nonlocal total
  assert len(rows)<budget['new_GETs']
  assert urlparse(url).netloc=='data.binance.vision','Only the official public landing/static page in discovery'
  began=time.monotonic();r=requests.get(url,timeout=budget['timeout_seconds'],stream=True);r.raise_for_status();raw=bytearray()
  for chunk in r.iter_content(8192):
   raw.extend(chunk);assert len(raw)<=budget['single_body_bytes'] and total+len(raw)<=budget['total_body_bytes']
  body=bytes(raw);total+=len(body);name=f'PAGE_{len(rows):02d}.txt';(state/name).write_bytes(body)
  rows.append(dict(url=url,actual_URL=r.url,status=r.status_code,bytes=len(body),SHA256=hashlib.sha256(body).hexdigest(),file=name,response_headers={k:v for k,v in r.headers.items() if k.lower() in ('date','last-modified','etag','content-type','content-length')},seconds=time.monotonic()-began));return body.decode('utf-8')
 landing=get('https://data.binance.vision/')
 for src in re.findall(r'<script[^>]*src=["\']([^"\']+)',landing):
  url=urljoin('https://data.binance.vision/',src)
  if urlparse(url).netloc=='data.binance.vision':get(url)
 out=dict(status='PASS_OFFICIAL_PAGE_ONLY_ENDPOINT_DISCOVERY',selection_available_UTC=p['fixed_selection_available_UTC'],requests=rows,total_bytes=total,new_price_ZIPs=0,new_fits=0,new_wallets=0,fetched_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 (state/'DISCOVERY.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print('OFFICIAL_ARCHIVE_DISCOVERY',len(rows),total,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);a=p.parse_args();discover(a.state)
