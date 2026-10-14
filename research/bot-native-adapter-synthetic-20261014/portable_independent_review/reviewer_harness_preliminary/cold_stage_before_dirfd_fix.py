"""Independent cold stage: exact source imports, array-open prohibition.

The reused 26-test and Decimal-audit source bodies are compiled unchanged.
Only the audit destination/candidate globals are rebound after compilation.
"""
from pathlib import Path
import argparse
import atexit
import hashlib
import json
import os
import sys
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('gate', 'native', 'independent', 'math', 'export', 'audit'))
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--review-sources', required=True)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--runtime-site', action='append', required=True)
    args = parser.parse_args()
    candidate = Path(args.candidate).resolve()
    output = Path(args.output).resolve()
    review = Path(args.review_sources).resolve()
    workspace = Path(args.workspace).resolve()
    sites = [Path(p).resolve() for p in args.runtime_site]
    sys.dont_write_bytecode = True
    os.environ['BOT_NATIVE_RUNTIME_SITES'] = json.dumps([str(p) for p in sites])
    sys.path[:0] = [str(candidate), str(review), *map(str, sites)]
    observations = dict(array_open_attempts=0, warm_workspace_open_attempts=0,
                        guarded_open_events=0, stage=args.stage)

    def guarded(event, values):
        if event != 'open' or not values or not isinstance(values[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(values[0])).resolve()
        if path.suffix.lower() in ('.npz', '.npy', '.parquet', '.arrow', '.feather'):
            observations['array_open_attempts'] += 1
            raise RuntimeError('ARRAY_OPEN_FORBIDDEN:' + path.name)
        if path.is_relative_to(workspace) and not any(path.is_relative_to(p) for p in (candidate, output, review, *sites)):
            observations['warm_workspace_open_attempts'] += 1
            raise RuntimeError('WARM_WORKSPACE_READ_FORBIDDEN:' + path.name)
        observations['guarded_open_events'] += 1

    sys.addaudithook(guarded)
    atexit.register(lambda: (output / (args.stage + '_OPEN_GUARD.json')).write_text(
        json.dumps(observations, indent=2) + '\n'))

    def exact_body(name, filename, expected):
        raw = (review / filename).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('REUSED_REVIEW_SOURCE_PIN:' + filename)
        namespace = dict(__name__=name, __file__=str(review / filename))
        exec(compile(raw, str(review / filename), 'exec'), namespace)
        return namespace

    import bind_sources as B
    assert Path(B.__file__).resolve() == candidate / 'bind_sources.py'
    if args.stage in ('gate', 'native'):
        name = 'test_portable_binding' if args.stage == 'gate' else 'test_native_adapter'
        suite = unittest.defaultTestLoader.loadTestsFromName(name)
    elif args.stage == 'independent':
        ns = exact_body('independent_exact_review', 'test_native_adversarial.py',
                        '2219b171dac07b15e5a31669d16f942a09910ba123dc0aee59586c893678f59a')
        import native_adapter
        assert Path(native_adapter.__file__).resolve() == candidate / 'native_adapter.py'
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(v)
                                  for v in ns.values() if isinstance(v, type)
                                  and issubclass(v, unittest.TestCase))
    elif args.stage == 'math':
        suite = unittest.defaultTestLoader.loadTestsFromName('test_portable_math')
    elif args.stage == 'export':
        import export_generated
        export_generated.HERE = output
        export_generated.export()
        return 0
    else:
        ns = exact_body('independent_exact_decimal_audit', 'audit_exported_journals.py',
                        'c7c345f2cb674661b3566bcef785dad76c0aa4c6e731e05b750188ca095df8b7')
        ns['CANDIDATE'] = output
        ns['HERE'] = output
        ns['main']()
        return 0
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
