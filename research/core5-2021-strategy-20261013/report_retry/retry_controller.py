"""One exclusive resource-checked REPORT retry using original bounded helpers."""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ORIGINAL_HERE = HERE.parent / 'coin_2021_strategy_postrun_20261013'
sys.path.insert(0, str(ORIGINAL_HERE))
import audit_all as bounded
import retry_gate


def write_new(path: Path, value) -> None:
    with path.open('x', encoding='utf-8') as file:
        json.dump(value, file, indent=2, sort_keys=True, allow_nan=False)
        file.write('\n')


def main() -> None:
    if sys.flags.optimize:
        raise RuntimeError('Frozen source assertions must remain enabled')
    binding = retry_gate.verify_retry_go()
    go_path = HERE / 'RETRY_GO.json'
    go_text, go_sha = go_path.read_text(), bounded.sha(go_path)
    if __import__('hashlib').sha256(go_text.encode()).hexdigest() != go_sha:
        raise RuntimeError('Retry GO changed while capturing authorization')
    guard, shared = bounded.load_resource_helpers()
    receipt = None
    failed = True
    with shared.controller_lock():
        retry_gate.ensure_unstarted()
        binding = retry_gate.verify_retry_go()
        admission = bounded.resource_admission(guard, shared)
        write_new(HERE / 'SINGLE_RETRY_STARTED.json', {
            'retry_GO_SHA256': go_sha, 'manifest_SHA256': binding['retry_manifest_SHA256'],
            'review_receipt_SHA256': binding['retry_review_receipt_SHA256'],
            'maximum_REPORT_attempts': 1, 'fresh_resource_admission': admission})
        names = ('COIN_FULL2021_RENDERER_RETRY_BOUNDED', 'COIN_FULL2021_RENDERER_RETRY_GO_SHA256')
        previous = {name: os.environ.get(name) for name in names}
        try:
            os.environ[names[0]], os.environ[names[1]] = '1', go_sha
            with (HERE / 'REPORT.log').open('x', encoding='utf-8') as log, redirect_stdout(log):
                receipt = bounded.run_bounded([sys.executable, str(HERE / 'build_report.py')], guard, shared)
            retry_gate.verify_retry_go(worker=True)
            if bounded.sha(go_path) != go_sha:
                raise RuntimeError('Retry GO changed during one-shot REPORT')
            if receipt['exit_code'] != 0 or receipt['stop_reason'] is not None:
                raise RuntimeError('Bounded renderer retry failed; this retry directory is terminal')
            if any(not (HERE / name).is_file() for name in ('RESULTS_COMPACT.json', 'SUMMARY.md')):
                raise RuntimeError('One-shot renderer retry did not produce both outputs')
            failed = False
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            write_new(HERE / 'REPORT_RESOURCE_RECEIPTS.json', {
                'status': 'STOP_PARTIAL' if failed else 'ALL_OBSERVERS_FINISHED', 'stage': 'REPORT',
                'case_ids': list(bounded.CASE_IDS), 'per_observer': {'FULL_FOUR_CASE_REPORT': receipt} if receipt is not None else {},
                'maximum_REPORT_attempts': 1, 'unstarted_observer_ids': [],
                'financial_advances': 0, 'historical_wallets_opened': 0, 'AUDIT_runs': 0, 'cold_restores': 0,
                'renderer_only_retry_binding': binding, 'retry_GO_SHA256': go_sha, 'retry_GO_text': go_text,
                'postrun_GO_SHA256': bounded.sha(ORIGINAL_HERE / 'POSTRUN_GO.json')})
    print('SINGLE_RENDERER_ONLY_REPORT_RETRY_FINISHED', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent-retry-go', action='store_true')
    args = parser.parse_args()
    if not args.parent_retry_go:
        parser.error('Explicit reviewed --parent-retry-go is required')
    main()
