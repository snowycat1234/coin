"""Generated-only source codecs, CS projection and fresh-process boundary."""
from io import BytesIO
import importlib.util
import json
import os
from pathlib import Path
import sys
import shutil
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

import cs_common as c
import cs_codec as codec
import cs_config as config
import cs_entry as entry
import cs_quality
import cs_signal as signal
import cs_source as source
import cs_source_bridge  # Exact pure graph preload.
from cs_source_guard import SourceOnlyGuard, SourceBoundaryViolation
from test_cs_entry import fake_authority


def pack(**arrays):
    out = BytesIO(); np.savez_compressed(out, **arrays); return out.getvalue()


def fake_daily(year):
    rows, first, last = codec.STORED_DAILY[year]
    clocks = np.arange(first, last + config.DAY, config.DAY, dtype=np.int64)
    x = np.arange(rows, dtype=np.float64)
    prices = np.column_stack([100 + j * 20 + x * (.02 + j * .003)
        + np.sin(x / (7 + j) + j) * .4 for j in range(5)])
    arrays = dict(close_available_us=clocks, close=prices)
    if year in (2021, 2022):
        arrays['symbol_order'] = np.array(signal.SYMBOLS)
    return arrays


def fake_month(count=4, start=1640995200000000):
    arrays = dict(times=np.arange(start, start + count * codec.MINUTE, codec.MINUTE, dtype=np.int64))
    arrays['available_us'] = arrays['times'] + codec.MINUTE
    arrays.update({symbol + '_' + field: np.full(count, 100 + j, dtype=np.float64)
        for j, symbol in enumerate(signal.SYMBOLS) for field in codec.FIELDS})
    return arrays


def source_read_paths():
    code = c.exact_object((c.HERE / 'CODE_MANIFEST.json').read_bytes())
    return [c.HERE / name for name in code['files']] + [c.ROOT / name for name in code['dependencies']] + [c.HERE / 'CODE_MANIFEST.json']


class SourceCodecTests(unittest.TestCase):
    def test_exact_fake2022_2023_daily_projection_and_all_three_CS_targets(self):
        for year in (2022, 2023):
            arrays = fake_daily(year)
            t, p, d = codec.daily_inputs(year, pack(**arrays))
            period = config.period_named(year)
            self.assertEqual(len(d), 365); self.assertEqual(len(t), 564)
            self.assertEqual(int(t[0]), period['warmup_start']); self.assertEqual(int(t[-1]), period['end'] - config.DAY)
            raw, original, common, covariance, diagnostic, proofs = signal.project_arrays(p, t, t, d)
            expected, diag = signal.originals().public_targets(p, t, d, signal.SYMBOLS, signal.SYMBOLS)
            self.assertEqual(expected.tobytes(), original.tobytes()); self.assertEqual(diag, diagnostic)
            for i in (0, 37, 364):
                for tier in config.TIERS:
                    target, proof = signal.common_grid().scale_to_tier(original[i], covariance[i], tier)
                    self.assertEqual(target.tobytes(), common[tier][i].tobytes())
            for array in (t, p, d):
                self.assertFalse(array.flags.writeable)

    def test_2023_endpoint_source_row_never_enters_targets_covariance(self):
        a = fake_daily(2023); changed = {key: value.copy() for key, value in a.items()}
        changed['close'][-1] *= np.array([20, .1, 4, .3, 7])
        t, p, d = codec.daily_inputs(2023, pack(**a)); tt, pp, dd = codec.daily_inputs(2023, pack(**changed))
        self.assertEqual(p.tobytes(), pp.tobytes())
        left, right = signal.project_arrays(p, t, t, d), signal.project_arrays(pp, tt, tt, dd)
        for i in (0, 1, 3): self.assertEqual(left[i].tobytes(), right[i].tobytes())
        for tier in config.TIERS: self.assertEqual(left[2][tier].tobytes(), right[2][tier].tobytes())

    def test_strict_numeric_headers_and_daily_clock_namespace(self):
        for year in (2022, 2023):
            original = fake_daily(year)
            for key, mutate in (('close', lambda x: x.astype(np.float32)),
                                ('close_available_us', lambda x: x.astype(np.uint64))):
                changed = {name: value.copy() for name, value in original.items()}; changed[key] = mutate(changed[key])
                with self.assertRaises(ValueError): codec.daily_inputs(year, pack(**changed))
            changed = {name: value.copy() for name, value in original.items()}; changed['close_available_us'][2] += 1
            with self.assertRaises(ValueError): codec.daily_inputs(year, pack(**changed))
            changed = {name: value.copy() for name, value in original.items()}; changed['close'][2, 1] = np.nan
            with self.assertRaises(ValueError): codec.daily_inputs(year, pack(**changed))
        bad = pack(x=np.ones(4, dtype=object))
        with self.assertRaises(ValueError): codec.npz(bad, {'x': ((4,), 'float64')})

    def test_duplicate_zip_member_and_truncated_payload_rejected_before_decode(self):
        array = BytesIO(); np.save(array, np.ones(4), allow_pickle=False)
        for contents in ((array.getvalue(), array.getvalue()), (array.getvalue()[:-1],)):
            out = BytesIO()
            with zipfile.ZipFile(out, 'w') as archive:
                for body in contents: archive.writestr('x.npy', body)
            with patch.object(np, 'load', side_effect=AssertionError('HEADER_MUST_FAIL_FIRST')):
                with self.assertRaises(ValueError): codec.npz(out.getvalue(), {'x': ((4,), 'float64')})

    def test_immutable_month_arrays_and_unlisted_or_genuine_mark_overwrite_denials(self):
        a = fake_month(); projected, missing = codec.month_arrays(2022, pack(**a), int(a['times'][0]), 4)
        self.assertFalse(missing)
        for value in projected.values():
            with self.assertRaises(ValueError): value.setflags(write=True)
        a['BTCUSDT_mark'][2] = np.nan
        with self.assertRaisesRegex(ValueError, 'ABSENCE'): codec.month_arrays(2022, pack(**a), int(a['times'][0]), 4)
        for count in (True, 0, 44641):
            with self.assertRaises(ValueError): codec.month_arrays(2022, b'', 0, count)


