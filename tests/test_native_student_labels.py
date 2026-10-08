"""Synthetic fixed policy/state sampling; no historical training or acquisition."""
from copy import deepcopy
from dataclasses import replace
import inspect
import json

import numpy as np
import pytest

from modules.native_action.availability import fit_available
from modules.native_action.availability_contract import CheckpointSchedule
from modules.native_action.interface import NativeExperiment
from modules.native_action.student_labels import (
    COLLECTION_SCHEMA, FixedStudent, TrainingWindow, collect_pass, detached_observation,
    student_from_reward_model, validate_student_label_clock,
)
from modules.native_action.teacher import causal_features, identity_digest, linear_ramp_risk_mapper, Proposal
from modules.native_action.train import E6, MODEL_SCHEMA, NativeRewardModel, fit, frozen_identity
from scripts.investment.perpetual_directional import DAY, MINUTE
from test_native_action_teacher import context, simulator


def experiment(*, missing=False):
    sim = simulator()
    checkpoints = CheckpointSchedule([])

    def context_at(d):
        c = context(d)
        if not missing:
            return c
        targets = c.expert_targets.copy()
        targets[5] = np.nan
        return replace(c, expert_targets=targets, action_available=np.array([1] * 5 + [0]),
                       checkpoint_schedule=checkpoints,
                       binding=dict(c.binding, rank_checkpoint_sha256=None,
                                    rank_checkpoint_schedule_sha256=checkpoints.sha256))

    return NativeExperiment(sim, context_at, linear_ramp_risk_mapper,
                            binding={'source_role': 'SYNTHETIC_ONLY', 'input_sha256': 'e' * 64})


def window(exp, *, sample=None):
    s = exp.simulator
    return TrainingWindow(s.start, s.end, s.end + DAY, s.end, s.start, s.end, sample)


def mixed_student(exp):
    s = exp.simulator
    names, _ = causal_features(s, exp.context_at(s.cursor))
    fixed = dict(desired=[0., .4, .1, .3, .2, 0.], target_scale=.7)

    def propose(observation):
        assert not hasattr(observation, 'simulator') and not hasattr(observation, 'window')
        assert not observation.context.expert_targets.flags.writeable
        p = exp.mapper(np.asarray(observation.budget), np.asarray(fixed['desired']), observation.context)
        return Proposal('ORIGINAL_MIXED', p.request, p.budget,
                        tuple(np.asarray(p.targets) * fixed['target_scale']), 'SAVED_EXACT_STUDENT')

    def adapter_fingerprint():
        return identity_digest(dict(source=inspect.getsource(propose),
                                    mapper_source=inspect.getsource(exp.mapper), config=fixed))

    student = FixedStudent(tuple(names), identity_digest(fixed), adapter_fingerprint(), s.start + DAY, s.end,
                           propose, lambda: identity_digest(fixed), adapter_fingerprint)
    return student, fixed


def original_replay(exp, student):
    s = exp.simulator
    decisions = []
    while s.cursor < s.end:
        c = exp.context_at(s.cursor)
        names, features = causal_features(s, c)
        obs = detached_observation(s, c, names, features)
        p = student.propose(obs)
        p.validate(s.budget, len(s.symbols))
        before = s.state_hash()
        s.budget = list(p.budget)
        assert s.advance_day(dict(zip(s.symbols, p.targets, strict=True)))['completed']
        decisions.append((before, s.state_hash(), p))
    return s, decisions


def numeric_model(exp):
    names, _ = causal_features(exp.simulator, exp.context_at(exp.simulator.cursor))
    coefficients = np.zeros((len(names) + 1, 6))
    coefficients[0, 3] = 1.
    c = exp.context_at(exp.simulator.cursor)
    return NativeRewardModel(np.zeros(len(names)), np.ones(len(names)), coefficients, tuple(names),
                             dict(schema=MODEL_SCHEMA, action_order=list(E6),
                                  frozen_identity=frozen_identity(c.binding),
                                  latest_label_available_us=exp.simulator.start + DAY,
                                  asof_us=exp.simulator.end, distribution_shift='TEST_ONLY'))


@pytest.fixture(scope='module')
def collected():
    exp = experiment(missing=True)
    student, _ = mixed_student(exp)
    labels, decisions = [], []
    sim, manifest = collect_pass(exp, student, window(exp), limit_seconds=90,
                                save_label=labels.append, save_decision=decisions.append)
    return sim, manifest, labels, decisions


