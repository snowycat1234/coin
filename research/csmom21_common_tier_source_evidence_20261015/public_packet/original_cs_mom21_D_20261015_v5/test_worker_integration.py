"""Fresh-process real CLI + real executable GO + unchanged guard regression.

Only invented fixture storage, recording source-context/capture and the post-
guard native constructor sentinel are substituted. Real loader, wire verifier,
code pin checks, NPZ codec, binding validation and CLI dispatch all execute.
No runtime generated flag exists. This is not an annual-history execution.
"""
from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import patch

import numpy as np
import cs_common as c
import cs_codec as codec
import cs_config as config
import cs_entry as entry
import cs_finance_gate as gate
import cs_loader as loader
import cs_source as source
import cs_verified_wires as verified
import run_cs
from cs_source_guard import current_guard, SourceOnlyGuard, SourceBoundaryViolation
from test_cs_entry import fake_preparation, fake_authority


def bundle(prep):
    p = c.exact_object(prep); code = gate.code_identity()
    pr = c.canonical(dict(schema=gate.PREPARED_REVIEW_SCHEMA, status='PASS', source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256,
        scope_manifest_SHA256=entry.manifest_sha(), source_contract_map_SHA256=entry.contract_sha(),
        tranche=entry.FIRST6, ordered_cells=list(entry.tranche_cells(entry.FIRST6)), years=[2022, 2023],
        preparation_SHA256=c.sha(prep), source_stage_GO_SHA256=p['source_stage_GO_SHA256'], source_review_SHA256=p['source_review_SHA256'],
        per_cell_input_binding_SHA256={k: v['input_binding_SHA256'] for k,v in p['cells'].items()},
        per_year_array_raw_SHA256={k: v['array_raw_SHA256'] for k,v in p['years'].items()},
        old_D_GO_reused_as_authority=False, native_financial_gate_reviewed=False, financial_execution_authorized=False))
    nr = c.canonical(dict(schema=gate.NATIVE_REVIEW_SCHEMA, status='PASS', source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256,
        financial_code_manifest_SHA256=code, scope_manifest_SHA256=entry.manifest_sha(), tranche=entry.FIRST6,
        ordered_cells=list(entry.tranche_cells(entry.FIRST6)), native_financial_gate_reviewed=True, financial_execution_authorized=False,
        actual_source_or_target_bodies_read=False, old_D_GO_reused_as_authority=False,
        generated_two_worker_probe_passed=True, worker_CPUs=[4,5], maximum_observed_live_workers=2,
        generated_resource_probe_SHA256='0'*64))
    rr = c.canonical(dict(schema=gate.REVIEW_SCHEMA, status='PASS', source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256,
        financial_code_manifest_SHA256=code, scope_manifest_SHA256=entry.manifest_sha(), source_contract_map_SHA256=entry.contract_sha(),
        preparation_SHA256=c.sha(prep), tranche=entry.FIRST6, ordered_cells=list(entry.tranche_cells(entry.FIRST6)),
        source_stage_GO_SHA256=p['source_stage_GO_SHA256'], old_D_GO_reused_as_authority=False,
        native_financial_gate_reviewed=True, financial_execution_authorized=False,
        prepared_source_target_review_SHA256=c.sha(pr), native_generated_review_SHA256=c.sha(nr),
        real_CLI_generated_GO_guard_integration_reviewed=True, failed_claim_supersession_packet_SHA256=gate.supersession.PACKET_SHA,
        stable_cross_version_claim_registry=gate.supersession.STABLE_REGISTRY_REL, permanent_one_use_failed_claim_consumption_reviewed=True))
    go=c.canonical(gate.policy(prep,c.sha(rr),c.sha(pr),c.sha(nr),[4,5]));sg,_,sr,_=fake_authority()
    raw={'go':go,'review':rr,'prepared-review':pr,'native-review':nr,'source-go':sg,'source-review':sr}
    return raw,{k:c.sha(v) for k,v in raw.items()}


