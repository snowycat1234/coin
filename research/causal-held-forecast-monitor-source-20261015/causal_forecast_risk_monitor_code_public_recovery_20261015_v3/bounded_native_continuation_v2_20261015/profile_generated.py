"""Generated native scheduler resource observation, not annual certification."""
import json,resource,time
from test_integration import run_case
import integration as i
rows=[]
for variant in ('CONTINUE_ONLY','TOPUP_THEN_CONTINUE'):
    began=time.monotonic();sim,guard=run_case(days=15,variant=variant)
    elapsed=time.monotonic()-began
    assert len(sim.account.trades)>0 and sim.account.fees>0, 'ACTIVE_PROFILE_REQUIRES_REAL_GENERATED_TRADES'
    rows.append(dict(policy_variant=variant,generated_minutes=sim.rows_written,wall_seconds=elapsed,
        estimated_366day_linear_seconds=elapsed*366/15,max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        monitor_rows=len(sim.account.monitor_journal),noop_cached=len(sim.account._noop_receipts),
        noop_total=sim.account._noop_count,financial_rows=len(sim.account.financial_ledger),
        primary_ledger_passed=i.financial_reconciliation(sim.account)['passed'],
        guard_receipts=len(guard.receipts),native_stop=sim.stop))
open('GENERATED_RESOURCE_PROFILE.json','w').write(json.dumps(dict(generated_only=True,annual_envelope_certified=False,
    extrapolation_is_not_a_runtime_guarantee=True,cases=rows),indent=2)+'\n')
print(json.dumps(rows))
