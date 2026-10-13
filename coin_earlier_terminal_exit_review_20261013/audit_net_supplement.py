"""Read-only lossless-chunk net-exposure supplement; no simulator imports."""
from pathlib import Path
import hashlib,json
import numpy as np
H=Path(__file__).resolve().parent; R=H.parent; M=R/'coin_earlier_terminal_exit_20261013'; P=R/'coin_earlier_terminal_postrun_20261013'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
syms=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT']
rows=[]
for c in read(M/'CASE_BINDINGS.json')['cases']:
 identity=c['case_id']+'_FINE_ORIGINAL'; pair={'case_id':identity}
 for label,directory in [('old',R/c['baseline_state_local_locator']),('new',M/'state_resumed_authorized_once'/identity)]:
  pointer_path=directory/'recovery/POINTER.json'; pointer=read(pointer_path); pointer_sha=sha(pointer_path)
  assert pointer['completed_minutes']==525600 and len(pointer['chunks'])==365
  columns=read(directory/'MINUTE_NUMERIC.json')['columns']
  assert columns[0]['name']=='nav' and [columns[i]['name'] for i in range(14,19)]==[s+'_signed_marked_notional' for s in syms]
  arrays=[]; digesters={i:hashlib.sha256() for i in [0,14,15,16,17,18]}
  for index,chunk in enumerate(pointer['chunks']):
   q=directory/'recovery'/chunk['path']
   assert chunk['path']==f'DAY_{index:04d}.npz' and chunk['rows']==1440 and sha(q)==chunk['SHA256']
   with np.load(q,allow_pickle=False) as z:
    x=z['minute_chunk']; assert x.shape==(1440,36) and np.isfinite(x[:,0]).all() and (x[:,0]>0).all()
    for i,d in digesters.items():d.update(np.ascontiguousarray(x[:,i]).tobytes())
    signed=sum(x[:,i] for i in range(14,19))/x[:,0]
    assert np.isfinite(signed).all();arrays.append(signed)
  for i,d in digesters.items():assert d.hexdigest()==columns[i]['raw_SHA256']
  v=np.concatenate(arrays); result=read(directory/'RESULT.json')
  value={'mean_actual_signed_net':float(np.mean(v)), 'max_actual_abs_signed_net':float(np.max(np.abs(v))), 'minute_rows':len(v), 'pointer_SHA256':pointer_sha, 'RESULT_SHA256':sha(directory/'RESULT.json'), 'lossless_nav_and_each_CORE5_notional_bits_verified':True}
  if label=='new':
   for k in ['mean_actual_signed_net','max_actual_abs_signed_net']:assert abs(value[k]-result[k])<=1e-12
  else:assert 'mean_actual_signed_net' not in result and 'max_actual_abs_signed_net' not in result
  assert sha(pointer_path)==pointer_sha;pair[label]=value
 rows.append(pair)
out={'status':'PASS_INDEPENDENT_LOSSLESS_NET_EXPOSURE_SUPPLEMENT', 'method':'CORE5 left-associated float signed_marked_notional sum divided by NAV at each observed minute; NumPy mean and maximum absolute net, matching original resumed runner', 'legacy_report_old_net_fields_remain_null':True, 'no_report_or_financial_source_edits':True, 'financial_advances':0, 'new_historical_wallets_executed':0, 'new_RESULT_metric_absolute_tolerance':1e-12,'cases':rows}
with (H/'NET_EXPOSURE_SUPPLEMENT.json').open('x') as f:json.dump(out,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
print(json.dumps(out,indent=2,sort_keys=True))
