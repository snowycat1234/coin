"""Independent exact-Decimal replay of every frozen generated owner journal."""
from collections import defaultdict
from decimal import Decimal as D, localcontext
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / 'coin_bot_native_adapter_synthetic_20261014'
ZERO = D(0)
BTC = 'BTCUSDT'


def main():
    summary = json.loads((CANDIDATE / 'GENERATED_SUMMARY.json').read_text())
    assert summary['historical_GO'] is False
    assert summary['status'] == 'NOT_CERTIFIED_GENERATED_ONLY'
    report = []
    with localcontext() as context:
        context.prec = 40
        for run in summary['runs']:
            journal = json.loads((CANDIDATE / run['journal']).read_text())
            account = journal['account_final']
            trades = journal['native_trades']
            funding = journal['native_funding']
            allocations = journal['ownership_allocations']
            assert trades == account['trades'] and funding == account['funding']
            assert account['config']['initial_cash'] == '10000'
            assert account['config']['leverage'] == '1'
            assert account['config']['fee_rate'] == '0.00055'
            assert account['config']['half_spread_bps'] == '4'
            assert account['config']['slippage_bps'] == '4'
            assert len({(r['fill_id'], r['leg'], r['event_us']) for r in trades}) == len(trades)
            by_leg = defaultdict(list)
            for row in allocations:
                by_leg[tuple(row['native_leg'])].append(row)
            assert set(by_leg) == {(r['fill_id'], r['leg'], r['event_us']) for r in trades}
            for row in trades:
                parts = by_leg[(row['fill_id'], row['leg'], row['event_us'])]
                for native, owner in [('quantity', 'quantity'), ('fee_amount', 'fee'), ('execution_cost', 'execution_cost')]:
                    assert sum((D(a[owner]) for a in parts), ZERO) == D(row['decimal_strings'][native])
                assert all(a['side'] == row['side'] for a in parts)
            assert sum((D(a['fee']) for a in allocations), ZERO) == D(account['totals']['fees'])
            assert sum((D(a['execution_cost']) for a in allocations), ZERO) == D(account['totals']['execution_cost'])
            funding_allocations = journal['funding_allocations']
            by_event = defaultdict(list)
            for row in funding_allocations:
                by_event[row['native_event']].append(row)
            assert set(by_event) == {row['event_id'] for row in funding}
            assert sum((D(a['cash']) for a in funding_allocations), ZERO) == D(account['totals']['funding_cash'])
            grid_legs = sorted((a for a in allocations if a['owner'] in ('GRID', 'GRID_EXIT')),
                               key=lambda a: a['native_leg'][2])
            grid_owned = ZERO
            cursor = 0
            for row in funding:
                # Equal-open funding occurs before native attempt at open+1us.
                while cursor < len(grid_legs) and grid_legs[cursor]['native_leg'][2] < row['event_us']:
                    part = grid_legs[cursor]
                    grid_owned += D(part['quantity']) * (1 if part['side'] == 'BUY' else -1)
                    assert grid_owned >= ZERO
                    cursor += 1
                amount = D(row['decimal_strings']['signed_funding_USDT'])
                quantity = D(row['decimal_strings']['quantity'])
                expected_grid = amount * grid_owned / quantity if row['symbol'] == BTC and quantity and grid_owned else ZERO
                parts = by_event[row['event_id']]
                assert sum((D(a['cash']) for a in parts), ZERO) == amount
                assert next(D(a['cash']) for a in parts if a['owner'] == 'GRID') == expected_grid
            state = journal['adapter_state_final']
            owned = sum((D(slot['owned']) for slot in state['grid']['slots']), ZERO) if state['grid'] else ZERO
            assert D(state['base_btc']) + owned == D(account['positions'][BTC]['quantity'])
            assert not (owned and D(state['base_btc']) < ZERO)
            if run['terminal_paid_flat']:
                assert all(D(position['quantity']) == ZERO for position in account['positions'].values())
            else:
                assert any(D(position['quantity']) != ZERO for position in account['positions'].values())
            report.append(dict(fixture=run['fixture'], arm=run['arm'], native_fill_legs=len(trades),
                               native_funding_events=len(funding), grid_owned_fill_legs=run['grid_owned_fill_legs'],
                               paid_flat=run['terminal_paid_flat']))
    result = dict(status='PASS_EXACT_GENERATED_JOURNAL_AUDIT', journals=len(report), runs=report,
                  historical_GO=False, risk_parity_certified=False)
    (HERE / 'JOURNAL_AUDIT_RECEIPT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'runs'}))


if __name__ == '__main__':
    main()
