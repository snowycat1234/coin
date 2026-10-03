"""UNRUN: sole new213 wiring case through the preserved bounded pytest runner."""
import argparse
import importlib.util
import os
import sys
from pathlib import Path
from quant.paths import ROOT
from scripts.investment import perpetual_directional as base
from scripts.investment import public_long_development_adapter as private

ORIGINAL = 'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py'
ORIGINAL_SHA256 = 'b19023de82a411d0d634d5d81693a40a57db7986983c240b17502556af1b9f3d'


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--protocol', type=Path, required=True); args, _ = p.parse_known_args()
    spec = base.small(args.protocol); hashes = spec['frozen_sources']
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    adapter = spec['research_adapter']; path = (ROOT/adapter['path']).resolve()
    base.need(path.is_relative_to(ROOT) and base.sha(path) == adapter['sha256'] == hashes[adapter['path']],
        'Exact new213 source; no model/data execution before prebinding')
    base.need(hashes.get(own) == base.sha(__file__) and hashes.get(ORIGINAL) == ORIGINAL_SHA256
        and base.sha(ROOT/ORIGINAL) == ORIGINAL_SHA256, 'Own wrapper and unchanged bounded pytest orchestration')
    base.need(len(spec['tests']) == 1 and spec['tests'][0].startswith('tests/')
        and spec['tests'][0] in hashes, 'Exactly one new wiring case; no old green suite')
    before = {key:os.environ.get(key) for key in ('COIN_213_WIRING_ADAPTER','COIN_213_WIRING_ADAPTER_SHA256')}
    os.environ['COIN_213_WIRING_ADAPTER'] = str(path)
    os.environ['COIN_213_WIRING_ADAPTER_SHA256'] = adapter['sha256']
    module_spec = importlib.util.spec_from_file_location('_d043_original_bounded_test_runner', ROOT/ORIGINAL)
    module = importlib.util.module_from_spec(module_spec); sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    # Only wrapper command/ownsource metadata globals differ. Exact original
    # pytest, registry, source-byte, JUnit, failure and resource body is reused.
    receipt = []
    environment = private.namespace(module, ['main'], dict(__file__=__file__,ARCHIVE=own), receipt)
    try:
        environment['main']()
    finally:
        for key,value in before.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key] = value


if __name__ == '__main__':
    main()
