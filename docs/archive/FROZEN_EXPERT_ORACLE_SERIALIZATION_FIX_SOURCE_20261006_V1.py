import json,os
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha
from datetime import UTC,datetime
previous=ROOT/'protocols/FROZEN_EXPERT_ORACLE_20261006_V2.json';spec=json.loads(previous.read_bytes())
task=json.loads((STATE/'task-progress/task-418208d509a94bdeae922f736fe20cbf.json').read_bytes())
assert task['status']=='failed' and task['exit_code']==1
partial=ROOT/'reports/FROZEN_EXPERT_ORACLE_OPPORTUNITY_20261006_V1.json'
spec.update(created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(ROOT/'scripts/investment/oracle_expert_opportunity.py'),
    serialization_only_recovery=dict(previous_protocol_path=str(previous.relative_to(ROOT)),previous_protocol_sha256=sha(previous),
        failed_task_id=task['id'],failed_source_path='docs/archive/FROZEN_EXPERT_ORACLE_SERIALIZATION_FAILED_SOURCE_20261006_V1.py',
        failed_source_sha256=sha(ROOT/'docs/archive/FROZEN_EXPERT_ORACLE_SERIALIZATION_FAILED_SOURCE_20261006_V1.py'),
        failed_partial_output_path=str(partial.relative_to(ROOT)),failed_partial_output_sha256=sha(partial),failed_partial_output_bytes=partial.stat().st_size,
        change='Only JSON NumPy scalar conversion and serialize before opening destination; no selection/calculation/period/cost/expert/gate change; no trading account rerun.'))
with (ROOT/'protocols/FROZEN_EXPERT_ORACLE_20261006_V3.json').open('x') as f:json.dump(spec,f,indent=2,ensure_ascii=False);f.write('\n')
receipt=dict(status='FAILED_ORACLE_SERIALIZATION_PRESERVED_NO_ECONOMIC_REPLAY',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),**spec['serialization_only_recovery'])
with (ROOT/'reports/FROZEN_EXPERT_ORACLE_SERIALIZATION_FAILURE_20261006_V1.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## D104输出修复\n\nOracle任务418208d509a94bdeae922f736fe20cbf已在JSON导出失败退出1；计算/归因断言通过但不得消费不完整输出。V1 partial与原源码SHA保留；V3只修NumPy标量JSON导出，周期/费用/专家/门槛不改，不重跑账户。恢复只读诊断，不把失败发布为成功。\n')
print(json.dumps(dict(status=receipt['status'])))
