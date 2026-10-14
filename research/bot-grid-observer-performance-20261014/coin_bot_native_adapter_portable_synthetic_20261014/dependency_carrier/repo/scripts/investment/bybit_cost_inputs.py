"""Thin user rate-snapshot adapter; no API, fee tier inference or maker fills."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from copy import deepcopy
from quant.perpetual_account import D, PerpetualConfig, USDTLinearPerpetualAccount


def snapshot_cost(path: Path, *, symbols, fee_zone_by_symbol: dict[str, str],
                  scenario_id: str, half_spread_bps, slippage_bps,
                  execution_source_ref: str, execution_status: str) -> dict:
    raw = Path(path).read_bytes()
    if len(raw) > 100_000:
        raise ValueError("small supplied rate snapshot required")
    source = json.loads(raw)
    names = tuple(symbols)
    if (not names or len(names) != len(set(names)) or set(fee_zone_by_symbol) != set(names)
            or len(set(fee_zone_by_symbol.values())) != 1 or source.get('exchange') != 'Bybit'
            or source.get('mnt_discount_enabled') is not False):
        raise ValueError("explicit homogeneous instrument zone scenario and non-discounted Bybit source required")
    zone = next(iter(fee_zone_by_symbol.values()))
    if zone not in {'DERIVATIVES_CRYPTO_STANDARD', 'DERIVATIVES_INNOVATION', 'DERIVATIVES_PREMARKET'}:
        raise ValueError("only existing crypto USDT linear research scope; no Spot/TradFi/options")
    rows = [row for row in source['product_rates'] if row['product_id'] == zone]
    if len(rows) != 1:
        raise ValueError("unique supplied fee zone required")
    row = rows[0]
    fee = D(row['taker_rate_fraction'])
    if (D(row['taker_percent_display'].removesuffix('%')) / 100 != fee
            or D(row['taker_bps']) / 10000 != fee):
        raise ValueError("percent/fraction/bp identity mismatch")
    config = PerpetualConfig(fee_rate=fee, half_spread_bps=half_spread_bps, slippage_bps=slippage_bps)
    context = dict(exchange='Bybit', product='LINEAR_USDT_PERPETUAL', settlement_asset='USDT',
        liquidity_role='TAKER', fee_rate_fraction=str(fee), fee_zone_by_symbol=dict(fee_zone_by_symbol),
        fee_source_ref=str(path), fee_source_sha256=hashlib.sha256(raw).hexdigest(),
        fee_time_scope=source['historical_use'], native_fee_zone_certified=False,
        symbol_zone_status='EXPLICIT_RESEARCH_SCENARIO_NOT_NATIVE_OR_HISTORICAL_CLASSIFICATION',
        historical_execution_certified=False, execution_source_ref=execution_source_ref,
        execution_status=execution_status)
    return dict(id=scenario_id, fee_rate_fraction=str(fee), half_spread_bps=str(config.half_spread_bps),
        slippage_bps=str(config.slippage_bps),
        roundtrip_bps=str(2 * (fee * 10000 + config.half_spread_bps + config.slippage_bps)),
        provenance=context)


def scenario_config(cost: dict) -> PerpetualConfig:
    """Legacy BASE27/STRESS43 remain numerically identical."""
    config = PerpetualConfig(fee_rate=cost.get('fee_rate_fraction', '0.00055'),
        half_spread_bps=cost['half_spread_bps'], slippage_bps=cost['slippage_bps'])
    expected = 2 * (config.fee_rate * 10000 + config.half_spread_bps + config.slippage_bps)
    if D(str(cost['roundtrip_bps'])) != expected:
        raise ValueError("roundtrip includes commission plus both execution components")
    return config


def execution_components(total: float, cost: dict) -> tuple[float, float]:
    """Split the already-priced execution loss; never debit it a second time."""
    config = scenario_config(cost)
    friction = config.half_spread_bps + config.slippage_bps
    if friction == 0:
        if total != 0:
            raise ValueError("zero configured friction with nonzero execution journal")
        return 0., 0.
    spread = total * float(config.half_spread_bps / friction)
    return spread, total - spread


def account_for_cost(cost: dict, symbols, factory=USDTLinearPerpetualAccount):
    kwargs = {'cost_context': cost['provenance']} if 'provenance' in cost else {}
    return factory(scenario_config(cost), symbols=tuple(symbols), **kwargs)


def cash_cost_summary(cost: dict, symbols, cached_summary: dict | None = None) -> dict:
    """Reuse a constant cash artifact, updating the entire cost identity."""
    result = deepcopy(cached_summary or {})
    if cached_summary is not None and (result['NAV'] != 10000 or result['trade_legs'] != 0
            or result['funding_events'] != 0 or any(p['quantity'] != 0 for p in result['positions'].values())):
        raise ValueError("only known constant cash may reuse zero-account artifacts")
    result.update(account_for_cost(cost, symbols).summary())
    return result
