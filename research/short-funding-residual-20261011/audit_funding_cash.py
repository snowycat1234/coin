"""Independent Decimal arithmetic and raw-source audit; imports no model code."""
import argparse
from decimal import Decimal, localcontext
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
D = lambda value: Decimal(str(value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    state = args.state.resolve()
    if not state.is_relative_to(Path('/workspace')):
        raise ValueError('Task STATE must be below /workspace')
    result = json.loads((state / 'ECONOMIC_RESULT.json').read_text())
    events = json.loads((state / 'ECONOMIC_EVENTS.json').read_text())
    probes = json.loads((state / 'ECONOMIC_PROBES.json').read_text())
    ids = json.loads((HERE / 'results/SAMPLE_IDENTITIES.json').read_text())
    predictions = json.loads((HERE / 'results/PREDICTIONS.json').read_text())
    raw = args.archive.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == result['archive_sha256']
    raw_events = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for symbol in {r['symbol'] for r in events}:
            tab = pq.read_table(io.BytesIO(archive.read('source_tables_not_model_inputs/economics/' + symbol + '_funding_events.parquet')),
                columns=['calc_time_ms', 'last_funding_rate', 'past_mark_price'],
                filters=[('calc_time_ms', '>=', 1640995200000), ('calc_time_ms', '<', 1672531200000)])
            for record in tab.to_pylist():
                raw_events[(symbol, record['calc_time_ms'] * 1000)] = record
    for row in events:
        raw_row = raw_events[(row['symbol'], row['event_us'])]
        assert raw_row['last_funding_rate'] == row['rate']
        if row['past_mark'] is None:
            assert raw_row['past_mark_price'] is None or not np.isfinite(raw_row['past_mark_price'])
        else:
            assert raw_row['past_mark_price'] == row['past_mark']
        saved = ids[row['saved_index']]
        assert saved['symbol'] == row['symbol'] and saved['decision_us'] == row['decision_us']
        delta = int(predictions['augmented_prediction'][row['saved_index']] > 0) - int(predictions['baseline_prediction'][row['saved_index']] > 0)
        assert delta == row['delta'] and delta != 0
        assert row['central_held'] == (saved['decision_us'] < row['event_us'] <= saved['label_end_us'])
        assert row['optional'] == (abs(row['event_us'] - saved['decision_us']) <= 60000000 or abs(row['event_us'] - saved['label_end_us']) <= 60000000)
    errors = []
    with localcontext() as context:
        context.prec = 50
        for row in probes:
            errors.append(abs(D(row['quantity_per_reference_capital']) - D('.12') / D(row['entry_price'])))
        for role, summary in result['summaries'].items():
            rows = events if role == 'all2022' else [r for r in events if r['role'] == role]
            divisor = D(summary['calendar_market_weeks'])
            price = D(summary['unchanged_price_cost_increment'])
            for scale, scaled in summary['scales'].items():
                for declared in scaled['conditional_sensitivity']:
                    epsilon = D(declared['assumed_relative_charge_mark_error'])
                    lower = upper = D(0)
                    for row in rows:
                        quantity = D('.12') / D(row['entry_price'])
                        coefficient = D(row['delta']) * quantity * D(row['rate']) * D(scale)
                        if row['past_mark'] is None:
                            marks = (D('.8') * D(row['entry_price']), D('1.2') * D(row['entry_price']))
                        else:
                            marks = ((1 - epsilon) * D(row['past_mark']), (1 + epsilon) * D(row['past_mark']))
                        choices = [coefficient * mark for mark in marks]
                        if row['optional']:
                            choices.append(D(0))
                        lower += min(choices)
                        upper += max(choices)
                    independently = (lower / divisor, upper / divisor)
                    errors.extend(abs(exact - D(saved)) for exact, saved in zip(independently, declared['paired_funding_interval']))
                    errors.extend(abs(price + exact - D(saved)) for exact, saved in zip(independently, declared['price_plus_funding_interval']))
        assert max(errors) < D('1e-14')
        # Hand example uses fixed units and changing settlement marks.
        hand = (D(1200) / D(100)) * (D('.0001') * D(110) - D('.0002') * D(90))
        assert hand == D('-.0840')
        # All common positions' cash cancels at equal q, even with missing mark.
        common = sum(a > 0 and b > 0 for a, b in zip(predictions['baseline_prediction'], predictions['augmented_prediction']))
        assert common == 43 and len(probes) == 9
        assert result['original_PASS_FAIL_changed'] is False and result['fits'] == 0
        report = dict(status='PASS', independent_implementation='Decimal50, no cash-check/model imports; raw2022 event rates and proxy marks rechecked',
            events_checked=len(events), differential_probes=len(probes), common_probes_cancelled=common,
            raw_missing_differential_marks=sum(r['past_mark'] is None for r in events),
            scalar_quantity_and_bound_checks=len(errors), max_absolute_error=str(max(errors)),
            hand_example=dict(reference_notional='1200', entry_price='100', fixed_coin_quantity='12',
                              marks=['110', '90'], fractional_rates=['.0001', '-.0002'], short_receipt=str(hand)),
            input_sha256={name: hashlib.sha256((state / name).read_bytes()).hexdigest() for name in ('ECONOMIC_RESULT.json','ECONOMIC_EVENTS.json','ECONOMIC_PROBES.json')},
            fits=0, new_predictions=0, development_reads=0, original_STOP_unchanged=True,
            limitation='Arithmetic/source-value audit; mark bounds and boundary ownership remain assumed, exact cash not certified')
    with (state / 'ECONOMIC_AUDIT.json').open('x') as f:
        json.dump(report, f, indent=2); f.write('\n')
    print(json.dumps({k: report[k] for k in ('status','events_checked','scalar_quantity_and_bound_checks','max_absolute_error','fits')}))


if __name__ == '__main__':
    main()
