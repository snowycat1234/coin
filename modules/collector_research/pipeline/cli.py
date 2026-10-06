from __future__ import annotations
import argparse
import importlib
import json
import os
import platform
import sys
from pathlib import Path
from .common import E, REPORTS, WORK, bounds, dump, exclusive_lock, init_dirs, log, research_config


def doctor() -> dict:
    bounds()
    required = ['numpy', 'pandas', 'requests'] + (['pyarrow'] if E('TABLE_FORMAT') == 'parquet' else [])
    versions = {}
    for name in required:
        try:
            module = importlib.import_module(name)
        except ImportError:
            raise RuntimeError(f'Missing {name}. Run: bash setup_python.sh') from None
        versions[name] = getattr(module, '__version__', 'UNKNOWN')
    if E('TABLE_FORMAT') not in ('parquet', 'csv.gz'):
        raise ValueError('TABLE_FORMAT must be parquet or csv.gz')
    from .common import disk_guard
    disk_guard()
    result = dict(status='PASS_LOCAL_PREFLIGHT_NETWORK_NOT_CERTIFIED', python=sys.version, platform=platform.platform(),
                  dependencies=versions, work_dir=str(WORK), torch_required_for_collection=False,
                  config=research_config(), existing_proxy_configured=bool(os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY')))
    dump(result, REPORTS / 'source_audit.json')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Historical collector by default; no automatic neural training or account actions')
    parser.add_argument('command', nargs='?', default='collect', choices=['plan', 'doctor', 'collect', 'normalize', 'verify', 'labels', 'train', 'research', 'export', 'report'])
    parser.add_argument('--include-raw', action='store_true', help='Include verified raw archives in portable dataset export')
    parser.add_argument('--output', type=Path, help='Export ZIP path (must not exist)')
    args = parser.parse_args()
    init_dirs()
    # Thread bounds must be set before importing numpy, torch or XGBoost.
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = E('NUM_THREADS')
    try:
        with exclusive_lock():
            bounds()
            if args.command == 'plan':
                from .download import planned_jobs
                jobs = planned_jobs()
                result = dict(status='PLAN_NO_NETWORK_NO_MARKET_BYTES_READ', jobs=len(jobs),
                              funding_unit='UNKNOWN', training_automatic=False, config=research_config(),
                              examples=[j.record() for j in jobs[:4]])
            elif args.command == 'doctor':
                result = doctor()
            elif args.command == 'collect':
                doctor()
                from .download import collect
                from .normalize import normalize
                from .report import report
                collect(); normalize()
                result = dict(report=report(), status='COLLECTED_AVAILABLE_DATA_AND_AUDITED_NO_TRAINING')
            elif args.command == 'normalize':
                doctor()
                from .normalize import normalize
                from .report import report
                normalize()
                result = dict(report=report(), status='NORMALIZED_NO_NETWORK_NO_TRAINING')
            elif args.command == 'verify':
                from .normalize import verify_dataset
                result = verify_dataset()
                result = dict(status='VERIFIED', files=len(result['artifacts']))
            elif args.command == 'labels':
                from .make_labels import make_labels
                result = make_labels()
                result = {k: v for k, v in result.items() if k != 'files'}
            elif args.command in ('train', 'research'):
                if args.command == 'research':
                    from .make_labels import make_labels
                    make_labels()
                from .train import train
                result = train()
            elif args.command == 'export':
                from .export import export_dataset
                result = dict(export=str(export_dataset(args.output, args.include_raw)))
            else:
                from .report import report
                result = dict(report=report())
            log(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except Exception as exc:
        # Never serialize proxy environment, YAML contents, secrets or old model bytes.
        dump(dict(status='FAILED', stage=args.command, exception=type(exc).__name__, error=str(exc)), REPORTS / 'LAST_FAILURE.json')
        log(f'FAILED [{args.command}] {type(exc).__name__}: {exc}')
        raise SystemExit(1) from exc


if __name__ == '__main__':
    main()