class FreshSourceGraphTests(unittest.TestCase):
    def test_pure_fake_CS_projection_inside_guard_has_zero_attempts(self):
        signal.originals(); signal.common_grid(); cs_quality.original_quality()
        arrays = fake_daily(2023); t, p, d = codec.daily_inputs(2023, pack(**arrays))
        guard = SourceOnlyGuard(read_paths=source_read_paths())
        with guard:
            signal.project_arrays(p, t, t, d[:2]); guard.checkpoint('FAKE_CS_TARGET_PROJECTION')
        self.assertFalse(any(guard.attempts.values()))

    def test_direct_file_loader_is_denied_and_attempt_is_fatal_even_if_caught(self):
        guard = SourceOnlyGuard(read_paths=source_read_paths())
        with self.assertRaises(SourceBoundaryViolation):
            with guard:
                try: importlib.util.spec_from_file_location('fake_alias', '/tmp/no_source.py')
                except SourceBoundaryViolation: pass
        self.assertEqual(guard.attempts['financial_imports'], 1)

    def test_preloaded_finance_and_captured_bound_method_refuse_guard_entry(self):
        fake = types.ModuleType('_generated_preloaded_finance'); fake.__source_guard_fixture__ = True
        touched = []
        class FakeAccount:
            def advance_day(self): touched.append(True)
        fake.FakeAccount = FakeAccount; captured = FakeAccount().advance_day
        sys.modules[fake.__name__] = fake
        guard = SourceOnlyGuard()
        try:
            with self.assertRaisesRegex(SourceBoundaryViolation, 'PRELOADED_FINANCIAL_GRAPH'):
                with guard: captured()
            self.assertFalse(touched); self.assertEqual(guard.attempts['financial_imports'], 1)
        finally: sys.modules.pop(fake.__name__, None)

    def test_nonattempt_or_frozen_output_rejected_before_source_capture(self):
        go, go_sha, review, review_sha = fake_authority()
        guard = SourceOnlyGuard(read_paths=source_read_paths())
        with guard:
            with patch.object(source, 'capture_year', side_effect=AssertionError('NO_SOURCE_READ')):
                for output in (c.ROOT / 'original_cs_mom21_D_20261015' / 'attempt', c.HERE / 'not_an_attempt'):
                    with self.assertRaisesRegex(ValueError, 'OUTPUT'):
                        source.prepare_source_only(output, source_go_raw=go, expected_source_go_sha256=go_sha,
                            review_raw=review, expected_review_sha256=review_sha)
        self.assertFalse(entry._ACTIVE_SOURCE)

    def test_cli_failure_persists_observed_stop_without_source_scope_or_masking(self):
        import prepare_cs_source as cli
        go, go_sha, review, review_sha = fake_authority()
        base = c.HERE / 'source_attempts'
        output = base / 'GENERATED_STOP_TEST_ONLY'
        if output.exists():
            raise AssertionError('EXCLUSIVE_GENERATED_TEST_OUTPUT_REQUIRED')
        try:
            with tempfile.TemporaryDirectory(dir=c.HERE) as td:
                td = Path(td); go_path = td / 'GENERATED_SOURCE_AUTHORIZATION.json'; review_path = td / 'GENERATED_REVIEW.json'
                go_path.write_bytes(go); review_path.write_bytes(review)
                argv = ['prepare_cs_source.py', '--output', str(output), '--source-go', str(go_path),
                    '--source-go-sha', go_sha, '--source-review', str(review_path), '--source-review-sha', review_sha,
                    '--cpu', str(min(os.sched_getaffinity(0)))]
                with patch.object(sys, 'argv', argv), patch.object(cli.resource, 'setrlimit'), \
                        patch.object(cli.signal, 'signal'), patch.object(cli.signal, 'alarm'), \
                        patch.object(source, 'prepare_source_only', side_effect=ValueError('GENERATED_STOP_BEFORE_SOURCE')):
                    with self.assertRaisesRegex(ValueError, 'GENERATED_STOP_BEFORE_SOURCE'):
                        cli.main()
            stopped = c.exact_object((output / 'STOP_SOURCE_TARGET_PREPARATION.json').read_bytes())
            self.assertTrue(stopped['source_scopes_revoked']); self.assertTrue(stopped['recording_scopes_revoked'])
            self.assertFalse(any(stopped['forbidden_attempts'].values()))
            self.assertEqual(stopped['status'], 'STOP_SOURCE_TARGET_ONLY_NO_FINANCIAL_ADMISSION')
        finally:
            if output.exists(): shutil.rmtree(output)
        self.assertFalse(entry._ACTIVE_SOURCE)


if __name__ == '__main__':
    unittest.main()