def fixture():
    year=2023;period=config.period_named(year);d=period['days'];n=d+199
    clocks=codec.frozen_array(np.arange(n,dtype=np.int64)*config.DAY+period['warmup_start'])
    close=codec.frozen_array(np.ones((n,5),dtype=np.float64)*100)
    decisions=codec.frozen_array(np.arange(d,dtype=np.int64)*config.DAY+period['start'])
    targets={key:codec.frozen_array(np.zeros((d,5,5) if key=='annual_covariance' else (d,5),dtype=np.float64))
        for key in ('annual_covariance','weekly_raw_CS','original_sized_CS',*(config.STRATEGY+'_'+t for t in config.TIERS))}
    targets['decision_us']=decisions
    rows=tuple(dict(symbol=s,close_us=int(at),available_us=int(at),close=100.) for at in clocks for s in ('BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT'))
    sidecar=c.canonical(dict(schema='GENERATED_STORAGE_FIXTURE_ONLY',cells=[]))
    captured=dict(year=year,period=period,clocks=clocks,close=close,decisions=decisions,source_rows=rows,
        events=(),months=(),quality_cells=(),quality_intervals=(),sidecar={},sidecar_raw=sidecar,
        source_identity=entry.contracts()['years']['2023']['source_identity'],contract=entry.contracts()['years']['2023'])
    artifacts={'2023/TARGETS.npz':source.target_blob(targets), '2023/SOURCE_INPUTS.npz':source.target_blob(dict(close_available_us=clocks,close=close)),
        '2023/MINUTE_MARK_PROVENANCE.json':sidecar,'2023/RAW_EVENTS.json':b'[]','2023/TARGET_PROOFS.json':b'{}'}
    prep=fake_preparation();info=prep['years']['2023']
    info.update(array_raw_SHA256={k:c.sha(v.tobytes()) for k,v in targets.items()},source_quality_sidecar_SHA256=c.sha(sidecar),
                source_rows_SHA256=c.jsha(rows),funding_events_SHA256=c.jsha(()))
    for cell in entry.tranche_cells(entry.FIRST6):
        if cell.startswith('2023'):
            binding=source.input_binding(config.cell_named(cell),captured,targets)
            prep['cells'][cell]['input_binding']=binding;prep['cells'][cell]['input_binding_SHA256']=c.jsha(binding)
    for k,v in artifacts.items():prep['artifacts'][k]=dict(SHA256=c.sha(v),bytes=len(v))
    sg,_,sr,_=fake_authority();artifacts.update(SOURCE_STAGE_AUTHORIZATION=sg)
    artifacts.pop('SOURCE_STAGE_AUTHORIZATION');artifacts['SOURCE_STAGE_AUTHORIZATION.json']=sg;artifacts['SOURCE_INDEPENDENT_REVIEW.json']=sr
    raw=c.canonical(prep);entry.validate_preparation_metadata(raw)
    return raw,artifacts,captured


class StopBeforeNative(Exception):pass


