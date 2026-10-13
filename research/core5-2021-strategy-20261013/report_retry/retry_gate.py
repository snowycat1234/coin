"""Fail-closed exact-code gate for one renderer-only REPORT retry; no restore."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ORIGINAL_HERE = HERE.parent / 'coin_2021_strategy_postrun_20261013'
sys.path.insert(0, str(ORIGINAL_HERE))
import gate
import provenance

sha = provenance.sha
FILES = frozenset({'build_report.py', 'retry_gate.py', 'retry_controller.py',
                   'test_retry.py', 'FULL_SUMMARY_RENDER_FIXTURE.json', 'PROTOCOL.md'})
FIXED_ORIGINAL_PINS = {'REVIEWED_POSTRUN_CODE.json': 'df3b065c99977ebe59a617b2aaa11c244bb006fc5509b000b5a43494e4bb70e4', 'POSTRUN_GO.json': '2a065efae889d748ad830080f21aa8926dd3db80810f70443ce36a0ff2bb266e', 'TERMINAL_INPUTS.json': '3f9bf930d0a06b41521a5114519ffda79c2edd70b7552bc4613d8d5eb9f4a552', 'REPORT_RESOURCE_RECEIPTS.json': 'deba182b05c0e902a215e1b11f9ac87e56b747c258cf8da82c40952949d1ded9', 'REPORT.log': 'd87b3ed0d388474c1d99962e681b4d1b37c48e023d68c15c9c2b320ff9c27380'}
ORIGINAL_FILES = frozenset(['AUDIT.log', 'AUDIT_RESOURCE_RECEIPTS.json', 'POSTRUN_GO.json', 'POSTRUN_REVIEW_RECEIPT.json', 'PREPARATION_RECEIPT.json', 'PROTOCOL.md', 'REPORT.log', 'REPORT_RESOURCE_RECEIPTS.json', 'REVIEWED_POSTRUN_CODE.json', 'SHA256SUMS.txt', 'SYNTHETIC_TEST_RESULTS.txt', 'TERMINAL_INPUTS.json', 'audit_all.py', 'build_report.py', 'cold_audit.py', 'gate.py', 'provenance.py', 'receipts/Y2021_EXACTHALF_FINE_ORIGINAL.json', 'receipts/Y2021_SMA200_10PCT_FINE_ORIGINAL.json', 'receipts/Y2021_STATIC50_FINE_ORIGINAL.json', 'receipts/Y2021_VOL_MATCHED_FINE_ORIGINAL.json', 'test_observer.py', 'test_report.py'])

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify_manifest(here: Path = HERE, original: Path = ORIGINAL_HERE) -> dict:
    manifest = read(here / 'RETRY_MANIFEST.json')
    if (manifest.get('kind') != 'SINGLE_RENDERER_ONLY_REPORT_RETRY'
            or set(manifest.get('files_SHA256', {})) != FILES
            or set(manifest.get('preserved_original_files_SHA256', {})) != ORIGINAL_FILES
            or manifest.get('approved_stages') != ['REPORT'] or manifest.get('maximum_REPORT_attempts') != 1
            or manifest.get('case_ids') != list(provenance.CASE_IDS)
            or manifest.get('original_input_locator') != str(original.relative_to(here.parent))
            or manifest.get('exclusive_output_locator') != str(here.relative_to(here.parent))
            or any(manifest.get(key) != 0 for key in ('historical_runs', 'AUDIT_runs', 'cold_restores', 'financial_advances'))
            or any(manifest['preserved_original_files_SHA256'].get(key) != value for key, value in FIXED_ORIGINAL_PINS.items())):
        raise RuntimeError('Renderer retry manifest identity or original fixed pins differ')
    for root, files in ((here, manifest['files_SHA256']), (original, manifest['preserved_original_files_SHA256'])):
        for name, digest in files.items():
            path = root / name
            if path.is_symlink() or sha(path) != digest:
                raise RuntimeError('Renderer retry pinned bytes changed: ' + name)
    failure = read(original / 'REPORT_RESOURCE_RECEIPTS.json')
    worker = failure.get('per_observer', {}).get('FULL_FOUR_CASE_REPORT', {})
    if (failure.get('stage') != 'REPORT' or failure.get('status') != 'STOP_PARTIAL'
            or worker.get('exit_code') != 1 or worker.get('stop_reason') is not None
            or 'TypeError: unsupported format string passed to dict.__format__' not in (original / 'REPORT.log').read_text()
            or any((original / name).exists() for name in ('RESULTS_COMPACT.json', 'SUMMARY.md'))):
        raise RuntimeError('Original stopped renderer-only failure evidence differs')
    prep = read(here / 'PREPARATION_RECEIPT.json')
    if (prep.get('status') != 'PASS_PURE_SYNTHETIC_PREPARATION'
            or prep.get('manifest_SHA256') != sha(here / 'RETRY_MANIFEST.json')
            or prep.get('synthetic_test_results_SHA256') != sha(here / 'SYNTHETIC_TEST_RESULTS.txt')
            or prep.get('failed_tests') != 0 or prep.get('tests_run', 0) <= 0
            or any(prep.get(key) != 0 for key in ('report_executions', 'AUDIT_executions', 'financial_advances', 'cold_restores'))):
        raise RuntimeError('Exact passing synthetic preparation required')
    return manifest


def ensure_unstarted(here: Path = HERE) -> None:
    if any((here / name).exists() for name in ('SINGLE_RETRY_STARTED.json', 'REPORT_RESOURCE_RECEIPTS.json', 'REPORT.log', 'RESULTS_COMPACT.json', 'SUMMARY.md')):
        raise FileExistsError('Single renderer retry already started or has outputs; never repeat or overwrite')


def verify_retry_go(here: Path = HERE, original: Path = ORIGINAL_HERE, *, worker: bool = False) -> dict:
    manifest = verify_manifest(here, original)
    review_path, go_path = here / 'RETRY_REVIEW_RECEIPT.json', here / 'RETRY_GO.json'
    review, go = read(review_path), read(go_path)
    manifest_sha = sha(here / 'RETRY_MANIFEST.json')
    if (review.get('status') != 'PASS_INDEPENDENT_RENDERER_ONLY_RETRY_REVIEW'
            or review.get('manifest_SHA256') != manifest_sha
            or review.get('preparation_receipt_SHA256') != sha(here / 'PREPARATION_RECEIPT.json')
            or review.get('financial_and_stream_function_AST_unchanged') is not True
            or any(review.get(key) != 0 for key in ('report_executions', 'AUDIT_executions', 'financial_advances', 'cold_restores'))):
        raise RuntimeError('Independent exact renderer retry code review required')
    original_pins = manifest['preserved_original_files_SHA256']
    if (go.get('parent_GO') is not True or go.get('approved_stages') != ['REPORT']
            or go.get('maximum_REPORT_attempts') != 1 or go.get('manifest_SHA256') != manifest_sha
            or go.get('review_receipt_SHA256') != sha(review_path)
            or go.get('preparation_receipt_SHA256') != sha(here / 'PREPARATION_RECEIPT.json')
            or go.get('exclusive_output_locator') != manifest['exclusive_output_locator']
            or go.get('original_input_locator') != manifest['original_input_locator']
            or go.get('preserved_original_files_SHA256') != original_pins):
        raise RuntimeError('Explicit parent renderer-only retry GO required')
    gate.verify_observer_go('REPORT', here=original)
    if worker:
        marker = read(here / 'SINGLE_RETRY_STARTED.json')
        if (marker.get('retry_GO_SHA256') != sha(go_path) or marker.get('manifest_SHA256') != manifest_sha
                or marker.get('review_receipt_SHA256') != sha(review_path)
                or marker.get('maximum_REPORT_attempts') != 1
                or (here / 'REPORT_RESOURCE_RECEIPTS.json').exists()):
            raise RuntimeError('Exact exclusive retry start marker required')
    else:
        ensure_unstarted(here)
    return {'retry_manifest_SHA256': manifest_sha, 'retry_review_receipt_SHA256': sha(review_path),
            'retry_GO_SHA256': sha(go_path), 'retry_preparation_receipt_SHA256': sha(here / 'PREPARATION_RECEIPT.json'),
            'original_input_locator': manifest['original_input_locator'], 'exclusive_output_locator': manifest['exclusive_output_locator'],
            'preserved_original_files_SHA256': original_pins, 'maximum_REPORT_attempts': 1,
            'historical_runs': 0, 'AUDIT_runs': 0, 'cold_restores': 0, 'financial_advances': 0}


def require_bounded_worker() -> dict:
    if (os.environ.get('COIN_FULL2021_RENDERER_RETRY_BOUNDED') != '1'
            or os.environ.get('COIN_FULL2021_RENDERER_RETRY_GO_SHA256') != sha(HERE / 'RETRY_GO.json')):
        raise RuntimeError('Renderer retry must run through its reviewed one-shot bounded controller')
    return verify_retry_go(worker=True)
