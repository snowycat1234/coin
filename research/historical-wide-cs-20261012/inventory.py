"""Reuse the original official archive directory parser with bounded I/O."""
import argparse,hashlib,json,time
from pathlib import Path
import httpx
from scripts.investment import multi_asset_data as original
HERE=Path(__file__).resolve().parent
def run(state,discovery):
 assert not state.exists();state.mkdir(parents=True);prior=json.loads((discovery/'DISCOVERY.json').read_text());P=json.loads((HERE/'DIRECTORY_PROTOCOL.json').read_text());B=P['directory_budget'];html=(discovery/'PAGE_00.txt').read_bytes();assert hashlib.sha256(html).hexdigest()==prior['requests'][0]['SHA256'];assert original.BUCKET.encode() in html
 rows=[];total=prior['total_bytes'];began=time.monotonic()
 with httpx.Client(timeout=B['timeout_seconds'],follow_redirects=False) as network:
  def handler(request):
   nonlocal total
   if str(request.url)==original.INDEX:return httpx.Response(200,content=html,request=request)
   assert str(request.url).startswith(original.BUCKET+'?') and len(rows)+len(prior['requests'])<B['new_GETs'];raw=bytearray();start=time.monotonic()
   with network.stream('GET',str(request.url)) as r:
    for chunk in r.iter_bytes():
     raw.extend(chunk);assert len(raw)<=B['single_body_bytes'] and total+len(raw)<=B['total_body_bytes']
    total+=len(raw);name=f'RESPONSE_{len(rows):02d}.xml';(state/name).write_bytes(raw);rows.append(dict(url=str(request.url),status=r.status_code,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest(),file=name,seconds=time.monotonic()-start,response_headers={k:v for k,v in r.headers.items() if k.lower() in ('date','last-modified','etag','content-type','content-length')}));(state/'HTTP.json').write_text(json.dumps(rows,sort_keys=True,indent=2)+'\n')
    return httpx.Response(r.status_code,content=bytes(raw),request=request)
  with httpx.Client(transport=httpx.MockTransport(handler)) as cached_client:
   budget=dict(original.DEFAULT_BUDGETS,inventory_pages=4,inventory_page_bytes=B['single_body_bytes'],inventory_wall_seconds=120,max_candidates=1500)
   result=original.inventory(cached_client,state,budget)
 result.update(selection_available_UTC=P['fixed_selection_available_UTC'],source_scope='CURRENT_OFFICIAL_ARCHIVE_FOLDER_UNION_NOT_CURRENT_TRADING_LIST_OR_PIT_CONTRACT_CERTIFICATE',full_historical_universe_certified=False,unknown_absence_is_not_nontradable=True,new_GETs=len(rows),total_discovery_and_inventory_body_bytes=total,prior_HTML_exact_cache=True,new_price_ZIPs=0,new_fits=0,new_wallets=0,seconds=time.monotonic()-began)
 (state/'INVENTORY.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print('ACTUAL_HISTORICAL_ARCHIVE_FOLDER_INVENTORY',len(result['symbols']),len(rows),total,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--discovery',type=Path,required=True);a=p.parse_args();run(a.state,a.discovery)