def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'positive'
    prep,artifacts,captured=fixture();raw,hashes=bundle(prep);events=[];captured_calls=[]
    # Negative authority serialization still fails under the unchanged guard.
    guard=SourceOnlyGuard()
    try:
        with guard:c.canonical(c.exact_object(raw['go']))
    except SourceBoundaryViolation:pass
    else:raise AssertionError('EXECUTABLE_GO_WRITE_WAS_ALLOWED')
    assert guard.attempts['financial_GO_writes']==1
    # Positive one-use metadata checks are recording-only and revoke on failures.
    cell='2023_CSMOM21_COMMON_TIER_LOW_D'
    claim=c.canonical(dict(cell_id=cell,root_GO_SHA256=hashes['go'],preparation_SHA256=c.sha(prep),code_identity=gate.code_identity()))
    for negative in ('wrongyear','wrongprep','wronggo','wrongcode','replay','revoked'):
        with verified.verify(preparation_raw=prep,cell_id=cell,raw=raw,hashes=hashes,claim_raw=claim) as token:
            kwargs=dict(preparation_raw=prep,year=2023,supplied=dict(raw))
            if negative=='wrongyear':kwargs['year']=2022
            if negative=='wrongprep':kwargs['preparation_raw']=prep+b' '
            if negative=='wronggo':kwargs['supplied']['go']=b'{}'
            if negative=='revoked':verified._LIVE.pop(token._token)
            if negative=='replay':token.consume(**kwargs)
            try:
                if negative=='wrongcode':
                    with patch.object(gate,'code_identity',return_value='a'*64):token.consume(**kwargs)
                else:token.consume(**kwargs)
            except ValueError:pass
            else:raise AssertionError('TOKEN_NEGATIVE_ALLOWED:'+negative)
        assert not verified._LIVE
    with verified.verify(preparation_raw=prep,cell_id=cell,raw=raw,hashes=hashes,claim_raw=claim):
        try:
            with verified.verify(preparation_raw=prep,cell_id=cell,raw=raw,hashes=hashes,claim_raw=claim):pass
        except ValueError as error:assert 'CONFLICTING' in str(error)
        else:raise AssertionError('DUPLICATE_LIVE_CLAIM_TOKEN_ALLOWED')
    assert not verified._LIVE
    with tempfile.TemporaryDirectory(prefix='CS_GENERATED_CLI_ONLY_') as td:
        base=Path(td);preproot=base/'preparation';preproot.mkdir();caseout=base/'case';caseout.mkdir()
        (preproot/'PREPARATION.json').write_bytes(prep)
        for key,value in artifacts.items():
            path=preproot/key;path.parent.mkdir(exist_ok=True);path.write_bytes(value)
        argv=['run_cs.py','--case','--cell-id',cell,'--cpu',str(min(os.sched_getaffinity(0))),'--case-output',str(caseout),
              '--preparation',str(preproot),'--preparation-sha',c.sha(prep)]
        for key,value in raw.items():
            path=base/(key+'.json');path.write_bytes(value);argv+=['--'+key,str(path),'--'+key+'-sha',hashes[key]]
        original_save=run_cs.r.save
        @contextmanager
        def recording_source_context(*args):
            assert current_guard() is not None;events.append('recording_source_context');yield object()
        def capture(year,scope):
            assert current_guard() is not None and year==2023;captured_calls.append(year);events.append('fake_source_capture')
            if mode=='capture_failure':raise ValueError('GENERATED_CAPTURE_FAILURE')
            return captured
        @contextmanager
        def stop_native(*args,**kwargs):
            assert current_guard() is None and not verified._LIVE;events.append('post_guard_native_constructor_sentinel')
            raise StopBeforeNative('GENERATED_STOP_BEFORE_ANY_NATIVE_ACCOUNT_SCOPE_OR_PROVIDER')
            yield
        def storage_save(path,value):
            original_save(path,value)
            if Path(path).name=='WORKER_AUTHORITY_VERIFIED.json':events.append('real_GO_verified_before_guard')
            if Path(path).name=='WORKER_SOURCE_ACCEPTED_BEFORE_ACCOUNT.json':
                events.append('source_accepted_guard_exited')
                m=types.ModuleType('cs_admission');m.admit_case=stop_native;sys.modules['cs_admission']=m
                sys.modules['cs_native']=types.ModuleType('cs_native')
                m=types.ModuleType('saved_native_reconciliation');m.reconcile_saved_native=lambda *a:None;m.checker_sha256=lambda:None
                sys.modules['saved_native_reconciliation']=m
        claim=c.canonical(dict(schema='GENERATED_RECORDING_STORAGE_CLAIM_ONLY',cell_id=cell,root_GO_SHA256=hashes['go'],preparation_SHA256=c.sha(prep),code_identity=gate.code_identity()))
        from contextlib import ExitStack
        original_guard_exit=SourceOnlyGuard.__exit__
        def fail_exit(self,*args):
            result=original_guard_exit(self,*args)
            if mode=='guard_exit_failure':raise ValueError('GENERATED_GUARD_EXIT_FAILURE')
            return result
        with ExitStack() as stack:
            if mode=='loaded_validation_failure':stack.enter_context(patch.object(loader.LoadedInputs,'validate',side_effect=ValueError('GENERATED_LOADED_VALIDATION_FAILURE')))
            if mode=='guard_exit_failure':stack.enter_context(patch.object(SourceOnlyGuard,'__exit__',fail_exit))
            stack.enter_context(patch.object(sys,'argv',argv));stack.enter_context(patch.object(run_cs,'worker_claim',return_value=claim))
            stack.enter_context(patch.object(entry,'admit_source_stage',recording_source_context));stack.enter_context(patch.object(source,'capture_year',capture))
            stack.enter_context(patch.object(run_cs.r,'save',storage_save))
            try:run_cs.main()
            except (StopBeforeNative,ValueError) as error:
                if mode=='positive':assert isinstance(error,StopBeforeNative)
                else:assert 'GENERATED_' in str(error)
            else:raise AssertionError('EXPECTED_BOUNDED_SENTINEL_NOT_REACHED')
        for name in ('cs_admission','cs_native','saved_native_reconciliation'):sys.modules.pop(name,None)
        receipt_name='SOURCE_RECAPTURE_GUARD_RECEIPT.json' if mode=='positive' else 'FAILED_SOURCE_RECAPTURE_GUARD_RECEIPT.json'
        receipt=c.exact_object((caseout/receipt_name).read_bytes())
        assert all(v==0 for v in receipt['forbidden_attempts'].values()),receipt
        assert captured_calls==[2023] and not verified._LIVE and not loader._LIVE
        if mode=='positive':assert events==['real_GO_verified_before_guard','recording_source_context','fake_source_capture','source_accepted_guard_exited','post_guard_native_constructor_sentinel'],events
        else:assert events==['real_GO_verified_before_guard','recording_source_context','fake_source_capture'],events
    print(json.dumps(dict(status='PASS_REAL_FRESH_CLI_GENERATED_EXECUTABLE_GO_UNCHANGED_GUARD', mode=mode, events=events,
        token_negative_cases=7, authority_serialization_negative_counter=1, positive_guard_counters=receipt['forbidden_attempts'],
        seams=['invented_fixture_storage','worker_claim_recording_storage_callback','recording_source_context_and_capture','post_guard_native_constructor_sentinel'],
        actual_source_reads=0,actual_source_scopes=0,historical_scopes=0,providers=0,accounts=0,claims=0,
        runtime_generated_bypass_present=False,annual_history_execution_certified=False),sort_keys=True))

if __name__=='__main__':main()

