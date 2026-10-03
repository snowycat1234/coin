"""D037 runtime-directory repair; unchanged V1 target/account function ASTs.

The first source directory remains a preserved pre-network startup failure.
Only the accepted daily receipt's new exclusive STATE directory is rebound.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from quant.paths import ROOT, STATE
from scripts.investment import public_donchian_daily_runner as original

ORIGINAL_SOURCE = 'scripts/investment/public_donchian_daily_runner.py'
ORIGINAL_SHA256 = '5459b231c340a705c4c136cd3923ecc0b510205f7f81c8c36a4ea021b97b41d9'
DAILY_DIR = STATE / 'd037-official-spot-daily-source-20261003-v2'
protocol_template = original.protocol_template
native_namespace = original.native_namespace
PROFILES = original.PROFILES
STRATEGY = original.STRATEGY


def context(spec):
    original.require(original.file_sha(ROOT / ORIGINAL_SOURCE) == ORIGINAL_SHA256,
        'Preserved original daily runner bytes required before directory adaptation')
    changes = []
    environment = original.parent.namespace(original,
        ('daily_metadata','load_daily','context','main'),
        dict(DAILY_DIR=DAILY_DIR,__file__=str(Path(__file__).resolve())),changes)
    result = environment['context'](spec)
    result['PERIOD_DERIVATION']['daily_source_directory_adaptation'] = dict(
        preserved_runner_path=ORIGINAL_SOURCE,preserved_runner_sha256=ORIGINAL_SHA256,
        daily_source_directory=str(DAILY_DIR),function_ASTs=changes,
        original_function_ASTs_unchanged=all(row['original_AST_sha256']==row['derived_AST_sha256']
            for row in changes),target_and_account_algorithms_unchanged=True)
    return result


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--protocol',type=Path,required=True)
    args,_ = parser.parse_known_args()
    path = args.protocol.resolve()
    original.require(path.is_relative_to(ROOT/'protocols') and path.is_file()
        and path.stat().st_size < 2_000_000,'Exclusive frozen ROOT protocol before execution')
    context(original.parent.old.read_json(path))['main']()

if __name__ == '__main__': main()
