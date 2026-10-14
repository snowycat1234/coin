"""Toy transport guards only. No historical source, account, or worker executes."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

import recovery_transport as r


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
    return path


class Fixture:
    """Synthetic checkpoint metadata, never interpreted as a financial wallet."""
    def __init__(self, root):
        self.root = Path(root)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.control_case = self.root / 'control'
        self.checkpoint = self.control_case / 'checkpoint'
        self.checkpoint.mkdir(parents=True)
        evidence = Path(r.__file__).parent / 'recovery_evidence'
        self.ledger = json.loads((evidence / 'CASE_LEDGER.json').read_text())
        self.results = json.loads((evidence / 'RESULTS.json').read_text())
        self.zero = json.loads((evidence / 'ZERO_ADVANCE_RECEIPT.json').read_text())
        self.binding = {'publication_commit': r.ORIGINAL_COMMIT, 'year': 2025, 'arm': 'control',
                        'V2_FREEZE_SHA256': r.ORIGINAL_FREEZE_SHA256, 'review_SHA256': r.ORIGINAL_REVIEW_SHA256,
                        'parent_GO_SHA256': r.ORIGINAL_GO_SHA256, 'source_index_SHA256': 'b' * 64,
                        'target_archive_SHA256': 'c' * 64}
        self.snapshot = {'market_range': [r.START_2025, r.END_2025],
                         'state': {'rows_written': 525600, 'cursor': r.END_2025, 'stop': None}}
        self.snapshot_path = self.checkpoint / 'STATE_000525600.json.gz'
        self.snapshot_path.write_bytes(gzip.compress(json.dumps(self.snapshot).encode(), mtime=0))
        self.snapshot_sha = r.sha(self.snapshot_path)
        chunks = []
        for index in range(365):
            path = self.checkpoint / f'DAY_{index:04d}.npz'
            path.write_bytes(b'TOY_METADATA_NO_WALLET_OR_SOURCE')
            chunks.append({'path': path.name, 'SHA256': r.sha(path), 'rows': 1440, 'columns': 36})
        self.pointer = {'binding': self.binding, 'completed_minutes': 525600, 'cursor': r.END_2025,
                        'stop': None, 'state_hash': r.CONTROL_STATE_HASH,
                        'snapshot_path': self.snapshot_path.name, 'snapshot_SHA256': self.snapshot_sha, 'chunks': chunks}
        self.pointer_path = write(self.checkpoint / 'POINTER.json', self.pointer)
        self.ledger_path = write(self.root / 'ledger.json', self.ledger)
        self.results_path = write(self.root / 'results.json', self.results)
        self.zero['control']['snapshot_SHA256'] = self.snapshot_sha
        self.zero_path = write(self.root / 'zero.json', self.zero)
        self.admission = {
            'schema': 'VALIDATED_FULL_CONTROL_RECOVERY_ADMISSION_V1',
            'status': 'PASS_SAVED_FINANCIAL_COMPLETION_ORIGINAL_TRANSPORT_FAILED',
            'original_publication_commit': r.ORIGINAL_COMMIT, 'recovery_publication_commit': r.RECOVERY_COMMIT,
            'original_failed_ledger_SHA256': r.sha(self.ledger_path),
            'zero_advance_receipt_SHA256': r.sha(self.zero_path), 'recovery_results_SHA256': r.sha(self.results_path),
            'snapshot_SHA256': self.snapshot_sha, 'state_hash': r.CONTROL_STATE_HASH,
            'completed_minutes': 525600, 'minute_chunks': 365, 'financial_advance_calls': 0,
            'original_transport_success': False, 'original_failed_ledger_unchanged': True,
            'checkpoint_binding': self.binding, 'checkpoint_binding_validation': 'PASS_ALL8_FIELDS',
            'checkpoint_POINTER_SHA256': r.sha(self.pointer_path),
        }
        self.admission_path = write(self.root / 'RECOVERY_ADMISSION_RECEIPT.json', self.admission)
        self.policy = json.loads((Path(r.__file__).parent / 'RESOURCE_POLICY.json').read_text())
        self.freeze_path = write(self.root / 'TRANSPORT_FREEZE.json', {'files_SHA256': {}})
        self.roots_path = write(self.root / 'roots.json', {'workspace': str(self.workspace), 'publication_repo': '/TOY',
                                                         'targets': '/TOY', 'source2025': '/TOY'})

    def pins(self):
        return patch.multiple(r, ORIGINAL_LEDGER_SHA256=r.sha(self.ledger_path),
                              RECOVERY_RECEIPT_SHA256=r.sha(self.zero_path), RECOVERY_RESULTS_SHA256=r.sha(self.results_path),
                              CONTROL_SNAPSHOT_SHA256=self.snapshot_sha, CONTROL_POINTER_SHA256=r.sha(self.pointer_path))

    def gate(self):
        return r.recovery_gate(self.ledger_path, self.zero_path, self.results_path, self.control_case,
                               self.admission_path, r.sha(self.admission_path), self.binding)

    def update_admission(self):
        write(self.admission_path, self.admission)


class Guards(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = Fixture(self.temporary.name)
        self.pin_patch = self.fixture.pins()
        self.pin_patch.start()

    def tearDown(self):
        self.pin_patch.stop()
        self.temporary.cleanup()

    def test_validated_recovery_accepts_distinct_effective_completion_and_preserves_failed_ledger(self):
        before = self.fixture.ledger_path.read_bytes()
        ledger, pointer = self.fixture.gate()
        effective = r.effective_completion(ledger, pointer, r.sha(self.fixture.admission_path))
        self.assertEqual(effective['completed'], [*r.PRIOR_COMPLETED, '2025_control'])
        self.assertFalse(effective['original_transport_control_success'])
        self.assertEqual(effective['original_control_attempt']['exit_code'], -9)
        self.assertEqual(ledger['completed'], r.PRIOR_COMPLETED)
        self.assertEqual(before, self.fixture.ledger_path.read_bytes())

    def test_failed_control_without_validated_recovery_rejects(self):
        self.fixture.zero['control']['status'] = 'NO_VALIDATED_RECOVERY'
        write(self.fixture.zero_path, self.fixture.zero)
        with patch.object(r, 'RECOVERY_RECEIPT_SHA256', r.sha(self.fixture.zero_path)):
            with self.assertRaisesRegex(r.GateError, 'FULL_ZERO_ADVANCE'):
                self.fixture.gate()

    def test_wrong_receipt_hash_rejects(self):
        self.fixture.zero_path.write_text('TAMPER')
        with self.assertRaisesRegex(r.GateError, 'EXACT_BYTES_REQUIRED'):
            self.fixture.gate()

    def test_pointer_and_chunk_tamper_rejects(self):
        original = self.fixture.pointer_path.read_bytes()
        self.fixture.pointer['chunks'][0]['SHA256'] = '0' * 64
        write(self.fixture.pointer_path, self.fixture.pointer)
        with self.assertRaisesRegex(r.GateError, 'EXACT_BYTES_REQUIRED:POINTER'):
            self.fixture.gate()
        self.fixture.pointer_path.write_bytes(original)
        (self.fixture.checkpoint / 'DAY_0000.npz').write_bytes(b'TAMPER')
        with self.assertRaisesRegex(r.GateError, 'EXACT_BYTES_REQUIRED:DAY_0000'):
            self.fixture.gate()

    def test_partial_checkpoint_rejects_even_if_new_receipt_pins_it(self):
        self.fixture.pointer['completed_minutes'] = 524160
        write(self.fixture.pointer_path, self.fixture.pointer)
        self.fixture.admission['checkpoint_POINTER_SHA256'] = r.sha(self.fixture.pointer_path)
        self.fixture.update_admission()
        with patch.object(r, 'CONTROL_POINTER_SHA256', r.sha(self.fixture.pointer_path)):
            with self.assertRaisesRegex(r.GateError, 'PARTIAL_OR_WRONG'):
                self.fixture.gate()

    def test_source_target_binding_mismatch_rejects(self):
        self.fixture.pointer['binding']['source_index_SHA256'] = '0' * 64
        write(self.fixture.pointer_path, self.fixture.pointer)
        self.fixture.admission['checkpoint_POINTER_SHA256'] = r.sha(self.fixture.pointer_path)
        self.fixture.update_admission()
        expected = dict(self.fixture.binding, source_index_SHA256='b' * 64)
        with self.assertRaises(r.GateError):
            r.recovery_gate(self.fixture.ledger_path, self.fixture.zero_path, self.fixture.results_path,
                            self.fixture.control_case, self.fixture.admission_path, r.sha(self.fixture.admission_path), expected)

    def test_zero_advance_and_original_failure_truth_required(self):
        self.fixture.admission['financial_advance_calls'] = 1
        self.fixture.update_admission()
        with self.assertRaisesRegex(r.GateError, 'ADMISSION_RECEIPT'):
            self.fixture.gate()

    def test_same_go_different_output_and_duplicate_namespace_reject(self):
        roots = {'workspace': str(self.fixture.workspace)}
        exact = self.fixture.workspace / r.OUTPUT_NAMESPACE
        self.assertEqual(r.candidate_output(roots, exact), exact)
        with self.assertRaisesRegex(r.GateError, 'SINGLE_CANDIDATE'):
            r.candidate_output(roots, self.fixture.workspace / 'another_output')
        exact.mkdir()
        with self.assertRaisesRegex(r.GateError, 'NO_DUPLICATE'):
            r.candidate_output(roots, exact)

    def test_cumulative_and_case_budgets_fail_closed_without_reset(self):
        self.assertEqual(r.remaining_seconds(1308.5219291619942, 0, 100, now=110), 590)
        for previous, now in ((3590, 105), (1308, 700), (float('nan'), 110)):
            with self.subTest(previous=previous, now=now):
                with self.assertRaises(r.GateError):
                    r.remaining_seconds(previous, 0, 100, now=now)

    def test_exact_new_output_cap_boundary_and_original_limit_unchanged(self):
        guard = SimpleNamespace(DISK_RESERVE=1, CASE_LIMIT=250_000_000, HOST_USED_LIMIT=8_000_000_000,
                                process_rss=lambda pid: 1, memory_observation=lambda: {'host_used': 1, 'SwapTotal': 0})
        process = SimpleNamespace(pid=123)
        case = self.fixture.root / 'case'
        with patch.object(r.time, 'monotonic', return_value=101), patch.object(r.shutil, 'disk_usage', return_value=SimpleNamespace(free=10**12)):
            with patch.object(r, 'case_bytes', return_value=500_000_000):
                self.assertIsNone(r.monitor_stop(guard, process, case, self.fixture.policy, 1308, 0, 100))
            with patch.object(r, 'case_bytes', return_value=500_000_001):
                self.assertEqual(r.monitor_stop(guard, process, case, self.fixture.policy, 1308, 0, 100),
                                 'REVIEWED_RECOVERY_TRANSPORT_CASE500MB_OUTPUT_CAP')
        self.assertEqual(guard.CASE_LIMIT, 250_000_000)

    def test_new_authorization_requires_review_root_hash_and_candidate_only_scope(self):
        f = self.fixture
        args = SimpleNamespace(transport_commit='1' * 40, transport_review=f.root / 'review.json',
                               transport_go=f.root / 'go.json', roots=f.roots_path,
                               recovery_admission_sha=r.sha(f.admission_path))
        review = {'schema': 'INDEPENDENT_RECOVERY_TRANSPORT_PUBLICATION_REVIEW_V1',
                  'status': 'PASS_EXACT_RECOVERY_TRANSPORT_NO_HISTORY', 'publication_commit': args.transport_commit,
                  'TRANSPORT_FREEZE_SHA256': r.sha(f.freeze_path), 'recovery_receipt_SHA256': r.RECOVERY_RECEIPT_SHA256,
                  'recovery_admission_receipt_SHA256': args.recovery_admission_sha}
        write(args.transport_review, review)
        args.transport_review_sha = r.sha(args.transport_review)
        go = {'schema': 'EXPLICIT_PARENT_RECOVERED_CONTROL_CANDIDATE_ONLY_GO_V1', 'parent_GO': True,
              'publication_commit': args.transport_commit, 'TRANSPORT_FREEZE_SHA256': r.sha(f.freeze_path),
              'transport_review_SHA256': args.transport_review_sha, 'original_publication_commit': r.ORIGINAL_COMMIT,
              'original_failed_ledger_SHA256': r.ORIGINAL_LEDGER_SHA256, 'recovery_publication_commit': r.RECOVERY_COMMIT,
              'recovery_receipt_SHA256': r.RECOVERY_RECEIPT_SHA256, 'recovery_admission_receipt_SHA256': args.recovery_admission_sha,
              'roots_SHA256': r.sha(args.roots), 'candidate_output_namespace': r.OUTPUT_NAMESPACE,
              'year': 2025, 'arms': ['candidate'], 'output_cap_bytes': 500_000_000, 'case_wall_seconds': 600,
              'six_case_cumulative_seconds': 3600, 'original_control_not_rerun': True, 'original_failed_ledger_unchanged': True}
        write(args.transport_go, go)
        args.transport_go_sha = r.sha(args.transport_go)
        with patch.object(r, 'HERE', f.root):
            self.assertEqual(r.transport_authorization(args, f.policy), r.sha(f.freeze_path))
            for key, value in (('arms', ['control', 'candidate']), ('roots_SHA256', '0' * 64), ('output_cap_bytes', 250_000_000)):
                bad = dict(go, **{key: value})
                write(args.transport_go, bad)
                args.transport_go_sha = r.sha(args.transport_go)
                with self.assertRaisesRegex(r.GateError, 'NEW_CANDIDATE_ONLY_GO'):
                    r.transport_authorization(args, f.policy)


if __name__ == '__main__':
    unittest.main(verbosity=2)
