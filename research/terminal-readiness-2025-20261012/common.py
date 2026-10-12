"""Exact public terminal snapshot access; original financial methods unchanged."""
import gzip,hashlib,importlib.util,io,json,subprocess,sys,zipfile
from decimal import Decimal as D,localcontext,ROUND_DOWN
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT='af6d8e1426c663f3d5afb2da311755487681c232';ARMS=('CS_MATCHED','VOL_MATCHED','STATIC50');SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');MINUTE=60000000;START=1767225600000000;END=START+60*MINUTE
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def save(p,x):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def account_api():
 grid=load('unchanged_terminal2025_grid',ROOT/'research/quantity-grid-sensitivity-20261012/grid_account.py')
 from scripts.investment import resumable_perpetual as native
 return grid.QuantityGridAccount,native
def parent(arm):
 assert arm in ARMS;prefix=f'research/portfolio-risk-2025-native-20261012/result/Y2025/{arm}/';index=json.loads(git('show',PARENT+':'+prefix+'INDEX.json'));parts=[]
 for r in index['parts']:
  raw=git('show',PARENT+':'+prefix+r['file']);assert len(raw)==r['bytes'] and digest(raw)==r['SHA256'];parts.append(raw)
 raw=b''.join(parts);assert len(raw)==index['packet_bytes'] and digest(raw)==index['packet_SHA256'];members={r['name']:r for r in index['members']}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  def read(name):
   raw=z.read(name);r=members[name];assert len(raw)==r['bytes'] and digest(raw)==r['SHA256'];return raw
  binding=json.loads(read('BINDING.json'));result=json.loads(read('RESULT.json'));body=json.loads(read('ACCOUNT.json'));ptr=json.loads(read('recovery/POINTER.json'));raw=read('recovery/'+ptr['snapshot_path']);assert digest(raw)==ptr['snapshot_SHA256'];snap=json.loads(gzip.decompress(raw))
 assert binding['arm']==result['arm']==arm and binding==ptr['binding'] and result['summary']==body['summary']
 assert snap['account']['clock_us']==snap['state']['cursor']==START and snap['state']['rows_written']==525600 and not snap['state']['pending'] and snap['state']['stop'] is None
 assert snap['account']['version']=='conditional_btc_anchored_quantity_grid_sensitivity_v1' and binding['quantity_profile_SHA256']=='94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf'
 proof=dict(parent_commit=PARENT,arm=arm,INDEX_SHA256=digest(git('show',PARENT+':'+prefix+'INDEX.json')),snapshot_SHA256=ptr['snapshot_SHA256'],parent_genuine_scheduler_hash=ptr['state_hash'],account_snapshot_SHA256=digest(json.dumps(snap['account'],sort_keys=True,separators=(',',':')).encode()),complete_historical_fill_requests=len(snap['account']['fill_requests']),historical_market_minutes_replayed=0,original_annual_status_unchanged=True)
 return snap,body,proof
def diagnose(state):
 assert not state.exists();state.mkdir(parents=True)
 price=Path('/workspace/portfolio-risk-2025-state/PUBLIC_SOURCE_RECOVERED/source/months/2025-12.npz');assert sha(price)=='684aa33ca39a1798072bcc850de5155ff5d8e9b1a12e650423f9fa73715f10b4'
 with np.load(price,allow_pickle=False) as z:times=z['times'];prices={s:dict(open=z[s+'_open'],quote=z[s+'_quote_volume']) for s in SYMBOLS}
 reports={}
 for arm in ARMS:
  snap,body,proof=parent(arm);account=snap['account'];requests=account['fill_requests'];rows=[]
  expired=[r for r in body['rejections'] if r.get('kind')=='TERMINAL' and r.get('reason')=='FIVE_ATTEMPTS_EXPIRED']
  for old in expired:
   matches=[(k,r) for k,r in requests.items() if k.startswith(old['order_id']+':')];assert len(matches)==5
   for key,row in sorted(matches,key=lambda x:x[1]['identity']['event_us']):
    x=row['identity'];s=x['symbol'];at=x['event_us']-1;k=int(np.searchsorted(times,at));assert times[k]==at and times[k-1]==at-MINUTE
    with localcontext() as c:c.prec=28;cap=D(str(float(prices[s]['quote'][k-1])))*D('.001')/D(str(float(prices[s]['open'][k])))
    assert str(cap)==x['available_quantity'];step=D(account['instrument_profiles'][s]['quantity_step']);executed=D(str(row['receipt']['executed_quantity']));request=D(x['quantity']);floor=(min(cap,request)/step).to_integral_value(rounding=ROUND_DOWN)*step
    assert executed==floor or row['receipt']['reason'] is not None
    rows.append(dict(fill_id=key,identity=x,receipt=row['receipt'],step=str(step),actual_previous_quote_available_us=at,capacity_decimal=str(cap),floor_decimal=str(floor),capacity_below_one_lot=cap<step))
  assert all(snap['state']['previous_quote'][s]==float(prices[s]['quote'][-1]) for s in SYMBOLS)
  reports[arm]=dict(proof=proof,terminal_expired=expired,exact_original_terminal_requests=rows,residual=body['summary']['positions'],original_marked_NAV=body['summary']['NAV'],account_advances=0,new_exit_trials=0,original_requests_kept=True)
 save(state/'DIAGNOSIS.json',reports);print('EXACT_PUBLIC_TERMINAL_CAUSE_DIAGNOSED',[(a,len(r['exact_original_terminal_requests'])) for a,r in reports.items()],flush=True)
