"""Reuse the accepted bounded runner for one new fixed Turtle direction case."""
import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from quant.paths import ROOT
from scripts.investment import perpetual_directional as base
from scripts.investment import public_long_development_adapter as private

ORIGINAL = 'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py'
ORIGINAL_SHA = 'b19023de82a411d0d634d5d81693a40a57db7986983c240b17502556af1b9f3d'
LOCK_SHA = '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'

def stream_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--protocol', type=Path, required=True)
    args, _ = parser.parse_known_args()
    spec = base.small(args.protocol)
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    base.need(spec['tests'] == ['tests/test_turtle_direction_mask_v2.py']
        and spec['frozen_sources'][own] == stream_sha(__file__)
        and spec['frozen_sources'][ORIGINAL] == stream_sha(ROOT / ORIGINAL) == ORIGINAL_SHA,
        'One frozen new direction-permission case and accepted runner')
    base.need('state/dataset_lock.json' not in spec['frozen_sources'], 'Private lock excluded')
    base.need(stream_sha(ROOT / 'state/dataset_lock.json') == LOCK_SHA, 'Private lock hash only')
    loader = importlib.util.spec_from_file_location('_d049_bounded_case', ROOT / ORIGINAL)
    module = importlib.util.module_from_spec(loader)
    sys.modules[loader.name] = module
    loader.loader.exec_module(module)
    def compact(path, event):
        value = dict(event)
        value['source_hashes'] = {args.protocol.relative_to(ROOT).as_posix(): event['protocol_hash']}
        for field, key in [('hyperparameters', 'calculation_rules'), ('thresholds', 'calculation_rules'),
                           ('cost_assumptions', 'fee_profile')]:
            value[field] = dict(frozen_protocol=event['protocol_hash'], field=key)
        return module.reuse.append_event(path, value)
    reuse = SimpleNamespace(**{**vars(module.reuse), 'append_event': compact})
    private.namespace(module, ['main'], dict(__file__=__file__, ARCHIVE=own, reuse=reuse), [])['main']()
    base.need(stream_sha(ROOT / 'state/dataset_lock.json') == LOCK_SHA, 'Private lock remained exact')

if __name__ == '__main__':
    main()
