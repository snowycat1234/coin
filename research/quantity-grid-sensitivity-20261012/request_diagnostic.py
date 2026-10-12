"""Read original request receipts; no account construction or financial replay."""
import argparse,gzip,hashlib,json
from collections import Counter
from decimal import Decimal as D
from pathlib import Path
def inspect(folder):
 ptr=json.loads((folder/'recovery/POINTER.json').read_text());binding=json.loads((folder/'BINDING.json').read_text());assert ptr['binding']==binding
 p=folder/'recovery'/ptr['snapshot_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==ptr['snapshot_SHA256'];a=json.loads(gzip.decompress(p.read_bytes()))['account']
 steps={s:D(v['quantity_step']) for s,v in a['instrument_profiles'].items()};counts=Counter();by=Counter();examples=[]
 for key,row in sorted(a['fill_requests'].items(),key=lambda r:(r[1]['identity']['event_us'],r[0])):
  x=row['identity'];r=row['receipt'];step=steps[x['symbol']];q=D(x['quantity']);cap=D(x['available_quantity'])
  if min(q,cap)<step:
   assert not r['fills'],'Zero after actual floor cannot have fills';counts['ZERO_AFTER_LOT_FLOOR']+=1;by[x['symbol']]+=1
   if q<step:counts['REQUEST_BELOW_LOT']+=1
   if cap<step:counts['CAPACITY_BELOW_LOT']+=1
   if len(examples)<8:examples.append(dict(fill_id=key,**x,step=str(step),receipt_reason=r['reason']))
 for row in a['trades']:
  q=D(row['decimal_strings']['quantity']);assert q>0 and q%steps[row['symbol']]==0
 return dict(scope='EXACT_ORIGINAL_SAVED_FILL_REQUEST_IDENTITIES_ZERO_ADVANCE_NOT_ALL_COMBINED_REASONS_ATTRIBUTED_TO_LOTS',snapshot_SHA256=ptr['snapshot_SHA256'],state_hash=ptr['state_hash'],fill_requests=len(a['fill_requests']),zero_floor_counts=dict(counts),zero_floor_by_symbol=dict(by),first_examples=examples,executed_quantity_lattice='ALL_POSITIVE_INTEGER_LOTS',terminal_quantity={s:v['quantity'] for s,v in a['positions'].items()})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--window',choices=['P1','P2'],required=True);a=p.parse_args();root=Path('/workspace/quantity-grid-state')/('OBSERVED_'+a.window);fine=Path('/workspace/unified-exit-economics-state')/('OBSERVED_'+a.window)
 for arm in ('CS_MATCHED','VOL_MATCHED','STATIC50'):
  r=dict(window=a.window,arm=arm,coarse=inspect(root/arm),fine_REUSED=inspect(fine/arm),new_wallets=0,account_advances=0)
  (root/arm/'REQUEST_DIAGNOSTIC.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n');print(arm,r['coarse']['zero_floor_counts'],r['fine_REUSED']['zero_floor_counts'])
