"""Only this project's three recent modules; legacy clocks are labelled."""
import json,hashlib
from pathlib import Path
from quant.paths import ROOT,STATE
def read(p):return json.loads(Path(p).read_bytes())
def union(intervals):
    ordered=sorted(intervals);total=0.;end=None
    for start,stop in ordered:
        if end is None or start>end:total+=stop-start;end=stop
        elif stop>end:total+=stop-end;end=stop
    return total
config=read(ROOT/'.cache/recent_research_timing_sources.json');rows=[]
for module,x in config.items():
    tasks=[]
    for tid,phase in x['tasks'].items():
        p=STATE/'task-progress'/('task-'+tid+'.json');t=read(p)
        assert t.get('ended_at') is not None
        tasks.append(dict(id=tid,phase=phase,start=t['started_at'],end=t['ended_at'],exit_code=t['exit_code'],
            receipt_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    start=min(t['start'] for t in tasks);end=max(t['end'] for t in tasks)
    wall=union([(t['start'],t['end']) for t in tasks]);actual=read(ROOT/x['result'])
    groups={g:union([(t['start'],t['end']) for t in tasks if t['phase']==g]) for g in sorted({t['phase'] for t in tasks})}
    rows.append(dict(module=module,observed_first_task_to_last_recorded_task_seconds=end-start,
        visible_task_interval_union_seconds=wall,visible_intertask_remainder_seconds=end-start-wall,
        grouped_interval_unions_seconds=groups,group_unions_are_not_additive_when_overlap=True,
        experiment_internal_combined_seconds=actual['elapsed_seconds'],experiment_task_id=actual['task_id'],
        experiment_internal_scope='Includes source/hash/capacity/replay/save, not separable from old records',tasks=tasks,
        excluded_initial_context_and_implementation='UNKNOWN',context_model_wait_document_untracked_interval_attribution='UNKNOWN',
        exact_model_id='UNKNOWN',reasoning_effort='UNKNOWN',end_to_end_conversation_seconds='UNKNOWN'))
out=STATE/'d081-fast-workflow-timing-20261005-v1';out.mkdir()
with (out/'RESULT.json').open('x') as f:json.dump(dict(status='RECENT_TASK_METADATA_ONLY_NO_REPLAY',modules=rows,
    clock_scope='Legacy wall-clock task receipts, not reconstructed monotonic history. New batch stages record monotonic intervals.',
    privacy_scope='Only explicitly enumerated own-project task IDs and accepted result timing; no other chat/session/key reads.'),f,indent=2)
print(json.dumps([{k:v for k,v in r.items() if k not in ('tasks','grouped_interval_unions_seconds')} for r in rows]))