def test_main_trajectory_matches_original_fixed_student_and_forks_are_isolated(collected):
    sim, manifest, labels, decisions = collected
    exp = experiment(missing=True)
    student, _ = mixed_student(exp)
    original, original_decisions = original_replay(exp, student)
    assert sim.state_hash() == original.state_hash()
    assert sim.snapshot() == original.snapshot()
    assert sim.result()['minute'].equals(original.result()['minute'])
    for key in ('summary', 'trades', 'funding', 'rejections', 'breaches', 'extrema'):
        assert sim.result()[key] == original.result()[key]
    for label, recorded, (before, after, proposal) in zip(labels, decisions, original_decisions, strict=True):
        assert label['state_hash'] == before == recorded['state_hash']
        assert label['main_state_after_hash'] == after == recorded['state_after_hash']
        assert label['candidates'][6]['state_after_hash'] == after
        assert label['student_proposal']['name'] == proposal.name
    assert manifest['completed_days'] == 3 and manifest['sampled_days'] == 3
    assert manifest['candidate_day_replays'] == 18 and manifest['main_day_replays'] == 3


def test_five_action_mask_has_no_fabricated_reward_or_target(collected):
    _, _, labels, _ = collected
    for label in labels:
        assert label['e6_available'] == [True] * 5 + [False]
        assert label['e6_valid'] == label['e6_available']
        assert label['e6_rewards_USDT'][5] is None
        assert label['candidates'][5]['completion'] == 'UNAVAILABLE_NOT_SIMULATED'
        assert 'targets' not in label['candidates'][5]
        json.dumps(label, allow_nan=False)


def test_non_onehot_exact_proposal_is_fair_competitor_with_bound_costs(collected):
    _, manifest, labels, _ = collected
    for label in labels:
        actual = label['candidates'][6]
        proposal = label['student_proposal']
        assert actual['request'] == list(proposal['request'])
        assert actual['targets'] == list(proposal['targets'])
        assert not any(np.array_equal(actual['request'], np.eye(6)[k]) for k in range(6))
        assert label['local_regret_USDT'] == pytest.approx(
            max(c['net_increment_USDT'] for c in label['candidates'] if c['valid'])
            - actual['net_increment_USDT'])
        assert label['local_regret_must_not_be_summed_as_NAV']
        assert actual['costs_USDT']['fees'] >= 0.
        assert actual['costs_USDT']['execution_cost'] >= 0.
        assert label['student_collection']['cost_profile'] == manifest['cost_profile']
        assert label['student_collection']['global_terminal_us'] == manifest['global_terminal_us']
        binding = label['student_collection']['student_binding']
        assert binding['feature_schema_sha256'] == identity_digest(label['feature_names'])


def test_mature_boundary_and_forced_terminal_paid_cash_close(collected):
    sim, manifest, labels, _ = collected
    terminal = labels[-1]
    assert terminal['label_available_us'] == manifest['training_end_us']
    validate_student_label_clock(terminal)
    assert terminal['forced_terminal_day'] and not terminal['optimization_allowed']
    assert terminal['e6_winner'] is None
    assert all(c['applied_targets'] == [0.] * len(sim.symbols)
               for c in terminal['candidates'] if c['valid'])
    assert terminal['candidates'][6]['costs_USDT']['fees'] > 0.
    assert sim.account.fees > 0 and all(p.quantity == 0 for p in sim.account.positions.values())
    assert manifest['model_improvement'] == 'NOT_TESTED' and manifest['refit_count'] == 0


def test_future_rewards_cannot_change_current_student_decision():
    first = []
    rewards = []
    for multiplier in (.85, 1.15):
        exp = experiment()
        sim = exp.simulator
        # Change only future execution marks; the current causal context is identical.
        for data in sim.window['market'].values():
            data['mark'][:] *= multiplier
            data['open'][:] *= multiplier
        student, _ = mixed_student(exp)
        labels, decisions = [], []
        collect_pass(exp, student, window(exp, sample=(sim.start,)), limit_seconds=90,
                     save_label=labels.append, save_decision=decisions.append)
        first.append(decisions[0])
        rewards.append(labels[0]['e6_rewards_USDT'])
    assert first[0]['proposal'] == first[1]['proposal']
    assert first[0]['state_hash'] == first[1]['state_hash']
    assert rewards[0] != rewards[1]


