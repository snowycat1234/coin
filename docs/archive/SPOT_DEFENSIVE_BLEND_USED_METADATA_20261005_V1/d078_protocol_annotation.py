import hashlib,json,os
from datetime import UTC,datetime
from pathlib import Path
R=Path('/mnt/d/codex/coin');p=R/'protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json'
r=R/'reports/fast_research/SPOT_DEFENSIVE_BLEND_20261005_V1.json'
v={'status':'NON_EXECUTABLE_METADATA_ERRATUM_NOT_PARAMETER_CHANGE',
   'original_protocol_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
   'original_fields_preserved':{'parent_commit':'4246975340b1b0debdb57bc25c4d16cd8c1077a3','question':'copied D077 Spot/perpetual question'},
   'correct_parent_commit':'c7898815e8dacb7726627d6da6035afa4f32975e',
   'correct_question':'Does fixed half HOLD10 / half EXIT10 reduce drawdown on same Spot input and full capital compared with accepted HOLD8, and at what net/cost/actual-risk tradeoff?',
   'reason':'Preparation inherited two stale documentary fields from D077; executable recipe/control/hypothesis/budget/success_decision were already correct.',
   'actual_result_exists_at_annotation':r.exists(),'task_id':os.environ['COIN_TASK_ID'],'created_utc':datetime.now(UTC).isoformat(),
   'source_or_parameters_changed':False,'old_protocol_overwritten':False}
assert not r.exists()
with (R/'protocols/SPOT_DEFENSIVE_BLEND_20261005_METADATA_ERRATUM_V1.json').open('x') as f:json.dump(v,f,indent=2);f.write('\n')
print(json.dumps(v))
