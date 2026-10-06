from __future__ import annotations
import json
from .common import REPORTS, atomic_text


def report() -> str:
    m = json.loads((REPORTS / 'DATASET_MANIFEST.json').read_text())
    lines = ['# Collector data report', '', f"Status: {m['status']}",
             f"Requested calendar: {m['date_range']}", f"Symbols: {', '.join(m['symbols'])}", '',
             'This report validates AVAILABLE source bytes and records missing observations; it does not certify that all requested dates exist.',
             '404 is not listing evidence. Gaps remain missing. No price/return/funding forward fill.', '',
             '| Symbol | Complete price days | Complete mark days | Complete funding intervals | Internal price gaps |',
             '|---|---:|---:|---:|---:|']
    for r in m['audit']:
        lines.append(f"| {r['symbol']} | {r['complete_kline_days']} | {r['complete_mark_days']} | {r['complete_funding_execution_intervals']} | {r['internal_incomplete_kline_days']} |")
    lines += ['', '## Scope', 'Binance USD-M public archives, NOT Bybit native execution data.',
              'Funding raw rate and calc_time are preserved. Rate unit and actual publication/charge timing remain conditional.',
              'Per-month minute tables, daily tables and funding events are listed with hashes in DATASET_MANIFEST.json.',
              'No repository-local dataset, old U artifact, CUDA runtime, proxy profile or live API key is required.',
              'Partial days are masked, not deleted from the calendar. Latest-day execution intervals can be unverified at the boundary.',
              'This package never certifies native margin, fills, liquidity capacity, liquidations or investment eligibility.']
    path = REPORTS / 'COLLECTOR_REPORT.md'
    atomic_text(path, '\n'.join(lines) + '\n')
    return str(path)
