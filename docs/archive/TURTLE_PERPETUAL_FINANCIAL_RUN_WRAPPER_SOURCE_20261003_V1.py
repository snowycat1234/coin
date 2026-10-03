"""UNRUN compact START -> unchanged D047 finance checker -> RESULT wrapper.

The same progress task executes the checker. Only protocol/manifest pointers
enter registry source_hashes; the full actual pins remain in ACTUAL_BINDING.
No actual completion is claimed while this caller is still live.
"""
import argparse
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
CHECKER = 'scripts/investment/audit_turtle_perpetual.py'
CHECKER_SHA = '722e48ca19b924d15f8922c13aebf021db8e11145130a97dca4e930e2f93ae53'
ARCHIVE = 'docs/archive/TURTLE_PERPETUAL_FINANCIAL_RUN_WRAPPER_SOURCE_20261003_V1.py'
RUN = STATE / 'd047-turtle-perpetual-financial-20261003-v1'
STATUS = 'PASS_D047_TURTLE_RECORDED_PERPETUAL_ACCOUNTING_NOT_COMPLETE_STRATEGY_NATIVE_OR_LONG_TERM_APR'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, default=RUN / 'ACTUAL_BINDING.json')
    args = parser.parse_args()
    assert os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE / 'v8-clean-env-20261002-v2')
    assert sha(ROOT / GUARD) == GUARD_SHA and sha(__file__) == sha(ROOT / ARCHIVE)
    module_spec = importlib.util.spec_from_file_location('d047_compact_registration_guard', ROOT / GUARD)
    g = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(g)
    before = resources.status(); g.bounded(before)
    g.check(args.binding == RUN / 'ACTUAL_BINDING.json' and RUN.is_dir()
        and {p.name for p in RUN.iterdir()} == {'ACTUAL_BINDING.json'}, 'Fresh exact prebound financial attempt')
    plan, plan_sha = g.small(args.binding)
    plan_path = plan['financial_binding_protocol_path']
    g.small(g.project(plan_path), plan_sha)
    g.check(plan['ready_to_execute'] is True and plan['run_dir'] == str(RUN)
        and plan['checker_sha256'] == sha(ROOT / CHECKER) == CHECKER_SHA
        and plan['wrapper_source'] == ARCHIVE and plan['wrapper_sha256'] == sha(__file__), 'Exact held checker/wrapper')
    g.closed(plan['actual_task_id'])
    spec, protocol_sha = g.small(g.project(plan['protocol_path']), plan['protocol_sha256'])
    actual_path = g.project(plan['actual_report']); g.small(actual_path, plan['actual_report_sha256'])
    output = ROOT / plan['output_path']
    g.check(output.parent == ROOT / 'reports/fast_research' and not output.exists(), 'Exclusive new financial report')
    task_id = os.environ['COIN_TASK_ID']
    experiment = 'D047_TURTLE_RECORDED_FINANCIAL_AUDIT_20261003_V1:' + task_id
    command = [sys.executable, str(ROOT / CHECKER), '--protocol', str(ROOT / plan['protocol_path']),
               '--actual', str(actual_path), '--run-dir', str(RUN), '--output', str(output)]
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=experiment, git_commit=plan['git_commit'],
        data_manifest_hash=spec['input_manifest']['sha256'], protocol_hash=protocol_sha,
        feature_set='RECORDED_TURTLE_LEGS_WALLET_NAV', labels='NONE', model_family='NONE',
        hyperparameters='UNCHANGED_ACCEPTED_1C4B_FINANCE_3600_HANDLEDGER', seed=None,
        thresholds=plan['tolerances'], cost_assumptions='FIXED_BASE27_STRESS43_TWO_UNCONFIRMED_UNIT_SCALES',
        all_folds=plan['period_ids'], success_failure='START_BEFORE_NEW_LEDGER_ARRAY_READ',
        reason_for_next_experiment='Independently check this four-selector accounting attempt',
        result_influenced_later_choice=False, task_id=task_id,
        source_hashes={plan_path: plan_sha, str(args.binding): plan_sha},
        full_source_pin_pointer=dict(protocol=plan_path, ACTUAL_BINDING=str(args.binding), sha256=plan_sha),
        exact_command=command)
    registration_start = append_event(ROOT / 'reports/experiment_registry.jsonl',
        dict(event, event_id=experiment + ':START', event_type='OPERATIONAL_RESEARCH_START'))
    code = 1; error = None; report_sha = None; report_status = None; result = None
    try:
        completed = subprocess.run(command, check=False, timeout=plan['budgets']['wall_seconds'])
        code = completed.returncode
        if output.exists():
            result, report_sha = g.small(output)
            report_status = result['status']
        if code == 0:
            g.check(result is not None and report_status == STATUS and result['binding']['task_id'] == task_id
                and result['binding']['ACTUAL_BINDING_sha256'] == plan_sha
                and result['completed_cases_verified'] == result['financial_case_calls'] == 4,
                'Four actual financial calls, never infer complete calendars or full strategy scope')
    except Exception as failure:
        error = dict(type=type(failure).__name__, reason=str(failure)); code = 1
    finally:
        registration_result = append_event(ROOT / 'reports/experiment_registry.jsonl',
            dict(event, event_id=experiment + ':RESULT', event_type='OPERATIONAL_RESEARCH_RESULT',
                success_failure='PASS_RECORDED_FINANCIAL_SCOPE' if code == 0 else 'FAIL_PRESERVED_ACTUAL_ATTEMPT',
                exit_code=code, output_report=plan['output_path'], output_sha256=report_sha,
                output_status=report_status, failure=error))
        g.write(RUN / 'REGISTRATION.json', dict(created_utc=datetime.now(UTC).isoformat(),
            task_id=task_id, actual_task_completion='LIVE_CALLER_EXTERNAL_CLOSED_TASK_CHECK_REQUIRED',
            checker_sha256=CHECKER_SHA, wrapper_sha256=sha(__file__), ACTUAL_BINDING_sha256=plan_sha,
            registration_start=registration_start, registration_result=registration_result,
            child_exit_code=code, output_report=plan['output_path'], output_report_sha256=report_sha,
            failure=error, resources_before=before, resources_after=resources.status(),
            financial_scope='RECORDED_ONLY_NOT_COMPLETE_STRATEGY_NATIVE_OR_LONG_TERM_APR'))
    print(json.dumps(dict(child_exit_code=code, output_report_sha256=report_sha,
        live_task_id=task_id, external_actual_closed_check_required=True)))
    raise SystemExit(code)


if __name__ == '__main__':
    main()
