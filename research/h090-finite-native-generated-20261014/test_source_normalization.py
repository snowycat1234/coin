"""Generated-only malformed source regressions and unchanged arithmetic checks.

Fixture pins prove byte consistency only, never real provider/source authority.
No account is imported or constructed; no historical data or execution is used.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
REVIEWED = HERE / 'dependencies/calendar_review_baseline'
PREVIOUS = HERE / 'dependencies/risk_review_baseline'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


c = load_module('h090_normalized_calendar', HERE / 'calendar_readiness_v2.py')
old = load_module('h090_reviewed_calendar', REVIEWED / 'calendar_readiness_v2.py')
D = c.DAY
H = 3_600_000_000


def fixture(decision=240 * D, interval=1440):
    def bars(last, step, kind):
        rows = []
        for i in range(200):
            end = last - (199 - i) * step
            for j, symbol in enumerate(c.CORE5):
                rows.append(dict(symbol=symbol, open_us=end - step, close_us=end,
                                 available_us=end, close=100. + j * 10 + i * .1 + np.sin(i + j),
                                 complete=True, imputed=False, actual_source=True,
                                 record_locator=f'{kind}/{i}/{symbol}'))
        return rows
    source = dict(symbol_order=list(c.CORE5), daily_bars=bars(decision // D * D, D, 'daily'))
    if interval == 240:
        source['signal_bars'] = bars(decision, 4 * H, 'signal')
    return source


def packet(module, source, interval=1440, manifest_changes=None):
    raw = json.dumps(source, separators=(',', ':'), allow_nan=True).encode()
    manifest = dict(schema='H090_REVIEWED_SOURCE_BAR_BINDING_V2',
                    status='PINNED_ACTUAL_COMPLETE_SOURCE_BARS',
                    source_blob_SHA256=hashlib.sha256(raw).hexdigest(),
                    source_index_SHA256='b' * 64, symbol_order=list(c.CORE5),
                    signal_interval_minutes=interval,
                    fixture_scope='GENERATED_ONLY_NOT_REAL_SOURCE_CERTIFICATION')
    manifest.update(manifest_changes or {})
    binding = json.dumps(manifest, separators=(',', ':')).encode()
    return module.SourcePacket(raw, binding, hashlib.sha256(binding).hexdigest())


def certify(module, source, decision=240 * D, interval=1440, manifest_changes=None):
    return module.certify_source(packet(module, source, interval, manifest_changes),
                                 decision_us=decision, signal_interval_minutes=interval)


class SourceNormalizationChecks(unittest.TestCase):
    def reject(self, source, code, decision=240 * D, interval=1440, manifest_changes=None):
        with self.assertRaisesRegex(c.SourceReadinessError, '^' + code + '$'):
            certify(c, source, decision, interval, manifest_changes)

    def test_original_three_typeerror_edges_reproduced_then_normalized(self):
        variants = [(fixture(), {'symbol_order': None}), (fixture(), None), (fixture(), None)]
        variants[1][0]['symbol_order'] = None
        variants[2][0]['daily_bars'][-1]['close'] = 10 ** 400
        for i, (source, changes) in enumerate(variants):
            with self.subTest(edge=i):
                with self.assertRaises(TypeError):
                    certify(old, source, manifest_changes=changes)
                code = 'POSITIVE_FINITE_SOURCE_CLOSE_REQUIRED' if i == 2 else 'EXACT_CORE5_SOURCE_ORDER_REQUIRED'
                self.reject(source, code, manifest_changes=changes)

    def test_manifest_and_source_require_five_string_json_list(self):
        invalid = [None, False, True, 7, 1.5, '', 'BTCUSDT', {}, dict.fromkeys(c.CORE5),
                   [], list(c.CORE5[:-1]), list(c.CORE5) + ['extra'],
                   [None] + list(c.CORE5[1:]), [7] + list(c.CORE5[1:]),
                   [False] + list(c.CORE5[1:]), [['BTCUSDT']] + list(c.CORE5[1:])]
        for location in ('manifest', 'source'):
            for value in invalid:
                with self.subTest(location=location, value=value):
                    source = fixture()
                    changes = {'symbol_order': value} if location == 'manifest' else None
                    if location == 'source':
                        source['symbol_order'] = value
                    self.reject(source, 'EXACT_CORE5_SOURCE_ORDER_REQUIRED', manifest_changes=changes)

    def test_exact_order_check_retained_after_shape_guard(self):
        for value in (list(c.CORE5[::-1]), [c.CORE5[0]] * 5, ['UNKNOWN'] + list(c.CORE5[1:])):
            for location in ('manifest', 'source'):
                with self.subTest(location=location, value=value):
                    source = fixture()
                    changes = {'symbol_order': value} if location == 'manifest' else None
                    if location == 'source':
                        source['symbol_order'] = value
                    self.reject(source, 'EXACT_CORE5_SOURCE_ORDER_REQUIRED', manifest_changes=changes)

    def test_huge_json_integer_close_rejects_on_daily_and_signal_bars(self):
        for interval, series, decision in ((1440, 'daily_bars', 240 * D),
                                           (240, 'daily_bars', 240 * D + 4 * H),
                                           (240, 'signal_bars', 240 * D + 4 * H)):
            for position in (0, -1):
                for value in (10 ** 20, 10 ** 400, -(10 ** 400)):
                    with self.subTest(interval=interval, series=series, position=position, value=value):
                        source = fixture(decision, interval)
                        source[series][position]['close'] = value
                        self.reject(source, 'POSITIVE_FINITE_SOURCE_CLOSE_REQUIRED', decision, interval)

    def test_huge_close_typeerror_is_preserved_as_error_cause(self):
        source = fixture()
        source['daily_bars'][-1]['close'] = 10 ** 400
        with self.assertRaises(c.SourceReadinessError) as result:
            certify(c, source)
        self.assertIsInstance(result.exception.__cause__, TypeError)

    def test_existing_invalid_close_rules_remain_fail_closed(self):
        for value in (None, True, False, '100', [], {}, 0, -1, -1., float('nan'), float('inf')):
            with self.subTest(value=value):
                source = fixture()
                source['daily_bars'][-1]['close'] = value
                with self.assertRaises(c.SourceReadinessError):
                    certify(c, source)

    def test_valid_daily_and_six_four_hour_grids_are_bitwise_unchanged(self):
        points = [(240 * D, 1440)] + [(240 * D + k * 4 * H, 240) for k in range(6)] + [(241 * D, 240)]
        for decision, interval in points:
            with self.subTest(decision=decision, interval=interval):
                source = fixture(decision, interval)
                wanted = certify(old, source, decision, interval)
                got = certify(c, source, decision, interval)
                for expected_array, actual_array in zip(wanted[:3], got[:3]):
                    self.assertEqual(expected_array.dtype, actual_array.dtype)
                    self.assertEqual(expected_array.tobytes(), actual_array.tobytes())
                self.assertEqual(wanted[3], got[3])

    def test_existing_accepted_int_and_float_closes_are_unchanged(self):
        for value in (1, 100, 10 ** 18, .125, 100., 1e100):
            with self.subTest(value=value):
                source = fixture()
                source['daily_bars'][0]['close'] = value
                wanted = certify(old, source)
                got = certify(c, source)
                for expected_array, actual_array in zip(wanted[:3], got[:3]):
                    self.assertEqual(expected_array.tobytes(), actual_array.tobytes())
                self.assertEqual(wanted[3], got[3])

    def test_unchanged_calendar_rules_reject_same_cases(self):
        changes = [lambda s: s['daily_bars'].pop(),
                   lambda s: s['daily_bars'].__setitem__(slice(-5, None), s['daily_bars'][-10:-5]),
                   lambda s: s['daily_bars'][-1].__setitem__('available_us', 240 * D + 1),
                   lambda s: s['daily_bars'][-1].__setitem__('imputed', True),
                   lambda s: s['daily_bars'][-1].__setitem__('complete', False),
                   lambda s: s['daily_bars'].__delitem__(slice(0, 5)),
                   lambda s: s['daily_bars'].__setitem__(slice(-5, None), s['daily_bars'][-5:][::-1])]
        for index, change in enumerate(changes):
            with self.subTest(case=index):
                source = fixture()
                change(source)
                with self.assertRaises(old.SourceReadinessError) as wanted:
                    certify(old, source)
                with self.assertRaises(c.SourceReadinessError) as got:
                    certify(c, source)
                self.assertEqual(str(wanted.exception), str(got.exception))

    def test_calendar_ast_changes_only_two_validation_sites(self):
        before = ast.parse((REVIEWED / 'calendar_readiness_v2.py').read_text())
        after = ast.parse((HERE / 'calendar_readiness_v2.py').read_text())
        self.assertEqual(len(before.body), len(after.body))
        changed = []
        for left, right in zip(before.body, after.body):
            if ast.dump(left) != ast.dump(right):
                changed.append(left.name)
        self.assertEqual(changed, ['_bars', 'certify_source'])
        normalized = copy.deepcopy(after)
        bars = next(node for node in normalized.body if isinstance(node, ast.FunctionDef) and node.name == '_bars')
        candidates = [node for node in ast.walk(bars) if isinstance(node, ast.Try)]
        self.assertEqual(len(candidates), 1)
        wrapped = candidates[0]
        self.assertEqual(len(wrapped.body), 1)
        def unwrap(node):
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for index, child in enumerate(value):
                        if child is wrapped:
                            value[index:index + 1] = wrapped.body
                            return True
                        if isinstance(child, ast.AST) and unwrap(child):
                            return True
                elif isinstance(value, ast.AST) and unwrap(value):
                    return True
            return False
        self.assertTrue(unwrap(bars))
        certify_node = next(node for node in normalized.body if isinstance(node, ast.FunctionDef) and node.name == 'certify_source')
        index = next(i for i, node in enumerate(certify_node.body)
                     if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'orders' for target in node.targets))
        del certify_node.body[index:index + 2]
        self.assertEqual(ast.dump(before), ast.dump(normalized))

    def test_reviewed_risk_math_ast_and_original_source_pins_unchanged(self):
        self.assertEqual((HERE / 'h090_risk_controller.py').read_bytes(),
                         (REVIEWED / 'h090_risk_controller.py').read_bytes())
        earlier = ast.parse((PREVIOUS / 'h090_risk_controller.py').read_text())
        reviewed = ast.parse((REVIEWED / 'h090_risk_controller.py').read_text())
        for name in ('_math', 'validate_weights', 'verify_originals', 'require_native_integration'):
            left = next(node for node in earlier.body if isinstance(node, ast.FunctionDef) and node.name == name)
            right = next(node for node in reviewed.body if isinstance(node, ast.FunctionDef) and node.name == name)
            self.assertEqual(ast.dump(left), ast.dump(right))
        prior_pins = json.loads((PREVIOUS / 'SOURCE_PINS.json').read_text())['files']
        reviewed_pins = json.loads((REVIEWED / 'SOURCE_PINS.json').read_text())['files']
        self.assertEqual({name: record['SHA256'] for name, record in prior_pins.items()},
                         {name: record['SHA256'] for name, record in reviewed_pins.items()})
        for name, record in reviewed_pins.items():
            self.assertEqual(hashlib.sha256((REVIEWED / record['package_path']).read_bytes()).hexdigest(), record['SHA256'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
