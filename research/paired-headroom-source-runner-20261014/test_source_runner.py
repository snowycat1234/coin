"""Generated arrays/files only; no historical source or wallet reads."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys
from unittest import mock
import numpy as np
gate = sys.modules.get('source_gate')
a = sys.modules.get('source_analysis')
if gate is None or a is None or not getattr(gate, '_verified_source_SHA256', None) or not getattr(a, '_verified_source_SHA256', None):
    raise RuntimeError('USE_HASH_BOUND_SYNTHETIC_CLI')


class SourceRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roots = gate.read(os.environ['PAIRED_TEST_CODE_ROOTS'])
        cls.pins, cls.cases = gate.verify_dependencies(cls.roots)
        cls.paired = gate.load_paired(cls.roots)
        cls.adapter = gate.import_file('_synthetic_exact_input', Path(cls.roots['input_module']) / 'inherited_input_binding.py', cls.pins['input_publication']['files']['inherited_input_binding.py']['SHA256'])
        cls.cli = gate.import_file('_synthetic_source_cli', gate.HERE / 'source_cli.py', gate.read(gate.HERE / 'RUNNER_MANIFEST.json')['files_SHA256']['source_cli.py'])
        for name in ('sha', 'read', 'check', 'import_file'):
            setattr(cls.cli, name, getattr(gate, name))

    def fixture(self, n=46080):
        clocks = np.arange(n, dtype=np.int64) * a.MINUTE
        x = np.arange(n, dtype=np.float64)
        mark = 100 * np.exp(.01 * np.sin(x / 77))
        opened = np.r_[100., mark[:-1]] * np.exp(.003 * np.cos(x / 39))
        return {'times': clocks, 'mark': mark, 'open': opened}

    def test_dependency_and_case_scope(self):
        self.assertEqual(set(self.cases['years']), {'2023', '2024', '2025'})
        self.assertEqual(self.cases['initial_prior_year_minute_warmup'], 'NONE_ADDED; retain original in-year30day warmup')

    def test_three_fixed_prefixes_and_suffix_changes(self):
        source = self.fixture(47520)
        flags = np.zeros(len(source['times']), bool)
        feature = self.paired.features(source['times'], source['mark'], source['open'], flags)
        checks = a.causal_checks(self.paired, source, flags, feature)
        self.assertEqual(len(checks), 3)
        self.assertTrue(all(r['standalone_prefix_equal'] and r['future_clock_price_mask_perturbation_equal'] for r in checks))

    def test_lossless_all_states_roundtrip(self):
        source = self.fixture()
        flags = np.zeros(len(source['times']), bool)
        feature = self.paired.features(source['times'], source['mark'], source['open'], flags)
        runs = a.lossless_runs(feature)
        decoded = a.decode_runs(runs, len(source['times']))
        a.equal_prefix(feature, decoded, len(source['times']))
        for field in a.FIELDS:
            ready = feature['ready']
            np.testing.assert_array_equal(feature[field][ready].view(np.uint64), decoded[field][ready].view(np.uint64))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'generated.npz'
            np.savez_compressed(path, **runs)
            with np.load(path, allow_pickle=False) as z:
                restored = {k: z[k].copy() for k in z.files}
            a.equal_prefix(feature, a.decode_runs(restored, len(source['times'])), len(source['times']))

    def test_signed_zero_preserved_in_ready_runs(self):
        f = {'ready': np.array([True, True]), 'reason': np.array(['READY', 'READY'])}
        f.update({k: np.array([0., -0.]) for k in a.FIELDS})
        r = a.lossless_runs(f)
        self.assertEqual(len(r['start_row']), 2)
        restored = a.decode_runs(r, 2)
        np.testing.assert_array_equal(restored['long_hurdle'].view(np.uint64), f['long_hurdle'].view(np.uint64))

    def test_full_daily_count_and_difference_decomposition(self):
        source = self.fixture()
        f = self.paired.features(source['times'], source['mark'], source['open'])
        summary = a.summarize(source['times'], f)
        days = a.daily_summaries(source['times'], f)
        self.assertEqual(len(days), 32)
        self.assertEqual(sum(d['ready_rows'] for d in days), summary['ready_rows'])
        for direction in ('long', 'short'):
            for row in summary['differences'][direction].values():
                self.assertEqual(row['exact_equal'] + row['left_greater'] + row['left_less'], summary['ready_rows'])

    def test_incomplete_day_is_rejected(self):
        source = self.fixture(46081)
        f = self.paired.features(source['times'], source['mark'], source['open'])
        with self.assertRaisesRegex(ValueError, 'COMPLETE_UTC_DAYS'):
            a.daily_summaries(source['times'], f)

    def test_generated_month_uses_original_schema(self):
        n = 1440
        source = self.fixture(n)
        symbols = self.cases['symbols']
        arrays = {'times': source['times']}
        for symbol in symbols:
            arrays.update({symbol + '_open': source['open'], symbol + '_mark': source['mark'],
                           symbol + '_close': source['open'], symbol + '_quote_volume': np.ones(n)})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'months').mkdir()
            path = root / 'months/generated.npz'
            np.savez_compressed(path, **arrays)
            rec = {'month': 'generated', 'minutes': n, 'source_NPZ_SHA256': gate.sha(path), 'source_NPZ_bytes': path.stat().st_size}
            # Exercise the exact inherited primitives without pretending a toy is a year.
            checked = self.adapter.check_file(root, 'months/generated.npz', {'SHA256': rec['source_NPZ_SHA256'], 'bytes': rec['source_NPZ_bytes']})
            with np.load(checked, allow_pickle=False) as z:
                self.adapter.schema(z, 0, n)
            arrays['times'] = arrays['times'].astype(np.float64)
            np.savez_compressed(path, **arrays)
            with np.load(path, allow_pickle=False) as z:
                with self.assertRaisesRegex(ValueError, 'CLOCK_SCHEMA'):
                    self.adapter.schema(z, 0, n)

    def test_source_hash_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'generated.bin'
            path.write_bytes(b'generated')
            with self.assertRaisesRegex(ValueError, 'INPUT_BYTES_CHANGED'):
                self.adapter.check_file(folder, path.name, {'SHA256': '0' * 64, 'bytes': path.stat().st_size})

    def test_twelve_generated_month_loader_and_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'months').mkdir()
            records = []
            for month in range(12):
                times = np.arange(month * 1440, (month + 1) * 1440, dtype=np.int64) * a.MINUTE
                arrays = {'times': times}
                for symbol in self.cases['symbols']:
                    arrays.update({symbol + '_open': np.full(1440, 100. + month),
                        symbol + '_mark': np.full(1440, 101. + month),
                        symbol + '_close': np.full(1440, 100. + month), symbol + '_quote_volume': np.ones(1440)})
                name = 'generated-' + str(month)
                path = root / ('months/' + name + '.npz')
                np.savez_compressed(path, **arrays)
                records.append({'month': name, 'minutes': 1440, 'source_NPZ_SHA256': gate.sha(path), 'source_NPZ_bytes': path.stat().st_size})
            case = {'calendar': [0, 12 * 1440 * a.MINUTE], 'months': records}
            source = a.load_symbol(self.adapter, case, root, 'BTCUSDT')
            self.assertEqual(len(source['times']), 17280)
            self.assertEqual(source['mark'][1440], 102.)
            self.assertEqual(source['open'][1440], 101.)
            np.testing.assert_array_equal(source['times'], np.arange(17280, dtype=np.int64) * a.MINUTE)

    def test_generated_exact_overlay_coordinates(self):
        import csv
        stamps = self.pins['derived_csv2024']['open_time_ms']
        times = np.array([stamps[0] * 1000 - a.MINUTE, stamps[0] * 1000, stamps[1] * 1000], np.int64)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'generated.csv'
            with path.open('w') as f:
                writer = csv.DictWriter(f, fieldnames=['symbol', 'open_time_ms', 'source_missing'])
                writer.writeheader()
                writer.writerows({'symbol': symbol, 'open_time_ms': stamp, 'source_missing': 'True'}
                    for symbol in self.cases['symbols'] for stamp in stamps)
            pins = {'derived_csv2024': dict(self.pins['derived_csv2024'], SHA256=gate.sha(path))}
            mask = a.derived_mask(2024, times, 'BTCUSDT', path, pins, gate.sha)
            np.testing.assert_array_equal(mask, [False, True, True])

    def test_excluded_year_before_receipt_or_source_read(self):
        with self.assertRaisesRegex(ValueError, 'EXCLUDED_YEAR'):
            gate.authorization(2021, '0' * 64, 'MISSING', '0' * 64, 'MISSING', '0' * 64)

    def test_missing_go_refused_without_source_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'empty.json'
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'EXACT_REVIEW_GO'):
                gate.authorization(2023, '0' * 64, path, gate.sha(path), path, gate.sha(path))

    def test_original_derived_window_behavior(self):
        source = self.fixture(90000)
        flags = np.zeros(90000, bool)
        flags[44000:44002] = True
        f = self.paired.features(source['times'], source['mark'], source['open'], flags)
        original = self.paired.original.features(source['times'], source['mark'], source['open'], flags)
        np.testing.assert_array_equal(f['ready'], original['ready'])
        np.testing.assert_array_equal(f['reason'], original['reason'])

    def test_2024_requires_exact_derived_proof(self):
        with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL2024'):
            a.derived_mask(2024, np.arange(10, dtype=np.int64), 'BTCUSDT', None, self.pins, gate.sha)

    def test_wrong_overlay_for_other_year_refused(self):
        with self.assertRaisesRegex(ValueError, 'OVERLAY_ONLY'):
            a.derived_mask(2023, np.arange(10, dtype=np.int64), 'BTCUSDT', 'ANY', self.pins, gate.sha)

    def test_bad_run_coverage_refused(self):
        f = {'ready': np.ones(2, bool), 'reason': np.array(['READY', 'READY'])}
        f.update({k: np.ones(2) for k in a.FIELDS})
        r = a.lossless_runs(f)
        r['end_row_exclusive'][-1] = 1
        with self.assertRaisesRegex(ValueError, 'RUN_COVERAGE'):
            a.decode_runs(r, 2)

    def test_nonfinite_ready_and_non_nan_notready_refused(self):
        f = {'ready': np.array([False, True]), 'reason': np.array(['LESS_THAN_30D', 'READY'])}
        f.update({k: np.array([0., 1.]) for k in a.FIELDS})
        with self.assertRaisesRegex(ValueError, 'READY_NAN_CONTRACT'):
            a.summarize(np.array([0, a.MINUTE]), f)

    def test_worker_rejects_unlimited_invalid_soft_and_hard_limits(self):
        policy = gate.read(gate.HERE / 'RESOURCE_POLICY.json')
        environment = {'_PAIRED_SOURCE_PARENT_PID': '123', 'OPENBLAS_NUM_THREADS': '1',
                       'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
        with mock.patch.dict(os.environ, environment), mock.patch.object(os, 'getppid', return_value=123), mock.patch.object(os, 'sched_getaffinity', return_value={0}):
            for limits in [(-1, -1), (1, -1), (-1, 1), (0, 1), (1, 0), (-2, 1), (601, 601), (1, 601)]:
                with mock.patch.object(self.cli.resource, 'getrlimit', return_value=limits):
                    with self.assertRaisesRegex(ValueError, 'FINITE_SOFT_AND_HARD'):
                        self.cli.bounded_worker_guard(policy)

    def test_worker_requires_all_one_thread_environment_fields(self):
        policy = gate.read(gate.HERE / 'RESOURCE_POLICY.json')
        environment = {'_PAIRED_SOURCE_PARENT_PID': '123', 'OPENBLAS_NUM_THREADS': '1',
                       'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
        limits = lambda kind: (4000000000, 4000000000) if kind == self.cli.resource.RLIMIT_AS else (600, 600)
        with mock.patch.dict(os.environ, environment), mock.patch.object(os, 'getppid', return_value=123), mock.patch.object(os, 'sched_getaffinity', return_value={0}), mock.patch.object(self.cli.resource, 'getrlimit', side_effect=limits):
            self.cli.bounded_worker_guard(policy)
            for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
                with mock.patch.dict(os.environ, {name: '2'}):
                    with self.assertRaisesRegex(ValueError, 'ONE_MATH_THREAD'):
                        self.cli.bounded_worker_guard(policy)

    def test_saved_archive_actual_bytes_and_signed_zero(self):
        feature = {'ready': np.array([False, True, True]), 'reason': np.array(['MISSING', 'READY', 'READY'])}
        feature.update({field: np.array([np.nan, 0., -0.]) for field in a.FIELDS})
        runs = a.lossless_runs(feature)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'generated.npz'
            np.savez_compressed(path, **runs)
            self.assertTrue(a.validate_saved_archive(path, feature, runs, gate.sha(path), gate.sha))
            changed = {k: v.copy() for k, v in runs.items()}
            changed['long_hurdle'][-1] = 0.
            np.savez_compressed(path, **changed)
            with self.assertRaisesRegex(ValueError, 'COEFFICIENT_BITS'):
                a.validate_saved_archive(path, feature, runs, gate.sha(path), gate.sha)
            changed = {k: v.copy() for k, v in runs.items()}
            changed['ready'] = changed['ready'].astype(np.int64)
            np.savez_compressed(path, **changed)
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_SCHEMA'):
                a.validate_saved_archive(path, feature, runs, gate.sha(path), gate.sha)

    def test_saved_archive_hash_and_field_set_refused(self):
        feature = {'ready': np.array([True]), 'reason': np.array(['READY'])}
        feature.update({field: np.ones(1) for field in a.FIELDS})
        runs = a.lossless_runs(feature)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'generated.npz'
            np.savez_compressed(path, **runs)
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_HASH'):
                a.validate_saved_archive(path, feature, runs, '0' * 64, gate.sha)
            np.savez_compressed(path, **{k: v for k, v in runs.items() if k != 'long_hurdle'})
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_FIELDS'):
                a.validate_saved_archive(path, feature, runs, gate.sha(path), gate.sha)

    def test_direct_verified_source_ignores_valid_unpinned_bytecode(self):
        import py_compile
        import importlib.util
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'generated.py'
            trusted = b"VALUE='VERIFIED_SOURCE'\n"
            malicious = b"VALUE='CACHED_ATTACK' \n"
            malicious += b' ' * (len(trusted) - len(malicious))
            self.assertEqual(len(malicious), len(trusted))
            path.write_bytes(malicious)
            os.utime(path, (1234567890, 1234567890))
            py_compile.compile(str(path), cfile=importlib.util.cache_from_source(str(path)), doraise=True)
            path.write_bytes(trusted)
            os.utime(path, (1234567890, 1234567890))
            module = gate.import_file('_synthetic_verified_cache_regression', path, gate.sha(path))
            self.assertEqual(module.VALUE, 'VERIFIED_SOURCE')
            self.assertEqual(module._verified_source_SHA256, hashlib.sha256(trusted).hexdigest())

    def test_unpinned_vendor_initializer_rejected_before_execution(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'vendor').mkdir()
            for name in ('paired_buffer.py', 'vendor/headroom_buffer.py'):
                shutil.copyfile(Path(self.roots['paired_module']) / name, root / name)
            sentinel = root / 'executed.txt'
            (root / 'vendor/__init__.py').write_text('from pathlib import Path\nPath(' + repr(str(sentinel)) + ').write_text("UNPINNED")\n')
            saved = {name: sys.modules.pop(name) for name in ('vendor', 'vendor.headroom_buffer', '_fixed_paired_headroom') if name in sys.modules}
            try:
                with self.assertRaisesRegex(ValueError, 'UNPINNED_VENDOR_INITIALIZER'):
                    gate.load_paired({'paired_module': root})
                self.assertFalse(sentinel.exists())
            finally:
                sys.modules.update(saved)

    def test_direct_worker_missing_controller_pipe_refused(self):
        from types import SimpleNamespace
        args = SimpleNamespace(roots=os.environ['PAIRED_TEST_CODE_ROOTS'], runner_manifest_sha='0' * 64,
                               year=2023, review_sha='1' * 64, parent_go_sha='2' * 64)
        with mock.patch.dict(os.environ, {'_PAIRED_SOURCE_CONTROLLER_FD': '-1'}):
            with self.assertRaisesRegex(ValueError, 'VERIFIED_CONTROLLER_HANDOFF'):
                self.cli.require_controller_handoff(args)

    def test_bound_inherited_pipe_handoff_and_mismatch(self):
        from types import SimpleNamespace
        args = SimpleNamespace(roots=os.environ['PAIRED_TEST_CODE_ROOTS'], runner_manifest_sha='0' * 64,
                               year=2023, review_sha='1' * 64, parent_go_sha='2' * 64)
        for mismatch in (False, True):
            r, w = os.pipe()
            packet = self.cli.controller_packet(args)
            packet['parent_pid'] = 123
            if mismatch: packet['year'] = 2025
            os.write(w, json.dumps(packet).encode())
            os.close(w)
            with mock.patch.dict(os.environ, {'_PAIRED_SOURCE_CONTROLLER_FD': str(r), '_PAIRED_SOURCE_PARENT_PID': '123'}), mock.patch.object(os, 'getppid', return_value=123), mock.patch.object(os, 'kill'):
                if mismatch:
                    with self.assertRaisesRegex(ValueError, 'HANDOFF_BINDING_MISMATCH'):
                        self.cli.require_controller_handoff(args)
                else:
                    self.cli.require_controller_handoff(args)

    def test_monitor_exception_kills_reaps_and_preserves_failure_receipt(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'attempt'
            args = SimpleNamespace(output=str(out), roots=os.environ['PAIRED_TEST_CODE_ROOTS'],
                runner_manifest_sha='0' * 64, year=2023, review='UNUSED', review_sha='1' * 64,
                parent_go='UNUSED', parent_go_sha='2' * 64)
            guard = SimpleNamespace(process_rss=mock.Mock(return_value=100),
                memory_observation=mock.Mock(side_effect=RuntimeError('generated observer failure')))
            external = SimpleNamespace(controller_lock=lambda: nullcontext())
            child = SimpleNamespace(pid=999999, poll=mock.Mock(return_value=None), wait=mock.Mock(return_value=-9))
            with mock.patch.object(self.cli, 'resource_modules', return_value=(guard, external, None)), mock.patch.object(self.cli, 'resource_admission', return_value={'allowed_cpus': [0, 1]}), mock.patch.object(self.cli.subprocess, 'Popen', return_value=child), mock.patch.object(os, 'write', side_effect=lambda fd, data: len(data)), mock.patch.object(os, 'killpg') as kill:
                with self.assertRaises(SystemExit):
                    self.cli.dispatch(args, self.roots, self.pins, self.cases)
                kill.assert_called_once()
                child.wait.assert_called_once()
            receipt = gate.read(out / 'RESOURCE_RECEIPT.json')
            self.assertEqual(receipt['stop_reason'], 'MONITOR_OR_LAUNCH_EXCEPTION')
            self.assertEqual(receipt['monitor_or_launch_error']['message'], 'generated observer failure')
            self.assertTrue((out / 'WORKER.log').exists())

    def test_launch_exception_preserves_failure_receipt_without_child(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'attempt'
            args = SimpleNamespace(output=str(out), roots=os.environ['PAIRED_TEST_CODE_ROOTS'],
                runner_manifest_sha='0' * 64, year=2023, review='UNUSED', review_sha='1' * 64,
                parent_go='UNUSED', parent_go_sha='2' * 64)
            external = SimpleNamespace(controller_lock=lambda: nullcontext())
            with mock.patch.object(self.cli, 'resource_modules', return_value=(None, external, None)), mock.patch.object(self.cli, 'resource_admission', return_value={'allowed_cpus': [0, 1]}), mock.patch.object(self.cli.subprocess, 'Popen', side_effect=OSError('generated launch failure')), mock.patch.object(os, 'killpg') as kill:
                with self.assertRaises(SystemExit):
                    self.cli.dispatch(args, self.roots, self.pins, self.cases)
                kill.assert_not_called()
            receipt = gate.read(out / 'RESOURCE_RECEIPT.json')
            self.assertEqual(receipt['status'], 'FAIL_BOUNDED_SOURCE_ONLY_PRESERVED')
            self.assertEqual(receipt['monitor_or_launch_error']['message'], 'generated launch failure')


if __name__ == '__main__':
    unittest.main()
