"""One active generated-only resource observation; not annual certification."""
import json
from pathlib import Path
import resource
import time
import numpy as np
import guard50_exit as d
from test_native_runtime import fixture

window,rows,decisions=fixture(15)
for day in range(len(decisions)):
    for key in ('open','close','mark'):
        window['market']['BTCUSDT'][key][day*1440+10:day*1440+21]=20000.
began=time.monotonic()
sim,guard=d.construct_case(window,rows,decisions,np.full((len(decisions),5),.03),generated_scope=d.GENERATED)
while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
elapsed=time.monotonic()-began
warnings=[r for r in sim.account.monitor_journal if any(a.get('reason')=='GUARD50_PAID_EXIT_NO_TOPUP' for a in r['actions'])]
assert len(sim.account.trades)>0 and sim.account.fees>0 and len(warnings)>0
assert not sim.account.transfer_journal
assert d.V2.financial_reconciliation(sim.account)['passed']
result=dict(generated_only=True,annual_envelope_certified=False,
    extrapolation_is_not_a_runtime_guarantee=True,
    case=dict(policy_variant=d.POLICY_VARIANT,generated_minutes=sim.rows_written,
        wall_seconds=elapsed,estimated_366day_linear_seconds=elapsed*366/15,
        max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        paid_trade_rows=len(sim.account.trades),paid_fees_USDT=str(sim.account.fees),
        Guard50_warning_rows=len(warnings),transfer_rows=0,
        conditional_settlements=len(sim.account.settlement_journal),
        monitor_rows=len(sim.account.monitor_journal),noop_cached=len(sim.account._noop_receipts),
        financial_rows=len(sim.account.financial_ledger),
        primary_ledger_passed=True,native_stop=sim.stop))
raw=(json.dumps(result,indent=2)+'\n').encode()
path=Path(__file__).resolve().parent/'GENERATED_RESOURCE_PROFILE_D.json'
with path.open('xb') as stream:stream.write(raw)
print(json.dumps(result))
