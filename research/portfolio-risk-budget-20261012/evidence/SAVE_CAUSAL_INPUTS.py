import json,hashlib,sys
from pathlib import Path
import numpy as np
root=Path('/workspace/coin-tail-risk');here=root/'research/portfolio-risk-budget-20261012';sys.path.insert(0,str(here));import driver as m
prepared=Path('/workspace/portfolio-risk-budget-state/PREPARED_FINAL'); dest=here/'input';assert not dest.exists();dest.mkdir()
for name in ('P1.npz','P2.npz','P1_RISK.json','P2_RISK.json','PREPARATION.json'):(dest/name).write_bytes((prepared/name).read_bytes())
summary=json.loads((dest/'PREPARATION.json').read_text());new=[];reused=[]
for key in ('P1','P2'):
 d,base=m.old.targets(key)
 with np.load(dest/(key+'.npz'),allow_pickle=False) as z:
  np.testing.assert_array_equal(z['decision_us'],d)
  for arm in m.ARMS:
   exact=z[arm].tobytes()==base[arm].tobytes();assert exact==summary['windows'][key]['arms'][arm]['whole_target_exact_REUSED']
   if not exact:new.append(dict(window=key,arm=arm));continue
   assert arm=='CS_MATCHED';src=root/'research/quantity-grid-sensitivity-20261012/summary'/key/arm;out=here/'summary'/key/arm;out.mkdir(parents=True)
   for name in ('RESULT.json','BINDING.json','DAILY.csv','PUBLIC_RESTORE.json'):
    raw=(src/name).read_bytes();assert raw==m.b.git('show',m.proto()['quantity_baseline_commit']+':'+str((src/name).relative_to(root)));(out/name).write_bytes(raw)
   note=dict(status='REUSED_EXACT_TARGET_BITS_SAME_CAUSAL_FIXED10_BUDGET_WITH_CAP_SHORTFALLS',window=key,arm=arm,reference_commit=m.proto()['quantity_baseline_commit'],original_result_SHA256=hashlib.sha256((out/'RESULT.json').read_bytes()).hexdigest(),original_binding_SHA256=hashlib.sha256((out/'BINDING.json').read_bytes()).hexdigest(),new_target_archive_SHA256=m.sha(dest/(key+'.npz')),component_target_bits_SHA256=hashlib.sha256(base[arm].tobytes()).hexdigest(),forecast_risk=summary['windows'][key]['arms'][arm],new_wallets=0,financial_advances=0,originals='PRESERVED_ORIGINAL_RESULT_BINDING_AND_EXISTING_PUBLIC_RECOVERY_BYTES')
   m.save(out/'REUSE.json',note);reused.append(note)
assert len(new)==4 and len(reused)==2
m.save(here/'evidence/EXECUTION_PLAN.json',dict(scientific_attempts=1,new_wallets=new,REUSED=reused,old_wallet_reruns=0,source_code_commit=summary['source_commit'],quantity_profile_SHA256=m.profile_sha(),annual_budget=.10,scope='FOUR_CHANGED_TARGET_WALLETS_ONLY_TWO_EXACT_CS_REUSED'))
print('INPUTS_PUBLISHED_FOUR_NEW_TWO_CS_REUSED_EXACT_BITS')
