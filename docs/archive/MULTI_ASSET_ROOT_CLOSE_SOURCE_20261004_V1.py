"""D050 saved-evidence root acceptance. No source arrays, account replay or staging."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, resource, subprocess, sys, time
import xml.etree.ElementTree as ET
from pathlib import Path
from quant import resources
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event

GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
LOCK = 'state/dataset_lock.json'
LOCK_SHA = '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
PREVIOUS_HEAD = 'd5f17f1ae749875e4e4dd34ef6504c9b1d527c44'
ROLES = {'TARGET', 'REPLAY', 'POOL', 'SOURCE', 'SOURCE_QA', 'N2_MARKET',
         'N2_INDEPENDENT', 'N10_MARKET', 'N10_INDEPENDENT', 'COMPARISON'}
FAILURES = {'TARGET_LAUNCH', 'ACCOUNT_METADATA', 'POOL_STARTUP', 'N2_STARTUP',
            'SOURCE_DIRECTORY', 'SOURCE_QA_V1', 'N10_CONCAT'}
FINANCE = {
    'src/quant/perpetual_account.py': '9a4223d1115add6ed2cce5b695cf6dcd89459daa6918eb61091b188e5ec05754',
    'scripts/investment/perpetual_closing_exempt_account.py': '30e0b41f094e01360aa9415011f2b27b4f49256819b2685c21d2da754f1d1b60',
    'scripts/investment/perpetual_directional.py': '570524281b80109b9a1d07b737831d3f768f308ac465c86e2e403a2415ec02ae',
    'scripts/investment/public_sma_perpetual.py': 'ba9fdacc5856324a16c858c99bc9346efc1be51c2d990af7c28069cf9671e079',
    'scripts/investment/vol_managed_perpetual_target.py': 'e9544541d6e749704f9ea828c98f4c345e95f8c04227548913b5bf87043cc3c0'}

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def identity(record):
    return ((record.get('binding') or {}).get('task_id') or record.get('task_id') or
            (record.get('task') or {}).get('id') or (record.get('actual_task') or {}).get('id'))

def public_path(name):
    p = Path(name)
    if (p.is_absolute() or '..' in p.parts or name == LOCK or
        name == 'reports/experiment_registry.jsonl' or not
        (name in {'AGENTS.md', 'README.md', 'configs/dataset_policy.json'} or
         name.startswith(('scripts/', 'src/', 'tests/', 'protocols/', 'environments/',
                          'third_party/', 'docs/', 'reports/')))):
        raise ValueError('Explicit public ROOT path only: '+name)
    return ROOT/p

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--binding', type=Path, required=True)
    args = parser.parse_args(); assert sha(ROOT/GUARD) == GUARD_SHA
    module_spec = importlib.util.spec_from_file_location('_d050_saved_guard', ROOT/GUARD)
    g = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(g)
    g.check(args.binding.parent == ROOT/'protocols' and
        Path(sys.prefix).resolve() == STATE/'v8-clean-env-20261002-v2', 'Frozen binding and clean bounded environment')
    plan, plan_sha = g.small(args.binding); own_task = os.environ.get('COIN_TASK_ID')
    g.check(own_task and plan['ready_to_execute'] is True and set(plan['roles']) == ROLES, 'Ten actual completed roles')
    g.check(FAILURES <= set(plan['failed_roles']) and sha(ROOT/LOCK) == LOCK_SHA, 'Preserved failures; private lock hash only')
    run = Path(plan['run_dir']); g.check(run.parent == STATE and run.name.startswith('d050-') and not run.exists(), 'Exclusive D050 root metadata')
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    g.check(plan['source_hashes'][own] == sha(__file__), 'Current root helper identity')
    for name, digest in FINANCE.items(): g.check(plan['source_hashes'][name] == sha(ROOT/name) == digest, 'Unchanged D050 finance/risk '+name)
    started = time.monotonic(); before = resources.status(); g.bounded(before); run.mkdir()
    binding = dict(task_id=own_task, source_sha256=sha(__file__), source_hashes=plan['source_hashes'],
                   binding_path=str(args.binding), binding_sha256=plan_sha,
                   git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    rb_sha, _ = g.write(run/'RUN_BINDING.json', binding)
    event = dict.fromkeys(FIELDS); event.update(event_id=own_task+':START', event_type='RESEARCH_ACCEPTANCE_START',
        experiment_id=plan['experiment_id'], task_id=own_task, git_commit=binding['git_commit'], protocol_hash=plan_sha,
        success_failure='START_BEFORE_SAVED_METADATA', hyperparameters=dict(binding_path=str(args.binding)),
        source_hashes=dict(binding_path=str(args.binding), binding_sha256=plan_sha), fits=0,
        reason_for_next_experiment='Accept shared-capital configured-N research; investment NONE')
    append_event(ROOT/'reports/experiment_registry.jsonl', event)
    report = dict(status='FAIL_ROOT_D050_MULTI_ASSET_PORTFOLIO', binding=binding, run_binding_sha256=rb_sha,
        candidate='NO_QUALIFIED_CANDIDATE', investment='CASH', long_term_APR='NOT_EVALUABLE',
        funding_unit_certified=False, native_market_certified=False, global_Top10_certified=False,
        source_or_saved_ledger_arrays_read=False, old_QA_or_accounts_replayed=False, models_fit=0, orders_sent=0,
        GPU=0, locked_consumed=False, local_non_git_source_hashes={LOCK: LOCK_SHA}, own_completion='EXTERNAL_CHECK_AFTER_RETURN')
    error = None
    try:
        records, tasks, verified, source_resolutions = {}, {}, {}, []
        archives = {(v['original_path'], v['sha256']): v['archive_path'] for v in plan['source_archives']}
        def resolve(name, digest):
            if name == LOCK:
                g.check(digest == LOCK_SHA == sha(ROOT/LOCK), 'Exact private lock; excluded from public source map'); return
            path = public_path(name)
            if path.is_file() and sha(path) == digest: selected = name
            else:
                selected = archives.get((name, digest)); g.check(selected is not None, 'Exact consumed-source archive '+name)
                g.check(selected.startswith('docs/archive/'), 'Historical source archive only')
                source_resolutions.append(dict(original_path=name, original_sha256=digest, archive_path=selected))
            g.small(public_path(selected), digest, False)
            g.check(selected not in verified or verified[selected] == digest, 'No conflicting public source identity')
            verified[selected] = digest
        metadata = public_path(plan['metadata_archive']); g.check(not metadata.exists() and metadata.parent == ROOT/'docs/archive'
            and metadata.name.startswith('MULTI_ASSET'), 'Exclusive D050 actual metadata archive'); metadata.mkdir()
        for group, code in ((plan['roles'], 0), (plan['failed_roles'], 1)):
            for role, item in group.items():
                value, digest = g.small(g.project(item['path']), item['sha256'])
                g.check(value['status'] == item['status'] and identity(value) == item['task_id'], 'Exact actual receipt '+role)
                tasks[role] = g.closed(item['task_id'], code); records[role] = value; verified[item['path']] = digest
                (metadata/(role+'-TASK.json')).write_bytes(Path(tasks[role]['path']).read_bytes())
                verified[(metadata/(role+'-TASK.json')).relative_to(ROOT).as_posix()] = tasks[role]['sha256']
                if item.get('run_binding_path'):
                    rb, h = g.small(item['run_binding_path'], item['run_binding_sha256'])
                    g.check(rb['task_id'] == item['task_id'] and rb == value['binding'], 'Actual pre-run binding '+role)
                    g.check(value.get('run_binding_sha256', h) == h, 'Receipt RUN_BINDING digest '+role)
                    destination = metadata/(role+'-RUN_BINDING.json'); destination.write_bytes(Path(item['run_binding_path']).read_bytes())
                    verified[destination.relative_to(ROOT).as_posix()] = h
                for name, h in (value.get('binding') or {}).get('source_hashes', {}).items(): resolve(name, h)
        g.check(len({tasks[k]['task']['id'] for k in ROLES}) == len(ROLES), 'Distinct actually completed roles')
        for ancestor, descendant in plan['chronology_edges']:
            g.check(tasks[ancestor]['task']['ended_at'] <= tasks[descendant]['task']['started_at'], 'Real causal task order '+ancestor+' -> '+descendant)
        for role in ('TARGET', 'REPLAY'):
            r = records[role]; g.check(r['test_exit_code'] == 0 and r['source_bytes_unchanged'] is True and
                r['junit_counts'] == dict(tests=1 if role == 'TARGET' else 4, errors=0, failures=0, skipped=0), 'Fresh synthetic scope '+role)
            junit = Path(r['run_dir'])/'junit.xml'; g.small(junit, r['junit_sha256'], False)
            tree = ET.parse(junit).getroot()
            g.check({k: sum(int(s.get(k, 0)) for s in tree.iter('testsuite')) for k in
                ('tests', 'errors', 'failures', 'skipped')} == r['junit_counts'], 'Actual JUnit '+role)
            destination = metadata/(role+'-JUNIT.xml'); destination.write_bytes(junit.read_bytes())
            verified[destination.relative_to(ROOT).as_posix()] = r['junit_sha256']
        pool, source, qa = (records[k] for k in ('POOL', 'SOURCE', 'SOURCE_QA'))
        g.check(pool['score_payloads_read'] == 0 and len(pool['symbols']) == 10 and pool['full_historical_universe_certified'] is False,
                'Actual pre-score limited-universe pool, no global Top10 claim')
        g.check(source['completed_source_files'] == 30 and source['source_bytes_unchanged'] is True and qa['source_only'] is True
            and qa['completed_files'] == 100 and qa['newly_verified_files'] == 80 and qa['reused_accepted_files'] == 20
            and qa['pool_receipt_sha256'] == plan['roles']['POOL']['sha256'], '100 source roles: 80 new and 20 accepted, not unit/native certification')
        g.check(source['symbols'] == qa['symbols'] and set(source['symbols']) == set(pool['symbols']) and
            qa['selected_symbols'] == pool['symbols'] and
            source['pool_receipt']['sha256'] == plan['roles']['POOL']['sha256'], 'Frozen pre-score pool retained unchanged')
        summaries = []
        for prefix, count in (('N2', 2), ('N10', 10)):
            market, audit = records[prefix+'_MARKET'], records[prefix+'_INDEPENDENT']
            g.check(market['completed_cases'] == market['complete_calendar_cases'] == audit['completed_cases_verified'] == 4
                and audit['financial_case_calls'] == audit['completed_full_calendar_cases_verified'] == 4
                and audit['incomplete_or_halted_cases_verified'] == 0 and market['actual_calendar_days'] == 30
                and market['initial_capital_per_comparison_account_USDT'] == 10000
                and audit['actual_report_sha256'] == plan['roles'][prefix+'_MARKET']['sha256'], 'Four complete shared-capital accounts '+prefix)
            g.check(g.canonical_reports(audit['binding']['actual_reports']) ==
                {str((ROOT/plan['roles'][prefix+'_MARKET']['path']).resolve()): plan['roles'][prefix+'_MARKET']['sha256']}
                and audit['verified_source_hashes'] == market['binding']['source_hashes'], 'Exact independently checked producer '+prefix)
            g.check(market['orders_sent'] == market['GPU'] == market['model_fits'] == 0 and
                not market['locked_consumed'] and not market['funding_unit_certified'] and
                not market['native_filters_certified'], 'Research boundaries '+prefix)
            for state in (market['resources_before'], market['resources_after'], audit['resources_before'], audit['resources_after']): g.bounded(state)
            original = {c['id']: c for c in market['cases']}; independent = {c['id']: c for c in audit['cases']}
            g.check(set(original) == set(independent) and len(original) == 4, 'Same four scenario identities')
            for key, case in original.items():
                s = case['summary']; a = independent[key]
                g.check(len(case['symbols']) == count and s['contract']['symbols'] == case['symbols'] and s['mode'] == 'LONG_ONLY'
                    and s['terminal_cash_realized'] is True and a['complete_calendar_verified'] is True
                    and s['completed_minutes'] == s['required_minutes'] == 43200 and s['unpaid_liability'] == 0
                    and all(p['quantity'] == 0 for p in s['positions'].values()), 'Configured pool, same HOLD, full terminal valuation')
                g.check(case['symbols'] == (['BTCUSDT', 'ETHUSDT'] if prefix == 'N2' else pool['symbols']), 'Explicit account symbol order preserved')
                for field in ('net_PnL', 'gross_PnL_same_quantities', 'fees_USDT', 'execution_cost_USDT', 'funding_USDT'):
                    g.near(s[field], a['summary'][field], audit['tolerances']['cash_USDT'])
                summaries.append(dict(id=key, symbols=case['symbols'], net_USDT=s['net_PnL'], gross_USDT=s['gross_PnL_same_quantities'],
                    fees_USDT=s['fees_USDT'], execution_USDT=s['execution_cost_USDT'], funding_USDT=s['funding_USDT'],
                    all_observation_MDD=s['all_observation_max_drawdown'], realized_risk_not_equalized=True))
        comparison = records['COMPARISON']; g.check(len(comparison['pairs']) == 4 and comparison['actual_days'] == 30
            and comparison['control']['sha256'] == plan['roles']['N2_MARKET']['sha256']
            and comparison['pool']['sha256'] == plan['roles']['N10_MARKET']['sha256'], 'Same saved eight accounts paired, no replay')
        for name, digest in {**plan['source_hashes'], **plan['project_files']}.items(): resolve(name, digest)
        resolve(args.binding.relative_to(ROOT).as_posix(), plan_sha)
        history = []
        for item in plan['historical_git_sources']:
            g.check(item['commit'] == PREVIOUS_HEAD and item['path'] != LOCK, 'Accepted D049 Git source, no private body')
            data = subprocess.check_output(['git', 'cat-file', 'blob', item['commit']+':'+item['path']], cwd=ROOT)
            g.check(hashlib.sha256(data).hexdigest() == item['sha256'], 'Historical exact Git bytes '+item['path']); history.append(item)
        ownership = []
        for name in plan['owned_STATE_directories']:
            path = Path(name); g.check(path.parent == STATE and path.name.startswith('d050-') and path.is_dir() and not path.is_symlink(), 'Explicit D050 ownership only')
            size = 0
            for current, dirs, files in os.walk(path, followlinks=False):
                g.check(not any((Path(current)/v).is_symlink() for v in dirs+files), 'No ownership symlink')
                size += sum((Path(current)/v).stat().st_size for v in files)
            ownership.append(dict(path=name, bytes=size))
        g.check(run.as_posix() in plan['owned_STATE_directories'] and
            len(plan['owned_STATE_directories']) == len(set(plan['owned_STATE_directories'])), 'Distinct exact module ownership including live root')
        g.check(sum(v['bytes'] for v in ownership) <= plan['maximum_owned_STATE_bytes'], 'Registered module stat-only capacity')
        g.check(sha(ROOT/LOCK) == LOCK_SHA, 'Final private lock hash only')
        report.update(status='PASS_ROOT_D050_CONFIGURED_N_SHARED_PORTFOLIO_RESEARCH_NOT_INVESTMENT_OR_APR',
            roles=tasks, source_hashes=verified, source_resolutions=source_resolutions, historical_git_sources=history,
            saved_case_summaries=summaries, paired_comparison= comparison['pairs'], ownership=ownership,
            pool_UNKNOWN_count=len(pool['unknown_candidates']), own_completion='EXTERNAL_CHECK_AFTER_RETURN')
    except Exception as caught:
        error = caught; report['failure'] = dict(type=type(caught).__name__, reason=str(caught))
    finally:
        after = resources.status(); g.bounded(after); report.update(resources_before=before, resources_after=after,
            elapsed_seconds=time.monotonic()-started, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        out_sha, _ = g.write(public_path(plan['output_path']), report)
        if error is None:
            portable = dict(status='D050_ACTUAL_SHARED_CAPITAL_RESEARCH_SOURCE_BOUND_NOT_INVESTMENT', source_hashes=dict(report['source_hashes']),
                source_resolutions=report['source_resolutions'], historical_git_sources=report['historical_git_sources'],
                selected_project_changes=plan['project_files'], local_non_git_source_hashes={LOCK: LOCK_SHA}, root_task_id=own_task)
            portable['source_hashes'][plan['output_path']] = out_sha
            g.write(public_path(plan['portable_output_path']), portable)
        append_event(ROOT/'reports/experiment_registry.jsonl', dict(event, event_id=own_task+':RESULT', event_type='RESEARCH_ACCEPTANCE_RESULT',
            success_failure=report['status'], artifact_path=plan['output_path'], artifact_sha256=out_sha))
    if error: raise error
    print(json.dumps(dict(status=report['status'], report_sha256=out_sha)))

if __name__ == '__main__': main()