def test_selected_training_dates_preserve_unsampled_continuous_wallet(collected):
    full, _, _, _ = collected
    exp = experiment(missing=True)
    student, _ = mixed_student(exp)
    labels, decisions = [], []
    config = replace(window(exp, sample=(exp.simulator.start + DAY,)),
                     collect_start_us=exp.simulator.start + DAY, collect_end_us=exp.simulator.end - DAY)
    result, manifest = collect_pass(exp, student, config, limit_seconds=90,
                                    save_label=labels.append, save_decision=decisions.append)
    assert [r['decision_us'] for r in labels] == [config.collect_start_us]
    assert [r['sampled'] for r in decisions] == [False, True, False]
    assert result.snapshot() == full.snapshot()
    assert manifest['candidate_day_replays'] == 6


@pytest.mark.parametrize('change', [
    {'training_end_us': -DAY}, {'evaluation_start_us': -2 * DAY}, {'label_asof_us': -1},
    {'sample_decisions_us': 'evaluation'}, {'sample_decisions_us': 'duplicates'},
])
def test_invalid_windows_reject_before_future_replay(change, monkeypatch):
    exp = experiment()
    student, _ = mixed_student(exp)
    config = window(exp)
    if change.get('sample_decisions_us') == 'evaluation':
        change = {'sample_decisions_us': (config.evaluation_start_us,)}
    elif change.get('sample_decisions_us') == 'duplicates':
        change = {'sample_decisions_us': (exp.simulator.start,) * 2}
    else:
        change = {k: getattr(config, k) + v for k, v in change.items()}
    monkeypatch.setattr(exp.simulator, 'fork', lambda: pytest.fail('forbidden fork'))
    with pytest.raises(ValueError):
        collect_pass(exp, student, replace(config, **change))


def test_delayed_funding_maturity_crossing_boundary_is_not_saved(monkeypatch):
    exp = experiment()
    student, _ = mixed_student(exp)
    config = window(exp, sample=(exp.simulator.start,))
    exp.simulator.window['events'][0]['available_us'] = config.training_end_us + 1
    original = exp.simulator.state_hash()
    labels = []
    with pytest.raises(ValueError, match='maturity/interval'):
        collect_pass(exp, student, config, save_label=labels.append)
    assert labels == [] and exp.simulator.state_hash() == original


def test_publication_delay_inside_training_matures_at_actual_receipt():
    exp = experiment()
    student, _ = mixed_student(exp)
    delayed = exp.simulator.start + DAY + 1
    exp.simulator.window['events'][0]['available_us'] = delayed
    labels = []
    collect_pass(exp, student, window(exp, sample=(exp.simulator.start,)), limit_seconds=90,
                 save_label=labels.append)
    assert labels[0]['label_available_us'] == delayed
    validate_student_label_clock(labels[0])


def test_global_terminal_close_charges_fills_without_forced_final_zero_target():
    exp = experiment()
    exp.simulator.final_day_target_zero = False
    student, _ = mixed_student(exp)
    labels = []
    sim, manifest = collect_pass(exp, student, window(exp, sample=(exp.simulator.end - DAY,)),
                                limit_seconds=90, save_label=labels.append)
    assert not labels[0]['forced_terminal_day'] and not manifest['final_day_target_zero']
    terminal_fills = [t for t in sim.account.trades if t['signal_us'] == sim.end - 6 * MINUTE]
    assert terminal_fills and sum(t['fee_USDT_mid'] for t in terminal_fills) > 0
    assert all(p.quantity == 0 for p in sim.account.positions.values())
    assert labels[0]['candidates'][6]['costs_USDT']['fees'] > 0


@pytest.mark.parametrize('kind', ['evaluation_decision', 'late_maturity', 'future_student'])
def test_fit_admission_cannot_recycle_evaluation_or_immature_student_labels(collected, kind):
    _, _, labels, _ = collected
    rows = deepcopy(labels)
    contract = rows[0]['student_collection']
    if kind == 'evaluation_decision':
        rows[0]['decision_us'] = contract['evaluation_start_us']
    elif kind == 'late_maturity':
        rows[0]['label_available_us'] = contract['training_end_us'] + 1
    else:
        contract['student_binding']['training_label_end_us'] = contract['evaluation_start_us']
    # Both fit entry points reject tainted rows even when they would otherwise filter the date.
    with pytest.raises(ValueError):
        fit(rows)
    with pytest.raises(ValueError):
        fit_available(rows, start_us=rows[1]['decision_us'], end_us=rows[-1]['interval_end_us'],
                      asof_us=rows[-1]['interval_end_us'], checkpoint_schedule=CheckpointSchedule([]))


