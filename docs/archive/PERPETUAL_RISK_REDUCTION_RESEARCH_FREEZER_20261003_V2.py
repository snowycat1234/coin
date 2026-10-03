"""Freeze only the new risk correctness control and direct capability pins."""
import argparse, hashlib, json, os, sys
from datetime import UTC, datetime
from pathlib import Path
from scripts.investment import perpetual_risk_reduction_research_v2 as new
ROOT=new.ROOT; STATE=new.base.STATE
ARCHIVE='docs/archive/PERPETUAL_RISK_REDUCTION_RESEARCH_FREEZER_20261003_V2.py'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
    p=ROOT/p;assert p.stat().st_size<2_000_000 and not p.is_symlink();return json.loads(p.read_bytes())
def ref(p,status):
    v=read(p);assert v['status']==status;return dict(path=p,sha256=sha(ROOT/p),required_status=status)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['smoke','market'],required=True);phase=parser.parse_args().phase
    assert os.environ.get('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
    assert Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
    assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
    parent=read('protocols/PERPETUAL_303_RESEARCH_20261003_V1.json')
    names=set(new.PINS)|{
        'scripts/investment/perpetual_risk_reduction_research_v2.py','docs/archive/PERPETUAL_RISK_REDUCTION_RESEARCH_SOURCE_20261003_V2.py',
        'tests/test_perpetual_risk_reduction_v2.py','docs/archive/PERPETUAL_RISK_REDUCTION_TEST_SOURCE_20261003_V2.py',
        'scripts/investment/perpetual_risk_reduction_smoke.py','docs/archive/PERPETUAL_RISK_REDUCTION_SMOKE_SOURCE_20261003_V1.py',
        ARCHIVE,'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py',
        'scripts/investment/public_pair_diagnostics.py','scripts/investment/bybit_spot_adapter.py',
        'scripts/investment/public_sma_daily.py','scripts/research_v8/registry.py',
        'scripts/research_v8/funding_price_source_v2.py','scripts/research_v7/oracle_flow_ceiling.py',
        'src/quant/paths.py','src/quant/resources.py','src/quant/disk.py','src/quant/metrics.py',
        'src/quant/execution_contract.py','environments/v8/uv.lock',
        'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json',
        'reports/GITHUB_PERPETUAL_303_RESEARCH_SOURCE_BINDING_20261003_V1.json',
        'reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json',new.parent.INPUT}
    hashes={p:sha(ROOT/p) for p in sorted(names)}
    for p,h in hashes.items():
        if p in parent['frozen_sources']:assert h==parent['frozen_sources'][p],p
    spec=dict(contract_id=new.CONTRACT,rules=new.RULES,period_ids=['303D'],cost_scenarios=new.base.COSTS,
        unit_scenarios=new.base.UNITS,environment=parent['environment'],frozen_sources=hashes,
        input_manifest=parent['input_manifest'],trade_source_acceptance=parent['trade_source_acceptance'],
        preceding_failed_source=new.parent.PRECEDING_FAILURE,private_lock_access='STREAM_SHA_ONLY_NOT_EXPORTED',
        run_dir=str(STATE/'d046-perpetual-risk-reduction-research-20261003-v2'),
        output_path='reports/fast_research/PERPETUAL_RISK_REDUCTION_RESEARCH_ACTUAL_20261003_V2.json',
        budgets=dict(new_owned_bytes=500_000_000,peak_RSS_bytes=3_000_000_000,wall_seconds=3600),
        prior_accepted_capability=dict(path='reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json',sha256='841a525d41162bbcbaedb14b0be0c3696bcf3356cfdb76542a864662797c4f58'),
        created_utc=datetime.now(UTC).isoformat(),freezer_task_id=os.environ['COIN_TASK_ID'])
    compiled=new.context(spec);assert len(compiled['derivation'])==2
    if phase=='smoke':
        output='protocols/PERPETUAL_RISK_REDUCTION_SMOKE_20261003_V2.json'
        spec.update(tests=['tests/test_perpetual_risk_reduction_v2.py'],research_adapter=dict(path='scripts/investment/perpetual_risk_reduction_research_v2.py',sha256=hashes['scripts/investment/perpetual_risk_reduction_research_v2.py']),
            calculation_rules=dict(scope='ONE_NEW_RISK_MINSTEP_MINNOTIONAL_CAPACITY_FUTURE_PREFIX_CASE',old_suite_replayed=False),fee_profile=new.base.COSTS,data_scope='SYNTHETIC_ONLY')
    else:
        output='protocols/PERPETUAL_RISK_REDUCTION_RESEARCH_20261003_V2.json'
        p='reports/fast_research/PERPETUAL_RISK_REDUCTION_SMOKE_20261003_V2.json'
        spec['required_smoke_receipt']=ref(p,'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT')
        task=read(p)['binding']['task_id'];t=json.loads((STATE/'task-progress'/('task-'+task+'.json')).read_bytes());assert t['status']=='completed' and t['exit_code']==0
        hashes[p]=sha(ROOT/p);hashes['protocols/PERPETUAL_RISK_REDUCTION_SMOKE_20261003_V2.json']=sha(ROOT/'protocols/PERPETUAL_RISK_REDUCTION_SMOKE_20261003_V2.json')
    with (ROOT/output).open('x') as f:json.dump(spec,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status='FROZEN_D046_'+phase.upper()+'_ALL_ANCHORS_COMPILED_NO_ARRAYS',path=output,sha256=sha(ROOT/output),direct_source_pins=len(hashes))))
if __name__=='__main__':main()
