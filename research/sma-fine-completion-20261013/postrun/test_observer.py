"""Synthetic-only fixed dispatcher, transitions, gates and resource tests."""
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
    return {'case_count': 3, 'modes': ['ORIGINAL'], 'cases': [
        {'case_id': base, 'year': year, 'arm': 'SMA200_10PCT', 'symbols': p.SYMBOLS,
         'calendar': p.CALENDARS[year], 'protective_enabled': False,
         'target_dtype': '<f8', 'target_shape': [366 if year == 2024 else 365, 5],
         'existing_fine_controls': {arm: {'case_id': identity,
             'state_local_locator': str((p.OLD_STATE / identity).relative_to(p.ROOT))}
             for arm, identity in p.CONTROL_IDS[year].items()}}
        for year, base in zip(p.YEARS, p.BASE_IDS)]}


def mem():
    return dict(SwapTotal=0, active_swaps=[], host_used=1_000_000_000,
        cgroup_swap_current=0, cgroup_limit_verified=False)


class ObserverTests(unittest.TestCase):
    def test_fixed_dispatch_and_control_paths(self):
        original = plan()
        self.assertEqual(p.verify_plan(original), list(p.CASE_IDS))
        for identity, year in zip(p.CASE_IDS, p.YEARS):
            self.assertEqual(p.dispatch_case(identity, original)['year'], year)
        for change in ('guard', 'fourth_case', 'duplicate', 'control_path', 'old_control_guard', 'year'):
            value = deepcopy(original)
            if change == 'guard': value['modes'].append('GUARD50')
            if change == 'fourth_case': value['cases'].append(value['cases'][0])
            if change == 'duplicate': value['cases'][1]['case_id'] = value['cases'][0]['case_id']
            if change == 'control_path': value['cases'][0]['existing_fine_controls']['STATIC50']['state_local_locator'] = 'other/state'
            if change == 'old_control_guard': value['cases'][0]['existing_fine_controls']['STATIC50']['case_id'] += '_GUARD50'
            if change == 'year': value['cases'][0]['year'] = 2026
            with self.subTest(change=change), self.assertRaises(ValueError): p.verify_plan(value)
        with self.assertRaises(ValueError): p.dispatch_case('Y2021_SMA200_10PCT_FINE_ORIGINAL', original)

    def test_controller_keeps_negative_and_partial_populations(self):
        ids = list(p.CASE_IDS)
        row = dict(exit_code=0, stop_reason=None, peak_RSS=1)
        complete = dict(status='ALL_CASES_FINISHED', unstarted_case_ids=[], per_case=dict.fromkeys(ids, row))
        p.verify_controller_population(complete, ids)
        partial = dict(status='STOP_PARTIAL', unstarted_case_ids=ids[1:], per_case={ids[0]: dict(row, exit_code=1)})
        p.verify_controller_population(partial, ids)
        for changed in ({**complete, 'per_case': {ids[0]: row}}, {**partial, 'unstarted_case_ids': []},
                        {**complete, 'status': 'RUNNING'}, {**complete, 'per_case': dict.fromkeys(ids, {**row, 'exit_code': True})}):
            with self.assertRaises(ValueError): p.verify_controller_population(changed, ids)

    def test_restore_forbids_all_transitions_and_restores_methods(self):
        class Simulator:
            def advance_day(self): return 'original'
        class Account:
            def execute_fill(self): return 'original'
        before = dict(Simulator.__dict__)
        with cold_audit.forbid_financial_transitions(Simulator, Account):
            for name in ('advance_day', 'schedule', 'attempt', 'funding_through', 'risk_schedule', 'observe'):
                with self.assertRaises(RuntimeError): getattr(Simulator(), name)()
            for name in ('execute_fill', 'apply_funding', 'update_marks'):
                with self.assertRaises(RuntimeError): getattr(Account(), name)()
        self.assertEqual(dict(Simulator.__dict__), before)
        self.assertEqual(Account().execute_fill(), 'original')

    def test_snapshot_verifies_all_scheduler_journal_state(self):
        from decimal import Decimal
        state = {'pending': {'a': {'target': '0.1'}}, 'weights': {'0': {'a': .1}},
                 'decision_kinds': {'0': {'a': 'DAILY_TARGET'}}, 'reentry_events': []}
        sim = SimpleNamespace(cursor=60_000_000, stop=None, rows_written=1, state_hash=lambda: 'hash',
            account=SimpleNamespace(snapshot=lambda: {'trades': [1]}), pending={'a': {'target': Decimal('.1')}},
            weights={0: {'a': .1}}, decision_kinds={0: {'a': 'DAILY_TARGET'}}, reentry_events=[])
        binding = {'case': 'synthetic'}
        pointer = dict(binding=binding, state_hash='hash', cursor=sim.cursor, stop=None, completed_minutes=1, chunks=[{'rows': 1}])
        cold_audit.verify_snapshot_state(sim, {'state': state, 'account': {'trades': [1]}}, pointer, binding)
        sim.reentry_events.append(1)
        with self.assertRaises(ValueError): cold_audit.verify_snapshot_state(sim, {'state': state, 'account': {'trades': [1]}}, pointer, binding)

    def test_resource_admission_and_runtime_stop(self):
        free = audit_all.DISK_RESERVE + audit_all.DISK_MARGIN
        row = audit_all.admission_check(mem(), {'external_busy_cpus': [1]}, [], free, [0, 1])
        self.assertEqual(row['cpu'], 0)
        self.assertIn('UNVERIFIED', row['cgroup_enforcement_claim'])
        for args in ((mem(), {}, [12], free, [0]), ({**mem(), 'host_used': 6_000_000_001}, {}, [], free, [0]),
            ({**mem(), 'SwapTotal': 1}, {}, [], free, [0]), (mem(), {}, [], free - 1, [0]),
            (mem(), {'external_busy_cpus': [0]}, [], free, [0])):
            with self.assertRaises(RuntimeError): audit_all.admission_check(*args)
        self.assertIsNone(audit_all.runtime_stop(mem(), 0, free, 1, []))
        self.assertEqual(audit_all.runtime_stop(mem(), audit_all.RSS_LIMIT + 1, free, 1, []), 'WORKER_RSS')
        self.assertEqual(audit_all.runtime_stop(mem(), 0, free, 1, [12]), 'HISTORICAL_PROCESS_REAPPEARED')
        self.assertEqual(audit_all.runtime_stop(mem(), 0, free, audit_all.WALL_LIMIT + 1, []), 'WALL_SECONDS')

    def test_historical_process_detector(self):
        script = '/workspace/' + audit_all.HISTORICAL_MARKERS[0]
        self.assertTrue(audit_all.is_historical_python_command(['python', '-u', script]))
        self.assertFalse(audit_all.is_historical_python_command(['grep', script]))
        self.assertFalse(audit_all.is_historical_python_command(['python', '-c', script]))

    def test_direct_worker_refused_without_real_bounds(self):
        with patch.object(gate, 'verify_observer_go'), patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(RuntimeError): gate.require_bounded_worker('AUDIT')
        env = {'COIN_SMA_FINE_POSTRUN_BOUNDED': '1', 'COIN_SMA_FINE_POSTRUN_GO_SHA256': 'sha'}
        for aslim, cpulim, affinity in (((4_000_000_000, 4_000_000_000), (300, 300), {0}),
            ((-1, -1), (300, 300), {0}), ((4_000_000_000, 4_000_000_000), (-1, -1), {0}),
            ((4_000_000_000, 4_000_000_000), (300, 300), {0, 1})):
            with patch.object(gate, 'verify_observer_go'), patch.object(gate, 'sha', return_value='sha'), \
                patch.dict('os.environ', env, clear=True), patch.object(gate.os, 'sched_getaffinity', return_value=affinity), \
                patch.object(gate.resource, 'getrlimit', side_effect=[aslim, cpulim]):
                if min(aslim) > 0 and min(cpulim) > 0 and len(affinity) == 1: gate.require_bounded_worker('AUDIT')
                else:
                    with self.assertRaises(RuntimeError): gate.require_bounded_worker('AUDIT')

    def test_missing_GO_blocks_all_financial_imports(self):
        with patch.object(cold_audit, 'require_bounded_worker', side_effect=RuntimeError('no GO')), \
             patch.object(cold_audit, 'read', side_effect=AssertionError('input read')):
            with self.assertRaisesRegex(RuntimeError, 'no GO'): cold_audit.main(p.CASE_IDS[0])

    def test_paths_refuse_escape(self):
        for locator in ('../outside', '/tmp/outside'):
            with self.assertRaises(ValueError): p.safe_path(p.HERE, locator)

    def test_bound_source_hash_byte_population_without_history(self):
        with tempfile.TemporaryDirectory(dir=p.HERE) as directory:
            root = Path(directory); source = root / 'source'; (source / 'months').mkdir(parents=True)
            months = []
            for month in range(1, 13):
                label = f'2023-{month:02d}'; path = source / 'months' / (label + '.npz'); path.write_bytes(b'synthetic bytes')
                months.append(dict(month=label, source_NPZ_SHA256=p.sha(path), source_NPZ_bytes=path.stat().st_size))
            files = {}
            for name in ('DAILY.json', 'EVENTS.json'):
                path = source / name; path.write_text('{}'); files[name] = dict(SHA256=p.sha(path), bytes=2)
            index = dict(calendar=p.CALENDARS[2023], symbol_order=p.SYMBOLS, months=months, files=files)
            path = source / 'SOURCE_INDEX.json'; path.write_text(json.dumps(index))
            case = dict(year=2023, source_index_local_locator='source/SOURCE_INDEX.json', source_index_SHA256=p.sha(path), calendar=p.CALENDARS[2023], symbols=p.SYMBOLS)
            with patch.object(p, 'ROOT', root):
                p.verify_source_files(case)
                (source / 'months/2023-12.npz').write_bytes(b'changed')
                with self.assertRaises(ValueError): p.verify_source_files(case)

    def test_exact_2025_metadata_schema_checks_operational_files_only(self):
        with tempfile.TemporaryDirectory(dir=p.HERE) as directory:
            root = Path(directory); source = root / 'source'; (source / 'months').mkdir(parents=True)
            months = []
            for month in range(1, 13):
                label = f'2025-{month:02d}'; path = source / 'months' / (label + '.npz'); path.write_bytes(b'synthetic bytes')
                months.append(dict(month=label, source_NPZ_SHA256=p.sha(path), source_NPZ_bytes=path.stat().st_size))
            files = {}
            for name in ('DAILY.json', 'EVENTS.json'):
                path = source / name; path.write_text('{}'); files[name] = dict(SHA256=p.sha(path), bytes=2)
            # Extra bound index entries are nonoperational metadata, not new
            # observer inputs; no extra file is created or read by this test.
            files.update({'Y2025.npz': {'SHA256': 'unused'}, 'Y2025_RISK.json': {'SHA256': 'unused'}})
            index = dict(calendar=p.CALENDARS[2025], symbol_order=p.SYMBOLS, months=months, files=files)
            path = source / 'SOURCE_INDEX.json'; path.write_text(json.dumps(index))
            case = dict(year=2025, source_index_local_locator='source/SOURCE_INDEX.json', source_index_SHA256=p.sha(path), calendar=p.CALENDARS[2025], symbols=p.SYMBOLS)
            with patch.object(p, 'ROOT', root):
                p.verify_source_files(case)
                (source / 'EVENTS.json').write_text('{"changed":true}')
                with self.assertRaises(ValueError): p.verify_source_files(case)
                (source / 'EVENTS.json').write_text('{}')
                index['files']['OTHER.json'] = {'SHA256': 'unused'}
                path.write_text(json.dumps(index)); case['source_index_SHA256'] = p.sha(path)
                with self.assertRaises(ValueError): p.verify_source_files(case)

    def test_exact_manifest_review_GO_and_terminal_pins(self):
        with tempfile.TemporaryDirectory(dir=p.HERE) as directory:
            here = Path(directory); state = here / 'state'; state.mkdir()
            for name in gate.FILES:
                (here / name).write_text('synthetic\n')
            manifest = dict(kind='PREPARED_FIXED_THREE_SMA_ZERO_ADVANCE_OBSERVER',
                files_SHA256={name: p.sha(here / name) for name in gate.FILES}, dependencies_SHA256={},
                case_ids=list(p.CASE_IDS), state_locator=str(p.STATE.relative_to(p.ROOT)),
                cold_observers=3, report_observers=1, new_historical_wallets_to_open=0, financial_advances=0,
                controls_to_rerun=0, historical_observer_executions_during_preparation=0,
                terminal_inputs_binding='EXCLUSIVE_CREATE_AFTER_TERMINAL_HASH_BOUND_BY_POSTRUN_GO')
            (here / 'REVIEWED_POSTRUN_CODE.json').write_text(json.dumps(manifest))
            (here / 'TERMINAL_INPUTS.json').write_text('{}')
            for name in ('RUN_BINDING.json', 'RESOURCE_RECEIPTS.json'):
                (state / name).write_text('{}')
            review = dict(status='PASS_INDEPENDENT_POSTRUN_PRE_EXECUTION_REVIEW',
                manifest_SHA256=p.sha(here / 'REVIEWED_POSTRUN_CODE.json'), historical_observer_executions=0)
            (here / 'POSTRUN_REVIEW_RECEIPT.json').write_text(json.dumps(review))
            go = dict(parent_GO=True, approved_stages=['AUDIT', 'REPORT'], manifest_SHA256=review['manifest_SHA256'],
                review_receipt_SHA256=p.sha(here / 'POSTRUN_REVIEW_RECEIPT.json'), state_locator=str(state.relative_to(p.ROOT)),
                run_binding_SHA256=p.sha(state / 'RUN_BINDING.json'), controller_receipt_SHA256=p.sha(state / 'RESOURCE_RECEIPTS.json'),
                terminal_inputs_SHA256=p.sha(here / 'TERMINAL_INPUTS.json'), historical_controller_released=True)
            (here / 'POSTRUN_GO.json').write_text(json.dumps(go))
            with patch.object(gate, 'verify_terminal_run', return_value=list(p.CASE_IDS)):
                self.assertTrue(gate.verify_observer_go('AUDIT', here, state)['parent_GO'])
                for key, value in (('approved_stages', ['AUDIT']), ('historical_controller_released', False), ('terminal_inputs_SHA256', 'bad')):
                    wrong = {**go, key: value}; (here / 'POSTRUN_GO.json').write_text(json.dumps(wrong))
                    with self.assertRaises(RuntimeError): gate.verify_observer_go('REPORT', here, state)
                (here / 'POSTRUN_GO.json').write_text(json.dumps(go))
                (state / 'RESOURCE_RECEIPTS.json').write_text('{"changed":true}')
                with self.assertRaises(RuntimeError): gate.verify_observer_go('AUDIT', here, state)
            (here / 'cold_audit.py').write_text('changed')
            with self.assertRaises(ValueError): gate.verify_code_manifest(here)


if __name__ == '__main__':
    unittest.main()
