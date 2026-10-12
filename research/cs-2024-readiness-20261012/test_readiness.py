import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('r',Path(__file__).with_name('readiness.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_unchanged_holes_block_both_wallet_and_irrelevant_acquisition():
    g=m.admission(10,451,True);assert g['native_wallets_admitted']==0 and not g['large_remaining_source_acquisition_admitted'] and not g['denied_API_retry_allowed']
def test_changed_hash_does_not_make_gap_ready_or_allow_denied_API():
    g=m.admission(10,451,False);assert g['status'].startswith('UNKNOWN') and g['native_wallets_admitted']==0 and not g['denied_API_retry_allowed']
def test_complete_slice_is_not_full_year_or_wallet_admission():
    g=m.admission(0,451,True);assert g['status'].startswith('SLICE_SOURCE_ONLY') and g['native_wallets_admitted']==0
