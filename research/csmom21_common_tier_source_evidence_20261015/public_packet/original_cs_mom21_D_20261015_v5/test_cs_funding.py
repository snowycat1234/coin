"""Invented rates/clocks in the exact qualified 2022 funding JSON schema.

Only the published metadata interval histogram is reproduced. No event-rate
body is read, no old source scope is minted, and no target is computed here.
"""
import ast
import json
from types import SimpleNamespace
from copy import deepcopy
from pathlib import Path
import unittest

import numpy as np

import cs_common as c
import cs_config as config
import cs_codec as codec
import cs_entry as entry
import cs_signal as signal
import cs_source as source


def invented_source_rows():
    start = config.period_named(2022)['start']
    rows = []
    for j, symbol in enumerate(signal.SYMBOLS):
        intervals = [8.] * 1095 if symbol != 'SOLUSDT' else [8.] * 1069 + [4.] * 2 + [2.] * 99
        for i, hours in enumerate(intervals):
            rows.append(dict(symbol=symbol, calc_time_ms=(start + (i + 1) * codec.MINUTE) // 1000,
                raw_rate=float((1 if i % 2 else -1) * (j + 1) * .00001), reported_interval_hours=hours))
    return sorted(rows, key=lambda row: (row['calc_time_ms'], signal.SYMBOLS.index(row['symbol'])))


def normalized_rows():
    # Same unchanged field projection as cs_source_bridge capture_2022.
    return [dict(symbol=r['symbol'], event_us=r['calc_time_ms'] * 1000, raw_rate=r['raw_rate'],
                 reported_interval_hours=r['reported_interval_hours'], raw_rate_unit='UNCONFIRMED')
            for r in invented_source_rows()]


class PreservedFundingSchemaTests(unittest.TestCase):
    def setUp(self):
        self.contract = entry.contracts()['years']['2022']
        self.rows = normalized_rows()

    def validate(self, rows):
        return source.funding_events(2022, c.canonical(rows), self.contract, normalized_2022=True)

    def test_exact5550_source_schema_and_interval_histogram_preserve_all_values(self):
        from collections import Counter
        raw = invented_source_rows()
        self.assertEqual(len(raw), 5550)
        self.assertTrue(all(set(row) == {'symbol', 'calc_time_ms', 'raw_rate', 'reported_interval_hours'} for row in raw))
        self.assertTrue(all(type(row['calc_time_ms']) is int and type(row['raw_rate']) is float
                            and type(row['reported_interval_hours']) is float for row in raw))
        self.assertEqual(Counter(row['reported_interval_hours'] for row in raw), {8.: 5449, 4.: 2, 2.: 99})
        result = self.validate(self.rows)
        self.assertEqual(c.canonical(result), c.canonical(self.rows))
        self.assertEqual([row['raw_rate'].hex() for row in result], [row['raw_rate'].hex() for row in self.rows])
        self.assertTrue(all(row['raw_rate_unit'] == 'UNCONFIRMED' for row in result))
        with self.assertRaises(TypeError): result[0]['reported_interval_hours'] = 8.

    def test_exact_original_D_validator_semantics_and_no_interval_rescale(self):
        path = c.ROOT / 'traditional_D_full2022_20261015_v2/source_projection.py'
        tree = ast.parse(path.read_bytes())
        project = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'project')
        begin = next(i for i, n in enumerate(project.body) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'events' for t in n.targets))
        pure_validation = project.body[begin + 1:begin + 4]
        self.assertEqual([type(n).__name__ for n in pure_validation], ['If', 'If', 'For'])
        period = config.period_named(2022)
        for value in (2., 4., 8., 16., .5):
            rows = deepcopy(self.rows); rows[0]['reported_interval_hours'] = value
            before = c.canonical(rows)
            namespace = dict(events=rows, s=SimpleNamespace(S=signal.SYMBOLS, START=period['start'], END=period['end']), np=np)
            exec(compile(ast.Module(body=pure_validation, type_ignores=[]), str(path), 'exec'), namespace)
            result = self.validate(rows)
            self.assertEqual(c.canonical(rows), before)
            self.assertEqual(c.canonical(result), before)

    def test_unmodified_v3_validator_reproduces_the_schema_failure(self):
        path = c.ROOT / 'original_cs_mom21_D_20261015_v3/cs_source.py'
        tree = ast.parse(path.read_bytes())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'funding_events')
        namespace = dict(c=c, config=config, codec=codec, signal=signal, np=np)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        with self.assertRaisesRegex(ValueError, 'PRESERVED_RAW_UNCERTIFIED_FUNDING_SCHEMA_REQUIRED'):
            namespace['funding_events'](2022, c.canonical(self.rows), self.contract, normalized_2022=True)

    def test_unsupported_bool_nonfinite_nonpositive_intervals_and_units_deny(self):
        for value in (True, 0, -2, '2'):
            bad = deepcopy(self.rows); bad[0]['reported_interval_hours'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.validate(bad)
        for value in (float('inf'), float('nan')):
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                source.funding_events(2022, json.dumps([dict(self.rows[0], reported_interval_hours=value)]).encode(),
                                      self.contract, normalized_2022=True)
        for key, value in (('raw_rate', True), ('raw_rate_unit', 'CERTIFIED'), ('event_us', True), ('symbol', 'OTHER')):
            bad = deepcopy(self.rows); bad[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.validate(bad)

    def test_exact_fields_identity_calendar_and_sameclock_order_stay_required(self):
        changes = []
        bad = deepcopy(self.rows); bad[0]['arrival_certified'] = True; changes.append(bad)
        bad = deepcopy(self.rows); bad[0] = dict(bad[1]); changes.append(bad)
        bad = deepcopy(self.rows); bad[0]['event_us'] = config.period_named(2022)['end']; changes.append(bad)
        bad = deepcopy(self.rows); bad[0], bad[1] = bad[1], bad[0]; changes.append(bad)
        changes.append(self.rows[:-1])
        for index, bad in enumerate(changes):
            with self.subTest(index=index), self.assertRaises(ValueError): self.validate(bad)

    def test_2023_eight_hour_contract_remains_unchanged(self):
        contract = entry.contracts()['years']['2023']; start = config.period_named(2023)['start']
        rows = [dict(symbol=symbol, event_us=start + i * 8 * 60 * codec.MINUTE,
                     raw_rate=.0001, reported_interval_hours=8.)
                for i in range(1095) for symbol in sorted(signal.SYMBOLS)]
        self.assertEqual(len(source.funding_events(2023, c.canonical(rows), contract)), 5475)
        rows[0]['reported_interval_hours'] = 2.
        with self.assertRaises(ValueError): source.funding_events(2023, c.canonical(rows), contract)


if __name__ == '__main__': unittest.main()
