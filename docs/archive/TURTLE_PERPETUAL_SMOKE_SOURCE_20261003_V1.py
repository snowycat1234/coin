"""Only the new Turtle state/order fixture through the accepted test runner."""
import argparse
import importlib.util
import sys
from pathlib import Path
from quant.paths import ROOT
from scripts.investment import perpetual_directional as base
from scripts.investment import public_long_development_adapter as private

ORIGINAL='docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py'
ORIGINAL_SHA='b19023de82a411d0d634d5d81693a40a57db7986983c240b17502556af1b9f3d'


def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--protocol',type=Path,required=True)
    args,_=p.parse_known_args();spec=base.small(args.protocol);own=Path(__file__).resolve().relative_to(ROOT).as_posix()
    base.need(spec['tests']==['tests/test_turtle_perpetual_bridge.py']
        and spec['frozen_sources'][own]==base.sha(__file__)
        and spec['frozen_sources'][ORIGINAL]==base.sha(ROOT/ORIGINAL)==ORIGINAL_SHA,
        'One new stateful Turtle case, original bounded pytest body')
    base.need('state/dataset_lock.json' not in spec['frozen_sources'], 'No private lock in exported source map')
    module_spec=importlib.util.spec_from_file_location('_d047_original_bounded_test_runner',ROOT/ORIGINAL)
    module=importlib.util.module_from_spec(module_spec);sys.modules[module_spec.name]=module
    module_spec.loader.exec_module(module)
    derived=private.namespace(module,['main'],dict(__file__=__file__,ARCHIVE=own),[])['main']
    derived()


if __name__=='__main__':
    main()
