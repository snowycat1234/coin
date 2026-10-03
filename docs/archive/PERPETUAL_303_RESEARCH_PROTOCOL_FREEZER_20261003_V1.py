"""Freeze source-accepted303 synthetic check/market design; no market array IO."""
import argparse,hashlib,importlib.util,json,os,sys
from datetime import UTC,datetime
from pathlib import Path
from scripts.investment import perpetual_303_research as new
ROOT,STATE=new.ROOT,new.base.STATE
ARCHIVE='docs/archive/PERPETUAL_303_RESEARCH_PROTOCOL_FREEZER_20261003_V1.py'
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(name):
    p=ROOT/name;assert p.stat().st_size<2_000_000 and not p.is_symlink();return json.loads(p.read_bytes())
def ref(name,status):
    v=read(name);assert v['status']==status;return dict(path=name,sha256=sha(ROOT/name),required_status=status)
def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['smoke','market'],required=True);phase=p.parse_args().phase
    assert os.getenv('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2'
    assert Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
    old=read('protocols/PERPETUAL_HOLD_RESEARCH_20261003_V1.json');hashes=dict(old['frozen_sources'])
    rootpath='reports/fast_research/PERPETUAL_303_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json'
    accepted=ref(rootpath,'PASS_ROOT_D045_COMPLETE_303_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS');source=read(rootpath)
    s=importlib.util.spec_from_file_location('_d045_freeze_guard',ROOT/GUARD);g=importlib.util.module_from_spec(s);s.loader.exec_module(g);g.closed(source['binding']['task_id'])
    for name,digest in source['source_hashes'].items():
        assert name not in hashes or hashes[name]==digest;hashes[name]=digest
    files=[ARCHIVE,rootpath,new.INPUT,'scripts/investment/perpetual_303_research.py','docs/archive/PERPETUAL_303_RESEARCH_SOURCE_20261003_V1.py',
        'scripts/investment/perpetual_303_wiring_smoke.py','docs/archive/PERPETUAL_303_WIRING_SMOKE_SOURCE_20261003_V1.py',
        'tests/test_perpetual_303_wiring.py','docs/archive/PERPETUAL_303_WIRING_TEST_SOURCE_20261003_V1.py',
        'docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py',
        'scripts/investment/perpetual_213_research.py']
    for name in files:hashes[name]=sha(ROOT/name)
    adapter='scripts/investment/perpetual_303_research.py'
    spec=dict(created_utc=datetime.now(UTC).isoformat(),metadata_freezer_task_id=os.environ['COIN_TASK_ID'],environment=old['environment'],
        frozen_sources=hashes,classification='FIXED303_SEEN_DEVELOPMENT_NOT_UNSEEN_NOT_REPAIRED547')
    if phase=='smoke':
        output='protocols/PERPETUAL_303_WIRING_TEST_20261003_V1.json'
        spec.update(tests=['tests/test_perpetual_303_wiring.py'],research_adapter=dict(path=adapter,sha256=hashes[adapter]),
            calculation_rules=dict(scope='ONE_NEW303_METADATA_FIXED_SELECTOR_FUTURE_PREFIX_CASE',source_files=94,selectors=20,physical_trading=16,constant_cash=1),
            fee_profile=old['cost_scenarios'],data_scope='ONLY_SYNTHETIC_NO_MARKET_OR_OLD_LEDGER_ARRAYS')
    else:
        smokepath='reports/fast_research/PERPETUAL_303_WIRING_SMOKE_20261003_V1.json'
        smoke=ref(smokepath,'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT');v=read(smokepath)
        g.closed(v['binding']['task_id']);assert v['test_exit_code']==0 and v['source_bytes_unchanged'] is True
        for name in [smokepath,'protocols/PERPETUAL_303_WIRING_TEST_20261003_V1.json']:hashes[name]=sha(ROOT/name)
        output='protocols/PERPETUAL_303_RESEARCH_20261003_V1.json'
        spec.update(contract_id=new.CONTRACT,rules=new.RULES,period_ids=[new.PERIOD],cost_scenarios=new.base.COSTS,unit_scenarios=new.base.UNITS,
            input_manifest=ref(new.INPUT,new.MANIFEST_STATUS),trade_source_acceptance=accepted,required_smoke_receipt=smoke,preceding_failed_source=new.PRECEDING_FAILURE,
            run_dir='/home/xflops/coin-state/d045-perpetual-303-research-20261003-v1',output_path='reports/fast_research/PERPETUAL_303_RESEARCH_ACTUAL_20261003_V1.json',
            budgets=dict(new_owned_bytes=1_000_000_000,peak_RSS_bytes=3_000_000_000,wall_seconds=3600))
        new.context(spec)
    for name,digest in hashes.items():assert sha(ROOT/name)==digest,name
    with (ROOT/output).open('x') as f:json.dump(spec,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status='FROZEN_NEW303_'+phase.upper()+'_METADATA_NO_ARRAYS',path=output,sha256=sha(ROOT/output),task_id=os.environ['COIN_TASK_ID'])))
if __name__=='__main__':main()
