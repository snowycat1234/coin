"""Synthetic metadata, dispatcher, transition prohibition, gates and resources."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import audit_all
import cold_audit
import gate
import provenance as p


def plan():
    return {'cases': [{'case_id': base, 'year': 2021, 'arm': arm,
        'symbols': p.SYMBOLS.copy(), 'calendar': p.CALENDAR.copy(), 'protective_enabled': False,
        'source_index_SHA256': p.SOURCE_SHA, 'target_archive_SHA256': p.TARGET_SHA,
        'source_index_local_locator': 'coin_2021_source_closure_20261013/prepared_2021/SOURCE_INDEX.json',
        'target_archive_local_locator': 'coin_2021_strategy_comparison_20261013/targets/Y2021.npz',
        'target_dtype': '<f8', 'target_shape': [365, 5]}
        for base, arm in zip(p.BASE_IDS, p.ARMS)], 'case_count': 4, 'modes': ['ORIGINAL'],
        'new_historical_wallets_executed': 0, 'status': 'FROZEN_FOUR_FULL2021_FINE_ORIGINAL_CASES_ZERO_HISTORY'}


def mem():
    return {'SwapTotal': 0, 'active_swaps': 0, 'cgroup_swap_current': None,
        'host_used': 2_000_000_000, 'cgroup_limit_verified': False,
        'cgroup_memory_current': None, 'cgroup_memory_max': None}


def controller():
    return {'status': 'ALL_CASES_FINISHED', 'unstarted_case_ids': [],
        'per_case': {identity: {'exit_code': 0, 'peak_RSS': 1_000_000_000,
                              'stop_reason': None} for identity in p.CASE_IDS}}


class DispatcherTests(unittest.TestCase):
    def test_exact_explicit_four_case_dispatcher(self):
        self.assertEqual(p.verify_plan(plan()), list(p.CASE_IDS))
        for identity, base in zip(p.CASE_IDS, p.BASE_IDS):
            self.assertEqual(p.dispatch_case(identity, plan())['case_id'], base)
        for identity in ('Y2021_STATIC50_FINE_GUARD50', 'Y2024_STATIC50_FINE_ORIGINAL', 'Y2021_EXACTHALF_FINE_REENTRY50'):
            with self.assertRaises(ValueError):
                p.dispatch_case(identity, plan())

    def test_population_changes_and_control_reruns_rejected(self):
        for mutate in (lambda x: x['cases'].reverse(), lambda x: x['cases'].append(x['cases'][0]),
                       lambda x: x.update(case_count=12), lambda x: x.update(new_historical_wallets_executed=1)):
            value = plan(); mutate(value)
            with self.assertRaises(ValueError):
                p.verify_plan(value)

    def test_terminal_finished_and_partial_population(self):
        p.verify_controller_population(controller(), list(p.CASE_IDS))
        partial = controller(); partial['status'] = 'STOP_PARTIAL'
        partial['unstarted_case_ids'] = [p.CASE_IDS[2]]
        del partial['per_case'][p.CASE_IDS[2]]
        partial['per_case'][p.CASE_IDS[1]]['exit_code'] = -15
        partial['per_case'][p.CASE_IDS[1]]['stop_reason'] = 'HOST_USED'
        p.verify_controller_population(partial, list(p.CASE_IDS))
        # A violated historical RSS limit is retained in partial receipts.
        partial['per_case'][p.CASE_IDS[1]]['peak_RSS'] = 2_000_000_001
        p.verify_controller_population(partial, list(p.CASE_IDS))
        with self.assertRaises(ValueError):
            broken = controller(); broken['per_case'].pop(p.CASE_IDS[0]); p.verify_controller_population(broken, list(p.CASE_IDS))
        with self.assertRaises(ValueError):
            broken = controller(); broken['status'] = 'RUNNING'; p.verify_controller_population(broken, list(p.CASE_IDS))
        with self.assertRaises(ValueError):
            broken = controller(); broken['status'] = 'STOP_PARTIAL'; p.verify_controller_population(broken, list(p.CASE_IDS))

    def test_unstarted_partial_accepted_and_missing_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); receipt = controller()
            identity = p.CASE_IDS[0]
            self.assertEqual(p.case_availability(root, identity, receipt), 'STARTED_NO_RECOVERABLE_CHECKPOINT')
            case = root / identity; (case / 'recovery').mkdir(parents=True)
            (case / 'BINDING.json').write_text('{}'); (case / 'recovery/POINTER.json').write_text('{}')
            self.assertEqual(p.case_availability(root, identity, receipt), 'RECOVERABLE_PARTIAL_CHECKPOINT')
            (case / 'RESULT.json').write_text('{}')
            self.assertEqual(p.case_availability(root, identity, receipt), 'ACCEPTED_RESULT')
            receipt['unstarted_case_ids'] = [identity]
            with self.assertRaises(ValueError):
                p.case_availability(root, identity, receipt)


class NoTransitionTests(unittest.TestCase):
    def test_restore_transition_hooks_forbidden_and_exactly_restored(self):
        class Account:
            def execute_fill(self): return 'fill'
            def apply_funding(self): return 'fund'
            def update_marks(self): return 'mark'
        class Base:
            def advance_day(self): return 'advance'
            def schedule(self): return 'schedule'
            def attempt(self): return 'attempt'
            def funding_through(self): return 'funding'
            def risk_schedule(self): return 'risk'
            def observe(self): return 'observe'
        class Simulator(Base): pass
        before = dict(Simulator.__dict__)
        with cold_audit.forbid_financial_transitions(Simulator, Account):
            for name in ('advance_day', 'schedule', 'attempt', 'funding_through', 'risk_schedule', 'observe'):
                with self.assertRaisesRegex(RuntimeError, 'financial transition'):
                    getattr(Simulator(), name)()
            for name in ('execute_fill', 'apply_funding', 'update_marks'):
                with self.assertRaisesRegex(RuntimeError, 'financial transition'):
                    getattr(Account(), name)()
        self.assertEqual(dict(Simulator.__dict__), before)
        self.assertEqual(Simulator().advance_day(), 'advance')
        self.assertEqual(Account().execute_fill(), 'fill')

    def test_snapshot_state_and_journals_require_exact_identity(self):
        state = {'pending': {'a': {'target': '0.10', 'attempts': 1}},
                 'weights': {'0': {'a': 0.1}}, 'decision_kinds': {'0': {'a': 'DAILY_TARGET'}},
                 'reentry_events': [], 'terminal_attempt_observations': {}}
        from decimal import Decimal
        sim = SimpleNamespace(cursor=60_000_000, stop=None, rows_written=1,
            state_hash=lambda: 'hash', account=SimpleNamespace(snapshot=lambda: {'trades': [1]}),
            pending={'a': {'target': Decimal('0.10'), 'attempts': 1}}, weights={0: {'a': 0.1}},
            decision_kinds={0: {'a': 'DAILY_TARGET'}}, reentry_events=[], terminal_attempt_observations={})
        pointer = {'binding': {'case': 'synthetic'}, 'state_hash': 'hash', 'cursor': sim.cursor,
                   'stop': None, 'completed_minutes': 1, 'chunks': [{'rows': 1}]}
        snapshot = {'state': state, 'account': {'trades': [1]}}
        cold_audit.verify_snapshot_state(sim, snapshot, pointer, pointer['binding'])
        sim.reentry_events.append({'wrong': True})
        with self.assertRaises(ValueError):
            cold_audit.verify_snapshot_state(sim, snapshot, pointer, pointer['binding'])


class ResourceTests(unittest.TestCase):
    def test_process_detector_ignores_read_only_status_tools(self):
        script = '/workspace/' + audit_all.HISTORICAL_MARKERS[0]
        self.assertTrue(audit_all.is_historical_python_command(['/usr/bin/python3.12', script, '--worker-case', 'synthetic']))
        self.assertTrue(audit_all.is_historical_python_command(['python', '-u', script]))
        self.assertFalse(audit_all.is_historical_python_command(['grep', script]))
        self.assertFalse(audit_all.is_historical_python_command(['python', '-c', script]))
        self.assertFalse(audit_all.is_historical_python_command(['bash', '-lc', script]))

    def test_admit_one_observer_and_disclose_unverified_cgroup(self):
        result = audit_all.admission_check(mem(), {'external_reserved_bytes': 0, 'external_busy_cpus': [1]}, [],
                                           audit_all.DISK_RESERVE + audit_all.DISK_MARGIN, [0, 1])
        self.assertEqual(result['cpu'], 0)
        self.assertEqual(result['observer_RSS_commitment_bytes'], 2_000_000_000)
        self.assertIn('UNVERIFIED', result['cgroup_enforcement_claim'])

    def test_active_history_cap_swap_disk_cpu_and_cgroup_rejected(self):
        base = (mem(), {}, [], audit_all.DISK_RESERVE + audit_all.DISK_MARGIN, [0])
        variants = [(mem(), {}, [123], base[3], [0]),
                    ({**mem(), 'host_used': 6_000_000_001}, {}, [], base[3], [0]),
                    ({**mem(), 'SwapTotal': 1}, {}, [], base[3], [0]),
                    ({**mem(), 'cgroup_swap_current': 1}, {}, [], base[3], [0]),
                    (mem(), {}, [], audit_all.DISK_RESERVE, [0]),
                    (mem(), {'external_busy_cpus': [0]}, [], base[3], [0]),
                    ({**mem(), 'cgroup_limit_verified': True, 'cgroup_memory_current': 1,
                      'cgroup_memory_max': 2_000_000_000}, {}, [], base[3], [0])]
        for args in variants:
            with self.subTest(args=args), self.assertRaises(RuntimeError):
                audit_all.admission_check(*args)

    def test_runtime_stop_all_resource_conditions(self):
        self.assertIsNone(audit_all.runtime_stop(mem(), 0, audit_all.DISK_RESERVE, 1, []))
        self.assertEqual(audit_all.runtime_stop(mem(), audit_all.RSS_LIMIT + 1, audit_all.DISK_RESERVE, 1, []), 'WORKER_RSS')
        self.assertEqual(audit_all.runtime_stop(mem(), 0, audit_all.DISK_RESERVE, 1, [1]), 'HISTORICAL_PROCESS_REAPPEARED')
        self.assertEqual(audit_all.runtime_stop(mem(), 0, audit_all.DISK_RESERVE - 1, 1, []), 'DISK_RESERVE')
        self.assertEqual(audit_all.runtime_stop(mem(), 0, audit_all.DISK_RESERVE, audit_all.WALL_LIMIT + 1, []), 'WALL_SECONDS')


class GateTests(unittest.TestCase):
    def make_fixture(self, directory):
        here = Path(directory) / 'observer'; here.mkdir()
        state = Path(directory) / 'state'; state.mkdir()
        for name in gate.FILES:
            (here / name).write_text('synthetic fixture only\n')
        manifest = {'kind': 'PREPARED_FOUR_CASE_ZERO_ADVANCE_FULL2021_OBSERVER',
            'files_SHA256': {name: p.sha(here / name) for name in gate.FILES},
            'case_ids': list(p.CASE_IDS), 'frozen_full2021_manifest_SHA256': p.PINS['FROZEN_CODE.json'],
            'independent_pre_GO_receipt_SHA256': p.PINS['REVIEW_RECEIPT.json'],
            'historical_observer_executions_during_preparation': 0, 'source_index_SHA256': p.SOURCE_SHA,
            'target_archive_SHA256': p.TARGET_SHA, 'state_locator': str(p.STATE.relative_to(p.ROOT)),
            'terminal_inputs_binding': 'EXCLUSIVE_CREATE_AFTER_TERMINAL_HASH_BOUND_BY_POSTRUN_GO',
            'cold_observers': 4, 'report_observers': 1, 'new_historical_wallets_to_open': 0,
            'financial_advances': 0, 'controls_to_rerun': 0}
        (here / 'REVIEWED_POSTRUN_CODE.json').write_text(json.dumps(manifest))
        (here / 'TERMINAL_INPUTS.json').write_text('{}')
        for name in ('RUN_BINDING.json', 'RESOURCE_RECEIPTS.json'):
            (state / name).write_text('{}')
        review = {'status': 'PASS_INDEPENDENT_POSTRUN_PRE_EXECUTION_REVIEW',
            'manifest_SHA256': p.sha(here / 'REVIEWED_POSTRUN_CODE.json'), 'historical_observer_executions': 0}
        (here / 'POSTRUN_REVIEW_RECEIPT.json').write_text(json.dumps(review))
        go = {'parent_GO': True, 'approved_stages': ['AUDIT', 'REPORT'],
            'manifest_SHA256': review['manifest_SHA256'],
            'review_receipt_SHA256': p.sha(here / 'POSTRUN_REVIEW_RECEIPT.json'),
            'state_locator': str(state.relative_to(p.ROOT)),
            'run_binding_SHA256': p.sha(state / 'RUN_BINDING.json'),
            'controller_receipt_SHA256': p.sha(state / 'RESOURCE_RECEIPTS.json'),
            'terminal_inputs_SHA256': p.sha(here / 'TERMINAL_INPUTS.json'), 'historical_controller_released': True}
        (here / 'POSTRUN_GO.json').write_text(json.dumps(go))
        return here, state, go

    def test_exact_code_review_action_and_terminal_binding_required(self):
        with tempfile.TemporaryDirectory(dir=p.ROOT) as directory:
            here, state, go = self.make_fixture(directory)
            with patch.object(gate, 'verify_terminal_run', return_value=list(p.CASE_IDS)):
                self.assertTrue(gate.verify_observer_go('AUDIT', here, state)['parent_GO'])
                go['approved_stages'] = ['AUDIT']
                (here / 'POSTRUN_GO.json').write_text(json.dumps(go))
                with self.assertRaises(RuntimeError): gate.verify_observer_go('REPORT', here, state)
                (state / 'RESOURCE_RECEIPTS.json').write_text('{"changed": true}')
                with self.assertRaises(RuntimeError): gate.verify_observer_go('AUDIT', here, state)
            (here / 'cold_audit.py').write_text('changed')
            with self.assertRaises(ValueError): gate.verify_code_manifest(here)

    def test_terminal_hash_tamper_omission_and_release_refused(self):
        with tempfile.TemporaryDirectory(dir=p.ROOT) as directory:
            here, state, go = self.make_fixture(directory)
            with patch.object(gate, 'verify_terminal_run', return_value=list(p.CASE_IDS)):
                gate.verify_observer_go('AUDIT', here, state)
                (here / 'TERMINAL_INPUTS.json').write_text('{"tampered":true}')
                with self.assertRaisesRegex(RuntimeError, 'Separate parent GO'):
                    gate.verify_observer_go('AUDIT', here, state)
                go['terminal_inputs_SHA256'] = p.sha(here / 'TERMINAL_INPUTS.json')
                go['historical_controller_released'] = False
                (here / 'POSTRUN_GO.json').write_text(json.dumps(go))
                with self.assertRaisesRegex(RuntimeError, 'Separate parent GO'):
                    gate.verify_observer_go('AUDIT', here, state)
                del go['terminal_inputs_SHA256']
                (here / 'POSTRUN_GO.json').write_text(json.dumps(go))
                with self.assertRaisesRegex(RuntimeError, 'Separate parent GO'):
                    gate.verify_observer_go('AUDIT', here, state)

    def test_terminal_inventory_and_horizon_drift_refused(self):
        with tempfile.TemporaryDirectory(dir=p.ROOT) as directory:
            here = Path(directory)
            original = {'case_ids': list(p.CASE_IDS), 'files_SHA256': {'synthetic': 'hash'}}
            (here / 'TERMINAL_INPUTS.json').write_text(json.dumps(original))
            with patch.object(p, 'HERE', here), patch.object(p, 'capture_terminal_inputs', return_value=original):
                self.assertEqual(p.verify_terminal_run(), list(p.CASE_IDS))
            for changed in ({**original, 'case_ids': list(p.CASE_IDS)[1:]},
                            {**original, 'files_SHA256': {'synthetic': 'different'}}):
                with patch.object(p, 'HERE', here), patch.object(p, 'capture_terminal_inputs', return_value=changed):
                    with self.assertRaisesRegex(ValueError, 'terminal input population/hash changed'):
                        p.verify_terminal_run()

    def test_direct_worker_cannot_inherit_historical_GO(self):
        with patch.object(gate, 'verify_observer_go', return_value={'parent_GO': True}), patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'bounded postrun orchestrator'):
                gate.require_bounded_worker('AUDIT')

    def test_bounded_token_also_requires_real_process_limits(self):
        env = {'COIN_FULL2021_POSTRUN_BOUNDED': '1', 'COIN_FULL2021_POSTRUN_GO_SHA256': 'synthetic-sha'}
        with patch.object(gate, 'verify_observer_go', return_value={}), patch.object(gate, 'sha', return_value='synthetic-sha'), \
                patch.dict('os.environ', env, clear=True), patch.object(gate.os, 'sched_getaffinity', return_value={0}), \
                patch.object(gate.resource, 'getrlimit', side_effect=[(4_000_000_000, 4_000_000_000), (300, 300)]):
            gate.require_bounded_worker('AUDIT')
        with patch.object(gate, 'verify_observer_go', return_value={}), patch.object(gate, 'sha', return_value='synthetic-sha'), \
                patch.dict('os.environ', env, clear=True), patch.object(gate.os, 'sched_getaffinity', return_value={0}), \
                patch.object(gate.resource, 'getrlimit', side_effect=[(-1, -1), (300, 300)]):
            with self.assertRaisesRegex(RuntimeError, 'Actual one-CPU'):
                gate.require_bounded_worker('AUDIT')


    def test_CPU_unbounded_missing_and_wrong_affinity_refused(self):
        env={'COIN_FULL2021_POSTRUN_BOUNDED':'1','COIN_FULL2021_POSTRUN_GO_SHA256':'synthetic-sha'}
        for affinity,as_limit,cpu_limit in (({0},(4_000_000_000,4_000_000_000),(-1,-1)),
            ({0},(4_000_000_000,4_000_000_000),(301,301)),
            ({0},(4_000_000_000,-1),(300,300)),({0,1},(4_000_000_000,4_000_000_000),(300,300))):
            with self.subTest(limits=(affinity,as_limit,cpu_limit)), \
                patch.object(gate,'verify_observer_go',return_value={}),patch.object(gate,'sha',return_value='synthetic-sha'), \
                patch.dict('os.environ',env,clear=True),patch.object(gate.os,'sched_getaffinity',return_value=affinity), \
                patch.object(gate.resource,'getrlimit',side_effect=[as_limit,cpu_limit]):
                with self.assertRaisesRegex(RuntimeError,'Actual one-CPU'): gate.require_bounded_worker('AUDIT')


if __name__ == '__main__':
    unittest.main()
