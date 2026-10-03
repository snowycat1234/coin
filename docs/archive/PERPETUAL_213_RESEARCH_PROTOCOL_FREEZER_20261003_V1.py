"""Freeze only the new213 smoke or market metadata; no financial array IO."""
import argparse, hashlib, json, os, sys, time
from datetime import UTC, datetime
from pathlib import Path
from scripts.investment import perpetual_213_research as new
ROOT,STATE=new.ROOT,new.STATE
ARCHIVE='docs/archive/PERPETUAL_213_RESEARCH_PROTOCOL_FREEZER_20261003_V1.py'
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(name):
    p=ROOT/name;assert p.stat().st_size<=2_000_000 and not p.is_symlink();return json.loads(p.read_bytes())
def ref(name,status):
    v=read(name);assert v['status']==status;return dict(path=name,sha256=sha(ROOT/name),required_status=status)
def main():
    a=argparse.ArgumentParser();a.add_argument('--phase',choices=['smoke','market'],required=True);phase=a.parse_args().phase
    assert os.getenv('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
    assert Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
    old=read('protocols/PERPETUAL_PUBLIC_BENCHMARK_20261003_V1.json');hashes=dict(old['frozen_sources'])
    for p,h in hashes.items():assert sha(ROOT/p)==h,p
    accepted=ref('reports/fast_research/PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json','PASS_ROOT_D043_COMPLETE_213_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS')
    source=read(accepted['path']);hashes.update(source['source_hashes'])
    for p in [ARCHIVE,accepted['path'],new.INPUT,'scripts/investment/perpetual_213_research.py',
        'scripts/investment/perpetual_213_wiring_smoke.py','tests/test_perpetual_213_wiring.py',
        'docs/archive/PERPETUAL_213_RESEARCH_SOURCE_20261003_V1.py',
        'docs/archive/PERPETUAL_213_WIRING_SMOKE_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_213_WIRING_TEST_SOURCE_20261003_V1.py']:
        hashes[p]=sha(ROOT/p)
    guard_path=ROOT/'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
    import importlib.util
    loader=importlib.util.spec_from_file_location('_d043_freeze_closed_guard',guard_path);g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    g.closed(source['binding']['task_id'])
    adapter='scripts/investment/perpetual_213_research.py'
    spec=dict(created_utc=datetime.now(UTC).isoformat(),metadata_freezer_task_id=os.environ['COIN_TASK_ID'],
        environment=old['environment'],frozen_sources=hashes,classification='FIXED213_SEEN_DEVELOPMENT_NOT_UNSEEN_NOT_COMPLETE547')
    if phase=='smoke':
        out='protocols/PERPETUAL_213_WIRING_TEST_20261003_V1.json'
        spec.update(tests=['tests/test_perpetual_213_wiring.py'],research_adapter=dict(path=adapter,sha256=hashes[adapter]),
            calculation_rules={'scope':'ONE_NEW_213_SOURCE_PRIVATE_DATE_WARMUP_AND_FUTURE_PREFIX_CASE','source_files':72,'selectors':20,'physical_trading':16,'constant_cash':1},
            fee_profile=old['cost_scenarios'],data_scope='ONLY_SYNTHETIC_NO_MARKET_OR_OLD_LEDGER_ARRAYS')
    else:
        smoke=ref('reports/fast_research/PERPETUAL_213_WIRING_SMOKE_20261003_V1.json','PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT')
        v=read(smoke['path']);g.closed(v['binding']['task_id']);assert v['test_exit_code']==0 and v['source_bytes_unchanged'] is True
        for p in [smoke['path'],'protocols/PERPETUAL_213_WIRING_TEST_20261003_V1.json']:hashes[p]=sha(ROOT/p)
        out='protocols/PERPETUAL_213_RESEARCH_20261003_V1.json'
        spec.update(contract_id=new.CONTRACT,rules=new.RULES,period_ids=[new.PERIOD],cost_scenarios=new.base.COSTS,unit_scenarios=new.base.UNITS,
            input_manifest=ref(new.INPUT,new.MANIFEST_STATUS),trade_source_acceptance=accepted,required_smoke_receipt=smoke,
            preceding_failed_source=new.PRECEDING_FAILURE,
            run_dir='/home/xflops/coin-state/d043-perpetual-213-research-20261003-v1',
            output_path='reports/fast_research/PERPETUAL_213_RESEARCH_ACTUAL_20261003_V1.json',
            budgets=dict(new_owned_bytes=1_000_000_000,peak_RSS_bytes=3_000_000_000,wall_seconds=3600))
        new.context(spec) # compile all private date/selector anchors before any array
    for p,h in hashes.items():assert sha(ROOT/p)==h,p
    assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
    with (ROOT/out).open('x') as f:json.dump(spec,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status='FROZEN_ONLY_NEW_213_'+phase.upper()+'_METADATA_NO_ARRAYS',path=out,sha256=sha(ROOT/out),own_source_sha256=sha(__file__))))
if __name__=='__main__':main()
