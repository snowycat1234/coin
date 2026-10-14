"""Export one fixed generated collision and boundary receipt, never history."""
from pathlib import Path
import hashlib,json
from bind_native import EXECUTED_SOURCE,ROOT
from generated_fixtures import new,finish,START,M
from native_adapter import S,HEADROOM
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def receipt(sim,name):
    return dict(name=name,completion=sim.completion,stop_offset_us=None if sim.stop is None else sim.stop-START,
        breaches=sim.breaches,protective_events=sim.protective_events,locks=sim.protective_locks,
        native_trades=sim.account.trades,native_funding=sim.account.funding,
        rejections=sim.rejections,final_account=sim.account.snapshot(),
        terminal_cash_realized=all(not x.quantity for x in sim.account.positions.values()))

def build():
    runs={}
    for name in ('CAP_COLLISION','CAP_COLLISION_PARTIAL','CAP_COLLISION_PAID','TERMINAL_ZERO','TERMINAL_LATE','TERMINAL_COMPLETE'):
        for arm in ('legacy_shared_priority_fixed','aligned_independent','paired'):
            runs[name+'__'+arm]=receipt(finish(new(arm,name)),name+'__'+arm)
    runs['CAP_COLLISION__ORIGINAL_UNFIXED_LEGACY_DIAGNOSTIC']=receipt(
        finish(new('legacy_shared_priority_fixed','CAP_COLLISION',True)),
        'CAP_COLLISION__ORIGINAL_UNFIXED_LEGACY_DIAGNOSTIC')
    return dict(schema='GENERATED_ONLY_HEADROOM_PRIORITY_AND_TERMINAL_WITNESS_V1',
        source_scope='SYNTHETIC_PRICES_CLOCKS_TARGETS_FUNDING_ONLY',historical_GO=False,
        historical_year_incidence_claim=False,historical_arrays_opened=0,
        original_unfixed_headroom_source_SHA256=sha(Path(HEADROOM.__file__)),
        native_account_source_SHA256=sha(ROOT/'coin_bot_native_adapter_portable_synthetic_20261014/dependency_carrier/repo/src/quant/perpetual_account.py'),
        executed_additional_closure=EXECUTED_SOURCE,
        exact_fixture_source_SHA256=sha(HERE/'generated_fixtures.py'),
        priority_difference=dict(unfixed_stop_offset_us=28*M+1,fixed_stop_offset_us=26*M+1,
          delay_us=2*M,unfixed_breaches=2,fixed_breaches=1,
          correction='RETAIN_PENDING_ORIGINAL_CAP_ORDER_OBJECT_TARGET_SIGNAL_ATTEMPTS'),
        runs=runs)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or not a.output.resolve().is_relative_to(HERE):raise ValueError('FRESH_ISOLATED_GENERATED_RECEIPT_REQUIRED')
    a.output.write_text(json.dumps(build(),sort_keys=True,indent=2,default=str)+'\n')
    print(json.dumps(dict(status='GENERATED_WITNESS_EXPORTED',file=a.output.name,SHA256=sha(a.output),bytes=a.output.stat().st_size)))
