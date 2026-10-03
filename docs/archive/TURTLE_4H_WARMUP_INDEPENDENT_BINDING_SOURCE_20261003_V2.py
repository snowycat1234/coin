"""D047 exclusive independent source binding; small metadata/compile only."""
import json,os
from pathlib import Path
from scripts.investment import audit_perpetual_4h_warmup_source as audit

ROOT,STATE=audit.ROOT,audit.STATE
OWN='scripts/investment/audit_perpetual_4h_warmup_source.py'
ARCHIVE='docs/archive/TURTLE_4H_WARMUP_INDEPENDENT_SOURCE_20261003_V1.py'
HELPER='docs/archive/TURTLE_4H_WARMUP_INDEPENDENT_BINDING_SOURCE_20261003_V2.py'
PROTOCOL='protocols/TURTLE_4H_WARMUP_SOURCE_20261003_V1.json'
PROTOCOL_SHA='b3a726a4b6b05aed2c3030491e6313740a39d5af4ef21a87716ae4be589a648b'
ACTUAL='reports/fast_research/TURTLE_4H_WARMUP_SOURCE_ACTUAL_20261003_V1.json'
ACTUAL_SHA='7f72a55ff2cf0e6f5b419f7e2466d6d91edae9ecda5db86e49ef3b001415ecde'
TASK='8b7f33122c82495abfc575bd5b4a20b9'
run=STATE/'d047-turtle-4h-warmup-independent-20261003-v1'
assert os.getenv('COIN_TASK_ID') and audit.sha(ROOT/OWN)=='aca87d857e6c720a1b1d22550a38d436652e5961106b83683be0a714d9cad36b'
assert audit.sha(ROOT/ARCHIVE)==audit.sha(ROOT/OWN) and audit.sha(ROOT/HELPER)==audit.sha(__file__)
assert audit.sha(ROOT/PROTOCOL)==PROTOCOL_SHA and audit.sha(ROOT/ACTUAL)==ACTUAL_SHA and not run.exists()
spec=json.loads((ROOT/PROTOCOL).read_bytes());actual=json.loads((ROOT/ACTUAL).read_bytes())
assert actual['binding']['task_id']==TASK and actual['binding']['protocol_sha256']==PROTOCOL_SHA and actual['status']==audit.ACTUAL_STATUS
g=audit.parent.base().guards();closed=g.closed(TASK)
private=audit.context();original=audit.parent.base();function,derivation=private['adapted_audit'](original)
assert callable(function) and closed['task']['status']=='completed' and closed['task']['exit_code']==0
hashes=dict(spec['frozen_sources'])
for path in (OWN,ARCHIVE,HELPER,audit.PARENT,audit.BASE,original.GUARD):
    value=audit.sha(ROOT/path);assert path not in hashes or hashes[path]==value;hashes[path]=value
assert 'state/dataset_lock.json' not in hashes
for path,value in hashes.items():assert audit.sha(ROOT/path)==value
plan=dict(ready_to_execute=True,checker_sha256=hashes[OWN],protocol_path=PROTOCOL,protocol_sha256=PROTOCOL_SHA,
    actual_report=ACTUAL,actual_report_sha256=ACTUAL_SHA,actual_task_id=TASK,budgets=audit.BUDGET,source_hashes=hashes,
    preparation_task_id=os.environ['COIN_TASK_ID'],preparation_source_sha256=audit.sha(__file__),
    scope='ONLY_FOUR_NEW_USDM_4H_JUL_AUG2024_RAW_NORMALIZED_QA',market_or_QA_executed_during_binding=False,
    independent_original_derivation=derivation)
run.mkdir();digest,size=g.write(run/'ACTUAL_BINDING.json',plan)
print(json.dumps(dict(status='PASS_D047_INDEPENDENT_SOURCE_BINDING_AND_COMPILE_ONLY_NO_ROWS',task_id=os.environ['COIN_TASK_ID'],
    binding_sha256=digest,bytes=size,source_count=len(hashes),producer_closed_task=TASK,QA_executed=False)))
