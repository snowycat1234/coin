"""Finite separately named pure-CS common-tier development scope."""
from datetime import datetime, timezone
from types import MappingProxyType

STRATEGY = 'CSMOM21_COMMON_TIER'
VERSION = 'PORTABLE_CSMOM21_COMMON_TIER_FIFTEEN_DEV_V2'
TIERS = ('LOW', 'MID', 'HIGH')
TIER_BUDGETS = MappingProxyType({'LOW': .05, 'MID': .10, 'HIGH': .15})
TIER_GROSS_CAPS = MappingProxyType({'LOW': .30, 'MID': .60, 'HIGH': .90})
DAY = 86_400_000_000


def utc(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()) * 1_000_000


PERIODS = (
    (2021, '2021-04-02', '2022-01-01', 274, 'PARTIAL_APR2_DEC31'),
    (2022, '2022-01-01', '2023-01-01', 365, 'FULL_YEAR'),
    (2023, '2023-01-01', '2024-01-01', 365, 'FULL_YEAR'),
    (2024, '2024-01-01', '2025-01-01', 366, 'FULL_YEAR'),
    (2025, '2025-01-01', '2026-01-01', 365, 'FULL_YEAR'),
)


def cells():
    return tuple(dict(cell_id=f'{year}_{STRATEGY}_{tier}_D', strategy=STRATEGY,
        tier=tier, year=year, start_UTC=start, end_exclusive_UTC=end,
        start_us=utc(start), end_exclusive_us=utc(end), calendar_days=days,
        calendar_label=label, annual_volatility_budget=TIER_BUDGETS[tier],
        gross_ceiling=TIER_GROSS_CAPS[tier], asset_ceiling=.30,
        fresh_annual_wallet=True, initial_cash_USDT='10000',
        classification='EXPOSED_SEEN_OR_ROLE_UNPROVEN_DEVELOPMENT_NOT_UNTOUCHED_OOS')
        for year, start, end, days, label in PERIODS for tier in TIERS)


def cell_named(cell_id):
    for cell in cells():
        if cell['cell_id'] == cell_id:
            return cell
    raise ValueError('EXACT_FIFTEEN_CELL_SCOPE_REQUIRED')


def period_named(year):
    if type(year) is not int:
        raise ValueError('EXACT_INTEGER_DEVELOPMENT_YEAR_REQUIRED')
    for row in PERIODS:
        if row[0] == year:
            return dict(year=year, start=utc(row[1]), end=utc(row[2]), days=row[3], label=row[4],
                        warmup_start=utc(row[1]) - 199 * DAY)
    raise ValueError('EXACT_FIVE_DEVELOPMENT_PERIODS_REQUIRED')
