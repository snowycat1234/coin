"""Unrun D034: one original VM sleeve over the accepted D033 date namespace.

No market IO occurs in context(). The unchanged common research path reuses
the accepted parent Parquet, then writes its normal private Parquet/IPC before
signals and native received-asset accounting. No account loop is copied.
New protocol fields: namespace_parent_protocol={path,sha256}, and the original
reused_minute_input={report_path,report_sha256,path,sha256}. Original common
environment/config/fees/source guards remain; root freezes the storage budget.
"""
from __future__ import annotations
import argparse, json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from quant.paths import ROOT, STATE
from scripts.investment import public_long_development_adapter as parent

STRATEGY='VOL_MANAGED_BUY_AND_HOLD'
PARENT_PROTOCOL='protocols/PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1.json'
PARENT_PROTOCOL_SHA='5366363196157c1629e2e00a00301956e61b2c295b476520359bc0bd55ac746d'
PARENT_ADAPTER_SHA='15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f'
PARENT_REPORT='reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json'
PARENT_REPORT_SHA='c70e3011f74ddbbbf250316bb2cad9a02d2bd6945b266a1a96a1083b9fcbc6e8'
INPUT_PATH=STATE/'public-long-547d-actual-20261003-v1/shared_source_minutes.parquet'
INPUT_SHA='69ee7e5b8bee31f1cc28cbfbee4c99176060959a0e7d831683a3fddc796a06d2'

def require(ok, reason):
    if not ok: raise ValueError(reason)

def parent_metadata():
    """Exact small frozen metadata and code bytes only, never source arrays."""
    path=ROOT/PARENT_PROTOCOL
    require(path.is_file() and path.stat().st_size<2_000_000
        and parent.native.file_sha(path)==PARENT_PROTOCOL_SHA,'Exact accepted D033 parent protocol')
    require(parent.native.file_sha(ROOT/'scripts/investment/public_long_development_adapter.py')==PARENT_ADAPTER_SHA,
        'Frozen D033 namespace adapter unchanged')
    return json.loads(path.read_text())

def validate(spec, inherited):
    require(spec['namespace_parent_protocol']==dict(path=PARENT_PROTOCOL,sha256=PARENT_PROTOCOL_SHA),
        'Explicit exact frozen D033 namespace parent')
    require(spec['strategy_ids']==[STRATEGY] and spec['planned_ledgers']==1,'Only one original VM account')
    for key in ('folds','source_receipt','source_receipt_sha256','source_scope','source_calendar',
        'source_days_per_symbol','common_config','costs','environment','fee_settlement',
        'fee_profile_path','fee_profile_sha256','market_type'):
        require(spec[key]==inherited[key],'Original full period/source/capital/risk/fee configuration: '+key)
    require(spec['reused_minute_input']==dict(report_path=PARENT_REPORT,report_sha256=PARENT_REPORT_SHA,
        path=str(INPUT_PATH),sha256=INPUT_SHA),'Only original accepted Parquet reuse schema and exact parent bytes')
    require(not any(key in spec for key in ('reused_reference_report','reused_target_inputs')),
        'No old account or target replay; saved reference comparison is separate')
    require(type(spec['maximum_new_owned_bytes']) is int and 0<spec['maximum_new_owned_bytes']<=400_000_000
        and 0<spec['maximum_wall_seconds']<=1800,'Explicit bounded new-output budget')

def context(spec):
    """Additional D034 guard; D033 validation is applied unchanged to its parent."""
    inherited=parent_metadata();validate(spec,inherited)
    environment=parent.context(inherited)
    changes=[]; original_bench=environment['benchmarks']
    # D033 public sleeves never called this inherited wrapper. VM must bind the
    # wrapper's existing integer/date guards to the already accepted private time.
    # The original V1 all-past EWMA seed/recurrence and function remain unchanged.
    private_bench=SimpleNamespace(**parent.namespace(parent.v2,('causal_vol_multiplier',),
        vars(original_bench),changes))
    private_bulk=SimpleNamespace(**parent.namespace(parent.bulk,('fixed_targets',),
        dict(common=private_bench,original=private_bench._v1),changes))
    derivation=dict(classification='D034_SINGLE_FIXED_VM_547D_SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN',
        accounts=1,strategy_ids=[STRATEGY],fixed_spread_bps=[8],nominal_roundtrip_bps=[36],
        parent_protocol=dict(path=PARENT_PROTOCOL,sha256=PARENT_PROTOCOL_SHA),parent_adapter_sha256=PARENT_ADAPTER_SHA,
        inherited_date_namespace=deepcopy(environment['PERIOD_DERIVATION']),
        additional_private_functions=changes,reused_minute_input=deepcopy(spec['reused_minute_input']),
        reused_input_rows=1664640,raw_normalized_market_files_read=False,
        original_reused_Parquet_reader_and_research_IO_unchanged=True,
        original_native_financial_kernel_AST_unchanged=True,original_VM_EWMA_and_targets_unchanged=True,
        EWMA_scope='ALL_AVAILABLE_COMPLETED_DAILY_GROSS_REFERENCE_RETURNS_SPAN7_MIN7_NOT_LAST7_ONLY',
        original_shared_modules_or_globals_mutated=False,old_accounts_replayed=False,
        source_acceptance_or_market_IO_performed_by_context=False,
        same_risk_rules_not_equal_realized_risk=True,long_term_APR_or_native_execution_qualification=False)
    overrides=dict(environment,benchmarks=private_bench,bulk_fixed_targets=private_bulk,PERIOD_DERIVATION=derivation)
    # Compile only pinned original research/main with the already accepted D033
    # date/count/single-cost transformations. Finance, targets and IO are unedited.
    derived=parent.namespace(parent.old,('research','main'),overrides,changes,parent.common_changes)
    derived['__file__']=str(Path(__file__).resolve())
    return derived

def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--protocol',type=Path,required=True)
    args,_=parser.parse_known_args();path=args.protocol.resolve()
    require(path.is_relative_to(ROOT/'protocols') and path.is_file() and path.stat().st_size<2_000_000,
        'New exclusive frozen ROOT D034 protocol required before execution')
    context(json.loads(path.read_text()))['main']()

if __name__=='__main__':main()
