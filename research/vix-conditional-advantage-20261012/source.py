"""One bounded official GET; no fallback or authentication."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
import numpy as np
import requests
from vix import URL,START,END,DAY,parse
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def verify():
 for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():h,p=line.split(maxsplit=1);assert sha(ROOT/p)==h,p
def bounds():
 assert END<1772323200000000 and URL.endswith('cosd=2021-03-01&coed=2023-12-31')
 p=ROOT/'state/dataset_lock.json'
 if p.exists():assert sha(p)=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d','Opaque lock changed; stop without parsing'
def run(state,science):
 assert not state.exists() and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT) and subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==science
 verify();bounds();state.mkdir(parents=True);began=time.monotonic();status=None
 try:
  fetch_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
  with requests.Session() as session:
   response=session.get(URL,timeout=(10,30),stream=True,allow_redirects=False);status=response.status_code;response.raise_for_status();assert status==200,'No redirect/source alternates admitted';parts=[];size=0;headers={k:response.headers.get(k) for k in ('Last-Modified','ETag','Date','Content-Type')}
   for body in response.iter_content(8192):size+=len(body);assert size<=100000,'Frozen source byte budget';parts.append(body)
  body=b''.join(parts);(state/'VIXCLS.csv').write_bytes(body);t,v=parse(body);actual=np.isfinite(v);assert actual.sum()>=680 and t[0]<=START+DAY and t[-1]>=END-4*DAY
  months={(time.strftime('%Y-%m',time.gmtime(int(at)//1000000))) for at in t};assert len(months)==34,'All requested source months required'
  np.savez_compressed(state/'VIX_OBSERVATIONS.npz',observation_us=t,close=v,available_proxy_us=t+2*DAY)
  report=dict(status='PASS_OFFICIAL_BOUNDED_VIX_OBSERVATIONS_CONDITIONAL_CLOCK_NOT_VINTAGE_CERT',source_commit=science,fetch_UTC=fetch_UTC,response_headers=headers,URL=URL,HTTP_status=status,raw_SHA256=sha(state/'VIXCLS.csv'),raw_bytes=len(body),observation_rows=len(t),actual_finite_closes=int(actual.sum()),explicit_missing_holiday_rows=int((~actual).sum()),first_observation_us=int(t[0]),last_observation_us=int(t[-1]),months=len(months),available_clock='OBSERVATION_UTC_DATE_PLUS2D_PROXY_NOT_HISTORICAL_RECEIVE_CERT',vintage='LATEST_VINTAGE_AT_RETRIEVAL_NOT_HISTORICAL_POINT_IN_TIME',revision_bias='EOD_MAY_BE_RETROACTIVELY_RESTATED_LAG_DOES_NOT_FIX',free_CSV_arrival_SLA='UNKNOWN',DataShop='UNUSED_NOT_PURCHASED',new_GETs=1,retries=0,model_fits=0,new_wallets=0,protected_or_unknown_dates_opened=False,seconds=time.monotonic()-began)
  assert report['seconds']<60;save(state/'SOURCE_RESULT.json',report);print('ACTUAL_OFFICIAL_VIX_SOURCE',report,flush=True)
 except Exception as exc:
  save(state/'FAILED.json',dict(error=str(exc),HTTP_status=status,URL=URL,new_GET_attempts=1,retries=0,no_fallback=True,model_fits=0,new_wallets=0,seconds=time.monotonic()-began));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.source_commit)
