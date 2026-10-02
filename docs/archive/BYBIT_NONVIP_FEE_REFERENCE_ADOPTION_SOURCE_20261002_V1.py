import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

root = Path('/mnt/d/codex/coin')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
files = {
    'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json': 'd6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f',
    'docs/BYBIT_NONVIP_COST_STANDARD_20261002.md': 'cb2977c396c9ab7ea9b1c8022a4ca6f89579d630b360dba14608d7af8d3aac76',
    'reports/fast_research/PUBLIC_STRATEGY_90D_ROOT_MODULE_ACCEPTANCE_20261002_V1.json': '865eea7de746b3c21e09dca197c88ff5b7e1bcbf07c5c8ae25df30d278020740',
}
for name, digest in files.items():
    assert sha(root / name) == digest, name
profile = json.loads((root / 'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json').read_text())
protocol = json.loads((root / 'protocols/PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json').read_text())
for market in profile['public_base_rates'].values():
    for liquidity in ('maker', 'taker'):
        assert Decimal(str(market[liquidity + '_fraction'])) * 10_000 == Decimal(str(market[liquidity + '_bps_per_side']))
spot = profile['public_base_rates']['ordinary_crypto_spot']
assert spot['taker_bps_per_side'] == spot['maker_bps_per_side'] == protocol['costs']['fee_bps_per_side'] == 10
assert spot['fee_asset_rule'] == 'PURCHASED_ASSET'
assert not profile['public_base_rates']['ordinary_perpetual_and_futures']['usable_for_spot']
assert protocol['costs']['nominal_roundtrip_bps'] == [2 * spot['taker_bps_per_side'] + 2 * protocol['costs']['slippage_bps_per_side'] + spread for spread in protocol['costs']['spread_bps']]
assert profile['existing_coin_spot_proxy']['fee_asset_rule'] == 'USDT_ON_BOTH_BUY_AND_SELL'
receipt = dict(status='BYBIT_NONVIP_PUBLIC_FEE_REFERENCE_ADOPTED_ACCOUNTING_COMPATIBILITY_PENDING',
    created_utc=datetime.now(UTC).isoformat(), source_hashes=files, raw_price_or_ledger_rows_read=0,
    source_verified_at_utc=profile['verified_at_utc'], public_base_rates=profile['public_base_rates'],
    numeric_spot_rate_matches_existing_proxy=True, existing_results_replayed_or_relabelled=False,
    current_engine_native_bybit_accounting=False, native_fee_asset_compatibility='PENDING_THIN_ADAPTER',
    current_data_venue='Binance', reference_fee_venue='Bybit', active_research_product='CRYPTO_SPOT_NO_BORROW_OR_LEVERAGE',
    nominal_spot_roundtrip_total_bps=protocol['costs']['nominal_roundtrip_bps'],
    actual_regional_account_fee_and_Bybit_price_filter_BBO_verification=False,
    old_protocols_and_engine_changed=False, candidate_status='NO_QUALIFIED_CANDIDATE',
    market_models_fit=0, locked_consumed=False, orders_sent=0, GPU_hours=0,
    next_action='Thin purchased-asset fee compatibility and causal inventory/cash verification, then fixed strategy hypothesis.')
out = root / 'reports/fast_research/BYBIT_NONVIP_STANDARD_ADOPTION_20261002_V1.json'
with out.open('x') as writer:
    json.dump(receipt, writer, ensure_ascii=False, indent=2)
    writer.write('\n')
print(json.dumps(dict(status=receipt['status'], sha256=sha(out))))