def test_model_changes_and_post_training_artifacts_fail_before_probe(monkeypatch):
    exp = experiment()
    student, fixed = mixed_student(exp)
    fixed['target_scale'] = .9
    monkeypatch.setattr(exp.simulator, 'fork', lambda: pytest.fail('forbidden probe'))
    with pytest.raises(ValueError, match='changed'):
        collect_pass(exp, student, window(exp))
    fixed['target_scale'] = .7
    with pytest.raises(ValueError, match='evaluation labels'):
        collect_pass(exp, replace(student, training_label_end_us=exp.simulator.end + 1), window(exp))
    with pytest.raises(ValueError, match='adapter/configuration changed'):
        collect_pass(exp, replace(student, adapter_fingerprint=lambda: 'b' * 64), window(exp))


def test_existing_reward_model_adapter_matches_original_student_runner():
    from modules.native_action.runner import run
    exp = experiment()
    # Frozen numeric coefficients, no model fitting in this test.
    model = numeric_model(exp)
    student = student_from_reward_model(model, exp.mapper)
    collected_sim, _ = collect_pass(exp, student, window(exp, sample=(exp.simulator.start,)), limit_seconds=90)
    original_exp = experiment()
    # Exercise the unmodified runner policy path, including its final-day CASH request.
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(dir='/workspace/coin-state/tests') as parent:
        original = run(original_exp, Path(parent) / 'original', 'student', model=model, limit_seconds=90)
    assert collected_sim.snapshot() == original.snapshot()


def test_reward_adapter_binds_real_mapper_configuration():
    exp = experiment()
    model = numeric_model(exp)
    config = {'target_scale': .7}

    def mapper(prior, request, day):
        p = linear_ramp_risk_mapper(prior, request, day)
        return replace(p, targets=tuple(np.asarray(p.targets) * config['target_scale']))

    student = student_from_reward_model(model, mapper)
    student.validate(window(exp))
    config['target_scale'] = .8
    with pytest.raises(ValueError, match='adapter/configuration changed'):
        student.validate(window(exp))


def test_original_unmasked_model_still_rejects_partial_action_inference(monkeypatch):
    exp = experiment(missing=True)
    student = student_from_reward_model(numeric_model(exp), exp.mapper)
    before = exp.simulator.state_hash()
    monkeypatch.setattr(type(exp.simulator), 'fork',
                        lambda self: pytest.fail('partial inference must fail before probe'))
    with pytest.raises(ValueError, match='Partial candidate inference'):
        collect_pass(exp, student, window(exp))
    assert exp.simulator.state_hash() == before


def test_cli_saves_bound_label_files_exclusively_without_fitting(tmp_path, monkeypatch, capsys):
    import hashlib
    import sys
    from modules.native_action import runner, student_labels

    exp = experiment()
    model_path = tmp_path / 'frozen.npz'
    numeric_model(exp).save(model_path)
    options_path = tmp_path / 'options.json'
    options_path.write_text('{}')
    config = window(exp, sample=(exp.simulator.start,))
    window_path = tmp_path / 'window.json'
    window_path.write_text(json.dumps(vars(config)))
    output = tmp_path / 'collection'
    monkeypatch.setattr(runner, 'load_experiment', lambda *a: experiment())
    monkeypatch.setattr(sys, 'argv', ['student_labels', '--adapter', 'unused:factory',
        '--options', str(options_path), '--model', str(model_path), '--window', str(window_path),
        '--output', str(output), '--limit-seconds', '90'])
    student_labels.main()
    manifest = json.loads((output / 'RUN.json').read_text())
    labels = [json.loads(row) for row in (output / 'student_train_labels.jsonl').read_text().splitlines()]
    decisions = (output / 'student_decisions.jsonl').read_text().splitlines()
    assert len(labels) == 1 and len(decisions) == 3
    assert manifest['student_binding']['model_artifact_sha256'] == hashlib.sha256(model_path.read_bytes()).hexdigest()
    assert manifest['source_binding'] == exp.binding
    assert 'student_state_collect' in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        student_labels.main()


def test_collection_schema_is_distinct_from_model_improvement_claim(collected):
    _, manifest, labels, _ = collected
    assert manifest['schema'] == COLLECTION_SCHEMA
    assert all(r['state_role'] == 'STUDENT_TRAIN_RELABEL' for r in labels)
    assert manifest['policy_use'] == 'OFFLINE_RETROSPECTIVE_FIXED_TRAINING_ARTIFACT'
