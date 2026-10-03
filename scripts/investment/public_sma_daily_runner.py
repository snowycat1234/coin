"""D038 new hook/identity over the accepted D037 source and minute account.

context remains metadata/AST only. No data source/fee/risk/financial change.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from quant.paths import ROOT
from scripts.investment import public_donchian_daily_runner_v2 as prior
from scripts.investment import public_sma_daily as sma

PROFILES, STRATEGY = prior.PROFILES, sma.STRATEGY_ID
SOURCE_PATH = 'reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ACTUAL_20261003_V2.json'
SOURCE_SHA256 = '3fb29968d533e90c2d1764d15b3bce3873ef2ad9784330fe838512824dd95167'
PINS = {'scripts/investment/public_donchian_daily_runner.py':prior.ORIGINAL_SHA256,
    'scripts/investment/public_donchian_daily_runner_v2.py':'7b3ad9c67e993f9065ec83b9bcfab3aeb2c23af88c497d2f3328146f97b784c6'}
native_namespace = prior.native_namespace


def context(spec):
    original = prior.original
    for path,digest in PINS.items():
        original.require(original.file_sha(ROOT/path)==digest,'Preserved accepted daily runner identity: '+path)
    original.require(spec['daily_source_receipt']==dict(path=SOURCE_PATH,sha256=SOURCE_SHA256,
        required_status=original.DAILY_STATUS),'Exact accepted D037 source proof; no new source/QA')
    changes = []
    environment = original.parent.namespace(original,('daily_metadata','load_daily','context','main'),
        dict(DAILY_DIR=prior.DAILY_DIR,daily=sma,STRATEGY=STRATEGY,__file__=str(Path(__file__).resolve())),changes)
    result = environment['context'](spec)
    result['PERIOD_DERIVATION'].update(classification='D038_THREE_SEPARATE_SEEN_SMA_DAILY_SCREENING_NOT_UNSEEN',
        original_200day_eligibility_source_load_dates_risk_and_native_finance_unchanged=True,
        strategy_rules=sma.RULES,hook_and_identity_namespace=dict(preserved_sources=PINS,function_ASTs=changes,
            original_function_ASTs_unchanged=all(row['original_AST_sha256']==row['derived_AST_sha256'] for row in changes)))
    return result


def protocol_template(identifier,smoke_receipt):
    spec = prior.protocol_template(identifier,SOURCE_PATH,SOURCE_SHA256,smoke_receipt)
    spec.update(strategy_ids=[STRATEGY],primary_reference=STRATEGY,strategy_rules=dict(sma.RULES),
        classification='D038_SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN_OR_LONG_TERM_APR',
        smoke_test_path='tests/test_public_sma_daily.py',smoke_pytest_expression='test_sma_daily_native_route')
    # ROOT must freeze final shared current source/vendor/test union and budgets.
    return spec


def main():
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument('--protocol',type=Path,required=True)
    args,_ = parser.parse_known_args(); path = args.protocol.resolve()
    prior.original.require(path.is_relative_to(ROOT/'protocols') and path.is_file()
        and path.stat().st_size<2_000_000,'Exclusive new frozen D038 ROOT protocol before execution')
    context(prior.original.parent.old.read_json(path))['main']()

if __name__=='__main__': main()
