"""Finite metadata preparation/binding for the accepted continuous 91D experiment."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
PREFIX = 'MULTI_ASSET_CONTINUOUS_91D_'
SUFFIX = '_20261004_V1.json'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'bind'))
    parser.add_argument('--recipe', choices=('TWO_CONTROL', 'TEN_EQUAL', 'TEN_INVERSE'))
    parser.add_argument('--financial-revision', choices=('1', '2'), default='1')
    args = parser.parse_args()
    assert os.environ.get('COIN_TASK_ID')
    from scripts.investment.multi_asset_financial_audit import calendar_scope
    if args.mode == 'prepare':
        from scripts.investment.multi_asset_data import compose_continuous_manifest
        nov_ref = dict(path=str(STATE/'d054-multiasset-november-source-acceptance-20261004-v2/INPUT_MANIFEST.json'),
            sha256='77881c6e61aaf9d23a8e369493bc58e51c5846034e5171b0f0ea1c06d78bc87d')
        assert sha(nov_ref['path']) == nov_ref['sha256']
        nov = read(nov_ref['path'])
        oct_ref = nov['warmup_manifest']
        assert sha(oct_ref['path']) == oct_ref['sha256']
        sep_ref = read(oct_ref['path'])['warmup_manifest']
        assert sha(sep_ref['path']) == sep_ref['sha256']
        manifest = compose_continuous_manifest([sep_ref, oct_ref, nov_ref])
        run = STATE/'d055-continuous-input-binding-20261004-v1'
        run.mkdir()
        manifest_path = run/'INPUT_MANIFEST.json'
        write(manifest_path, manifest)
        independent_sha = sha(ROOT/'scripts/investment/multi_asset_financial_audit.py')
        comparer_sha = sha(ROOT/'scripts/investment/compare_multi_asset_portfolios.py')
        protocols = {}
        for recipe in ('TWO_CONTROL', 'TEN_EQUAL', 'TEN_INVERSE'):
            prior = read(ROOT/('protocols/MULTI_ASSET_NOVEMBER_'+recipe+SUFFIX))
            current = dict(prior)
            for name, digest in prior['source_hashes'].items():
                if name not in ('scripts/investment/multi_asset_data.py', 'scripts/investment/multi_asset_portfolio.py'):
                    assert sha(ROOT/name) == digest, 'Unchanged finance/target source: '+name
            current.update(experiment_id='D055-CONTINUOUS-91D-'+recipe+'-20261004',
                start='2024-09-01T00:00:00+00:00', end_exclusive='2024-12-01T00:00:00+00:00',
                period_days=91, account_path='CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D',
                data_role='SEEN_DEVELOPMENT_CONTINUOUS_ACCEPTED_THREE_MONTH_MANIFEST',
                data_role_note='One initial full10k wallet across all three months; never stitched fresh monthly NAV.',
                warmup='One accepted Feb-Aug70 daily; three scoring months reduced causally, not restarted.',
                data_manifest=dict(path=str(manifest_path), sha256=sha(manifest_path)),
                source_hashes={name:sha(ROOT/name) for name in prior['source_hashes']},
                independent_reference_pre_market_sha256=independent_sha,
                economic_comparer_pre_market_sha256=comparer_sha,
                budget=dict(owned_bytes=100_000_000 if recipe=='TWO_CONTROL' else 250_000_000,
                    wall_seconds=1800, peak_RSS_bytes=3_000_000_000),
                question='Do fixed pool/allocation gains survive a real continuous 91D shared wallet, risk, funding ownership and capacity exit?',
                success_rule='12 actual complete or truthfully stopped accounts, 12 independent financial calls where complete; no positive-return requirement.',
                created_utc=datetime.now(UTC).isoformat())
            current.pop('source_acceptance', None)
            current['source_acceptances'] = manifest['monthly_acceptances']
            current['research_budget'] = dict(models_fit=0,HPO=0,new_actual_accounts=12,
                new_independent_accounts=12,total_new_STATE_bytes=1_000_000_000,new_recipes=0)
            path = ROOT/('protocols/'+PREFIX+recipe+SUFFIX)
            write(path, current)
            protocols[recipe] = dict(path=str(path), sha256=sha(path), required_scope=calendar_scope(current))
        report = dict(status='BOUND_THREE_ALREADY_ACCEPTED_MONTHS_FOR_CONTINUOUS_91D_NOT_NEW_QA_OR_ECONOMICS',
            task_id=os.environ['COIN_TASK_ID'], created_utc=datetime.now(UTC).isoformat(),
            metadata_source_sha256=sha(__file__), manifest=dict(path=str(manifest_path),sha256=sha(manifest_path)),
            monthly_manifests=manifest['monthly_manifests'], protocols=protocols,
            new_downloads=0,new_source_QA=0,new_market_accounts=0,models_fit=0,
            funding_unit_certified=False,native_Bybit_certified=False,locked_consumed=False)
        write(ROOT/('reports/fast_research/'+PREFIX+'INPUT_BINDING'+SUFFIX),report)
        print(json.dumps(dict(status=report['status'],manifest_sha256=sha(manifest_path),protocols=protocols)))
    else:
        assert args.recipe
        recipe = args.recipe
        protocol_path = 'protocols/'+PREFIX+recipe+SUFFIX
        actual_path = 'reports/fast_research/'+PREFIX+recipe+SUFFIX
        spec, actual = read(ROOT/protocol_path), read(ROOT/actual_path)
        assert actual['actual_calendar_days']==91 and actual['completed_cases']==actual['complete_calendar_cases']==4
        assert actual['account_path']==spec['account_path']=='CONTINUOUS_SHARED_ACCOUNT_SEP_NOV_91D'
        producer_task_path = STATE/('task-progress/task-'+actual['binding']['task_id']+'.json')
        task = read(producer_task_path)
        assert task['status']=='completed' and task['exit_code']==0 and task.get('ended_at')
        assert actual['binding']==read(Path(actual['run_dir'])/'RUN_BINDING.json')
        assert actual['binding']['source_hashes']==spec['source_hashes']
        checker_sha = sha(ROOT/'scripts/investment/multi_asset_financial_audit.py')
        correction = None
        if args.financial_revision == '1':
            assert checker_sha==spec['independent_reference_pre_market_sha256']
        else:
            old_path=ROOT/'docs/archive/MULTI_ASSET_CONTINUOUS_FINANCIAL_INPUT_FAILED_SOURCE_20261004_V1.py'
            old=old_path.read_bytes()
            new=(ROOT/'scripts/investment/multi_asset_financial_audit.py').read_bytes()
            original_line=b"    daily = pool['source_records']"
            fixed_line=b"    daily = [r for r in pool['source_records'] if r['symbol'] in value['symbols']]"
            assert old.count(original_line)==1 and old.replace(original_line,fixed_line,1)==new
            assert sha(old_path)==spec['independent_reference_pre_market_sha256']==\
                '21097539b1a2ca2c70a9fdc4223c3bcb1a4ed26b4e8cb7baff05708f47d10076'
            assert checker_sha=='db1332b4a6284aeb6d1caacf2191127b8900eedc340b2d9431e17223c0411339'
            failure_path=ROOT/'reports/fast_research/MULTI_ASSET_CONTINUOUS_91D_TWO_CONTROL_INDEPENDENT_20261004_V1.json'
            failure=read(failure_path)
            failed_task_path=STATE/('task-progress/task-'+failure['binding']['task_id']+'.json')
            failed_task=read(failed_task_path)
            assert failure['status']=='FAIL_CONFIGURED_N_PERPETUAL_RECORDED_ACCOUNTING' and\
                failure['completed_cases_verified']==0 and failed_task['status']=='failed' and failed_task['exit_code']==1
            correction=dict(original_pre_market_checker_sha256=sha(old_path),failed_report=str(failure_path),
                failed_report_sha256=sha(failure_path),failed_task_id=failed_task['id'],
                failed_task_sha256=sha(failed_task_path),exact_one_line_byte_replacement_verified=True,
                correction='FILTER_UNUSED_POOL_CANDIDATE_DAILY_METADATA_TO_ORIGINAL_FROZEN_SOURCE_SYMBOLS',
                producer_protocol_changed=False,financial_target_and_tolerance_bytes_changed=False,
                corrected_checker_pinned_before_new_financial_payload=True)
        prior_plan = read(STATE/'d054-november-ten-equal-financial-20261004-v1/ACTUAL_BINDING.json')
        source_hashes=dict(prior_plan['source_hashes'])
        source_hashes['scripts/investment/multi_asset_financial_audit.py']=checker_sha
        for name,digest in source_hashes.items():
            assert sha(ROOT/name)==digest, 'Independent helper changed: '+name
        plan=dict(prior_plan, checker_sha256=checker_sha, source_hashes=source_hashes,
            protocol_path=protocol_path,protocol_sha256=sha(ROOT/protocol_path),
            actual_report=actual_path,actual_report_sha256=sha(ROOT/actual_path),
            actual_task_id=task['id'],
            actual_closed_task=dict(path=str(producer_task_path),sha256=sha(producer_task_path),task=task),
            producer_run_binding_sha256=sha(Path(actual['run_dir'])/'RUN_BINDING.json'),
            required_scope=calendar_scope(spec),strategy=spec['strategy'],allocation=spec['allocation'],
            audit_scope='CONTINUOUS_91D_RECORDED_SHARED_WALLET_TARGETS_BOUNDARY_COUPONS_AND_FINAL_INVENTORY',
            metadata_scope='New 91D producer actual closed0 and same pre-market-pinned independent source; no old QA/account replay.',
            budgets=dict(new_owned_bytes=100_000,wall_seconds=1800,peak_RSS_bytes=1_500_000_000),
            created_utc=datetime.now(UTC).isoformat())
        if correction:
            plan['correctness_repair']=correction
            plan['metadata_scope']='Original checker pinned pre-market; exact one-line metadata-only repair after source-gate failure. Corrected checker pinned before new financial payload; no producer or financial math change.'
        run=STATE/('d055-continuous-'+recipe.lower().replace('_','-')+'-financial-20261004-v'+args.financial_revision)
        run.mkdir()
        write(run/'ACTUAL_BINDING.json',plan)
        print(json.dumps(dict(recipe=recipe,plan=str(run/'ACTUAL_BINDING.json'),sha256=sha(run/'ACTUAL_BINDING.json'))))


if __name__=='__main__':
    main()
