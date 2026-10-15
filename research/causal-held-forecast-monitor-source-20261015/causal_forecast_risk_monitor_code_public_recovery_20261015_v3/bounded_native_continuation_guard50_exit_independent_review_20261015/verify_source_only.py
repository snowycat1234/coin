"""Read-only independent source/artifact binding verification; finance blocked."""
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch
import guard50_exit_entry as e
import guard50_exit as d

OUT=e.ROOT/'bounded_native_continuation_guard50_exit_independent_review_20261015'
DIRECTORY=e.HERE/'source_only_preparation_attempt002'
raw=(DIRECTORY/'PREPARATION.json').read_bytes()
with ExitStack() as stack:
    blockers=[(e.a.n,'_construct_case'),(e.a.n,'runtime'),(e.a.g,'make_account'),
        (e.a,'make_annual_case'),(e.a,'validate_root_go'),(e,'make_annual_case'),
        (e,'validate_root_go'),(e,'_default_constructor_callback'),
        (d.Guard50ExitAccount,'__init__'),(d.V2.ContinuationAccount,'__init__'),
        (d.V2.ENGINE.USDTLinearPerpetualAccount,'__init__')]
    guards=[stack.enter_context(patch.object(obj,name,side_effect=AssertionError('NO_FINANCE_OR_GO:'+name)))
        for obj,name in blockers]
    prep=e._validate_preparation(raw)
    assert prep['code_identity']==e.code_identity()
    assert prep['preserved_evidence_pins']==e.preserved_evidence_identity()
    for name,digest in prep['code_identity'].items():
        assert sha256((e.ROOT/name).read_bytes()).hexdigest()==digest
    artifacts={name:e.a.h._read_exact(DIRECTORY/name,pin['SHA256'],pin['bytes'])
        for name,pin in prep['artifacts'].items()}
    annual_raw,annual=e._frozen_preparation()
    assert annual_raw==artifacts['ANNUAL_SOURCE_PREPARATION.json']
    for name in e.a.ARTIFACTS:
        assert artifacts[name]==(e.ANNUAL_PREPARATION/name).read_bytes()
    index,files,quality,rows,decisions,target,covariance,captured=e._source_projection(
        e.ROOT/'native_2024_source_restore_20261015',annual_raw,annual,artifacts)
    assert files==prep['source_files'] and quality==prep['original200_quality']
    assert annual['source_identity']==prep['source_identity']
    assert e._sha(decisions.tobytes())==prep['decision_raw_SHA256']
    assert e._sha(target.tobytes())==prep['selected_target_raw_SHA256']
    assert e._sha(covariance.tobytes())==prep['covariance_raw_SHA256']
    window=e._make_window(index,captured,json.loads(artifacts['CAUSAL_MARK_ADAPTER.json']))
    assert e._same(e._input_binding(window,rows,decisions,target),prep['input_binding'])
    assert all(g.call_count==0 for g in guards)
    result=dict(status='PASS_FINAL_SOURCE_ONLY_PINS_NO_ACCOUNT_OR_ADVANCE',
        preparation_SHA256=e._sha(raw),policy_version=e.POLICY_VERSION,source_scope=e.SOURCE_SCOPE,
        code_files_checked=len(prep['code_identity']),source_files_checked=len(files),
        artifacts_checked=len(artifacts),exact_old_artifact_bytes_preserved=True,
        selected_target_decision_covariance_raw_hashes_match=True,
        source_identity=prep['source_identity'],policy_identity=prep['policy_identity'],
        input_binding_SHA256=prep['input_binding_SHA256'],
        financial_runtime_and_account_construction_explicitly_blocked=True,
        blocked_finance_runtime_or_GO_entry_calls=0,actual_historical_accounts_constructed=0,
        historical_minutes_advanced=0,adaptive_2024_development_comparison=True,
        B_C_reruns_authorized=False,maximum_cases=1)
(OUT/'SOURCE_ONLY_FINAL_VERIFICATION.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
