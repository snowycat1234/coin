"""Synthetic boundary checks only; no historical teacher/model/market work."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import numpy as np
import pytest

from modules.native_action.availability import (AvailableRewardModel, fit_available,
                                               label_metrics_available, main)
from modules.native_action.availability_contract import CheckpointSchedule, candidate_mask
from modules.native_action.inputs import BoundE6Inputs
from modules.native_action.teacher import E6, SCHEMA, causal_features, linear_ramp_risk_mapper, replay_candidates
from modules.native_action.train import TRAIN_START, TRAIN_END, fit
from modules.native_action.runner import NativeExperiment, run
from scripts.investment.perpetual_directional import DAY
from test_native_action_inputs import bound_inputs
from test_native_action_teacher import context, simulator


START2022 = 1_641_859_200_000_000  # 2022-01-12 UTC; synthetic clocks only.


def schedule(start=TRAIN_START, switch=None):
    def entry(a, b, checkpoint):
        return dict(start_us=a, end_us=b, available_us=a,
                    training_label_end_us=a, checkpoint_sha256=checkpoint * 64)
    if switch is None:
        return CheckpointSchedule([entry(start, start + 30 * DAY, '1')])
    return CheckpointSchedule([entry(start, switch, '1'), entry(switch, switch + 30 * DAY, '4')])


def labels(start=START2022, masks=None, checkpoints=None):
    masks = masks if masks is not None else [[True] * 5 + [False]] * 4
    checkpoints = checkpoints if checkpoints is not None else CheckpointSchedule([])
    rows = []
    for i, mask in enumerate(masks):
        d = start + i * DAY
        c = context(d)
        binding = dict(c.binding, rank_checkpoint_sha256=checkpoints.at(d) if mask[5] else None,
                       rank_checkpoint_schedule_sha256=checkpoints.sha256)
        rows.append(dict(schema=SCHEMA, decision_us=d, interval_end_us=d + DAY,
                         label_available_us=d + DAY, feature_available_us=d,
                         action_order=list(E6), e6_available=list(mask), e6_valid=list(mask),
                         e6_rewards_USDT=[float(k - 8 + i / 10) if mask[k] else None for k in range(6)],
                         state_role='TEACHER_SELF', state_hash=str(i), global_native_upper_bound=False,
                         binding=binding, symbol_order=['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'],
                         feature_names=['market.vol30', 'wallet.nav_fraction'], features=[.1 + i / 20, 1. - i / 100]))
    return rows


def fitted(rows, checkpoints):
    start = rows[0]['decision_us']
    return fit_available(rows, start_us=start, end_us=start + len(rows) * DAY,
                         asof_us=start + len(rows) * DAY, checkpoint_schedule=checkpoints)


def test_missing_rank_has_no_reward_no_branch_and_preserves_source_wallet():
    sim = simulator()
    c = context(sim.cursor)
    missing = c.expert_targets.copy()
    missing[5] = np.nan
    clocks = c.expert_available_us.copy()
    clocks[5] += DAY
    checkpoints = CheckpointSchedule([])
    c = replace(c, expert_targets=missing, expert_available_us=clocks,
                action_available=np.array([1, 1, 1, 1, 1, 0]), checkpoint_schedule=checkpoints,
                binding=dict(c.binding, rank_checkpoint_sha256=None,
                             rank_checkpoint_schedule_sha256=checkpoints.sha256))
    original = sim.state_hash()
    called = []
    def mapper(prior, request, day):
        called.append(int(np.argmax(request)))
        return linear_ramp_risk_mapper(prior, request, day)
    row, winner, _ = replay_candidates(sim, c, mapper)
    assert called == list(range(5)) and sim.state_hash() == original
    assert row['e6_rewards_USDT'][5] is None and not row['e6_valid'][5]
    assert row['e6_available'] == [True] * 5 + [False]
    assert row['candidates'][5]['completion'] == 'UNAVAILABLE_NOT_SIMULATED'
    assert row['e6_winner'] < 5 and winner.cursor == sim.cursor + DAY
    json.dumps(row, allow_nan=False)
    names, x = causal_features(sim, c)
    assert x[names.index('expert.OOF_LEARNED_RANK.available')] == 0.


def test_all_missing_and_residual_unavailable_budget_fail_closed():
    with pytest.raises(ValueError, match='at least one'):
        candidate_mask([False] * 6)
    sim = simulator()
    sim.budget = [0., 0., 0., 0., 0., 1.]
    c = context(sim.cursor)
    checkpoints = CheckpointSchedule([])
    c = replace(c, action_available=np.array([1, 1, 1, 1, 1, 0]), checkpoint_schedule=checkpoints,
                binding=dict(c.binding, rank_checkpoint_sha256=None,
                             rank_checkpoint_schedule_sha256=checkpoints.sha256))
    with pytest.raises(ValueError, match='residual budget'):
        replay_candidates(sim, c, linear_ramp_risk_mapper)


def test_masked_loss_uses_negative_available_rewards_and_missing_head_stays_nan(tmp_path):
    checkpoints = CheckpointSchedule([])
    rows = labels(checkpoints=checkpoints)
    model = fitted(rows, checkpoints)
    assert model.metadata['train_start_us'] == START2022
    assert model.metadata['available_label_counts'] == [4] * 5 + [0]
    assert np.isnan(model.coefficients[:, 5]).all()
    row = rows[0]
    prediction = model.predict(row['features'], row['feature_names'], row['binding'],
                               decision_us=row['decision_us'], available=row['e6_available'])
    assert np.isnan(prediction[5]) and np.argmax(prediction[:5]) == 4
    assert label_metrics_available(model, rows)['winner_hit_rate'] == 1.
    z = np.column_stack((np.ones(4),
                         (np.asarray([r['features'] for r in rows]) - model.mean) / model.scale))
    y = np.asarray([r['e6_rewards_USDT'][:5] for r in rows])
    assert model.metadata['masked_training_MSE_USDT2'] == pytest.approx(np.mean((z @ model.coefficients[:, :5] - y) ** 2))
    path = tmp_path / 'masked.npz'
    model.save(path)
    restored = AvailableRewardModel.load(path)
    np.testing.assert_array_equal(restored.coefficients, model.coefficients)
    with pytest.raises(FileExistsError):
        model.save(path)


@pytest.mark.parametrize('bad', [0., 1e9, float('inf')])
def test_unavailable_reward_cannot_be_zero_or_a_fabricated_score(bad):
    rows = labels()
    rows[0]['e6_rewards_USDT'][5] = bad
    with pytest.raises(ValueError, match='never zero'):
        fitted(rows, CheckpointSchedule([]))


def test_first_available_rank_switch_and_later_checkpoint_changes_are_causal():
    start = START2022
    checkpoints = schedule(start + DAY, start + 2 * DAY)
    masks = [[1] * 5 + [0], [1] * 6, [1] * 6, [1] * 6]
    rows = labels(start, masks, checkpoints)
    model = fitted(rows, checkpoints)
    assert rows[0]['binding']['rank_checkpoint_sha256'] is None
    assert rows[1]['binding']['rank_checkpoint_sha256'] == '1' * 64
    assert rows[2]['binding']['rank_checkpoint_sha256'] == '4' * 64
    assert model.metadata['available_label_counts'] == [4] * 5 + [3]
    assert label_metrics_available(model, rows)['label_state_rows'] == 4
    wrong = deepcopy(rows[2])
    wrong['binding']['rank_checkpoint_sha256'] = '1' * 64
    with pytest.raises(ValueError, match='causally scheduled'):
        model.predict(wrong['features'], wrong['feature_names'], wrong['binding'],
                      decision_us=wrong['decision_us'], available=wrong['e6_available'])


def test_untrained_new_rank_requires_refit_not_zero_prediction():
    checkpoints = schedule(START2022 + 4 * DAY)
    rows = labels(checkpoints=checkpoints)
    model = fitted(rows, checkpoints)
    binding = dict(rows[0]['binding'], rank_checkpoint_sha256='1' * 64)
    with pytest.raises(ValueError, match='refit required'):
        model.predict(rows[0]['features'], rows[0]['feature_names'], binding,
                      decision_us=START2022 + 4 * DAY, available=[True] * 6)


@pytest.mark.parametrize('field', ['training_label_end_us', 'available_us'])
def test_teacher_checkpoint_future_leak_is_rejected(field):
    raw = schedule().entries
    raw[0][field] = raw[0]['start_us'] + 1
    with pytest.raises(ValueError, match='precede use'):
        CheckpointSchedule(raw)


def test_future_checkpoint_and_expert_clocks_fail_closed():
    sim = simulator()
    c = context(sim.cursor)
    checkpoints = schedule(sim.cursor + DAY)
    c = replace(c, action_available=np.ones(6, dtype=bool), checkpoint_schedule=checkpoints,
                binding=dict(c.binding, rank_checkpoint_schedule_sha256=checkpoints.sha256))
    with pytest.raises(ValueError, match='causally scheduled'):
        c.validate(sim)
    checkpoints = schedule(sim.cursor)
    c = replace(c, checkpoint_schedule=checkpoints,
                binding=dict(c.binding, rank_checkpoint_schedule_sha256=checkpoints.sha256),
                expert_available_us=np.full(6, sim.cursor + 1, dtype=np.int64))
    with pytest.raises(ValueError, match='causally available'):
        c.validate(sim)


def test_maturity_feature_leak_duplicate_and_all_missing_labels():
    rows = labels()
    checkpoints = CheckpointSchedule([])
    bad = deepcopy(rows)
    bad[0]['feature_available_us'] += 1
    with pytest.raises(ValueError, match='Causal feature'):
        fitted(bad, checkpoints)
    with pytest.raises(ValueError, match='Causal clocks'):
        label_metrics_available(fitted(rows, checkpoints), bad)
    bad = deepcopy(rows)
    bad[0]['label_available_us'] = bad[0]['decision_us']
    with pytest.raises(ValueError, match='label maturity'):
        fitted(bad, checkpoints)
    bad = deepcopy(rows)
    bad[1] = deepcopy(bad[0])
    with pytest.raises(ValueError, match='Duplicate'):
        fitted(bad, checkpoints)
    bad = deepcopy(rows)
    bad[0]['e6_available'] = [False] * 6
    with pytest.raises(ValueError, match='at least one'):
        fitted(bad, checkpoints)
    later = deepcopy(rows[0])
    later['decision_us'] += 100 * DAY
    later['features'] = [1e9, 1e9]
    model = fitted(rows, checkpoints)
    extended = fit_available(rows + [later], start_us=START2022, end_us=START2022 + 4 * DAY,
                             asof_us=START2022 + 4 * DAY, checkpoint_schedule=checkpoints)
    np.testing.assert_array_equal(model.coefficients, extended.coefficients)


def test_all_e6_fit_exactly_matches_the_existing_default():
    checkpoints = schedule()
    rows = labels(TRAIN_START, [[True] * 6] * 4, checkpoints)
    old = fit(rows, asof_us=TRAIN_END)
    new = fitted(rows, checkpoints)
    np.testing.assert_array_equal(new.mean, old.mean)
    np.testing.assert_array_equal(new.scale, old.scale)
    np.testing.assert_array_equal(new.coefficients, old.coefficients)


def test_bound_npz_opt_in_preserves_default_rejection_and_first_available_switch(tmp_path):
    existing, sim = bound_inputs(tmp_path)
    arrays = {k: v.copy() for k, v in existing.arrays.items()}
    arrays['action_eligible'] = np.ones((3, 8), dtype=bool)
    arrays['action_eligible'][0, 5] = False
    arrays['rank_checkpoint_sha256'] = np.asarray(['', '1' * 64, '1' * 64])
    arrays['expert_targets'][0, 5] = np.nan
    path = tmp_path / 'explicit.npz'
    np.savez_compressed(path, **arrays)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    field_map = {k: k for k in arrays}
    strict = BoundE6Inputs(path, checksum, field_map, existing.binding)
    with pytest.raises(ValueError, match='unavailable'):
        strict.context_at(sim.start)
    checkpoints = schedule(sim.start + DAY)
    bound = BoundE6Inputs(path, checksum, field_map, existing.binding,
                         availability_aware=True, checkpoint_schedule=checkpoints)
    first = bound.context_at(sim.start)
    first.validate(sim)
    assert first.binding['rank_checkpoint_sha256'] is None
    second = bound.context_at(sim.start + DAY)
    assert second.action_mask().all() and second.binding['rank_checkpoint_sha256'] == '1' * 64
    foreign = deepcopy(arrays)
    foreign['rank_checkpoint_sha256'][1] = '4' * 64
    wrong_path = tmp_path / 'foreign.npz'
    np.savez_compressed(wrong_path, **foreign)
    wrong = BoundE6Inputs(wrong_path, hashlib.sha256(wrong_path.read_bytes()).hexdigest(),
                         field_map, existing.binding, availability_aware=True, checkpoint_schedule=checkpoints)
    with pytest.raises(ValueError, match='causally scheduled'):
        wrong.context_at(sim.start + DAY)


def test_training_cli_has_explicit_range_and_schedule(tmp_path, monkeypatch, capsys):
    checkpoints = CheckpointSchedule([])
    rows = labels()
    label_file, schedule_file, output = tmp_path / 'rows.jsonl', tmp_path / 'schedule.json', tmp_path / 'model.npz'
    label_file.write_text('\n'.join(json.dumps(r) for r in rows))
    schedule_file.write_text('[]')
    monkeypatch.setattr('sys.argv', ['availability', '--labels', str(label_file), '--output', str(output),
                        '--start-us', str(START2022), '--end-us', str(START2022 + 4 * DAY),
                        '--asof-us', str(START2022 + 4 * DAY), '--checkpoint-schedule', str(schedule_file)])
    main()
    result = json.loads(capsys.readouterr().out)
    assert result['scheduled_identity']['rank_checkpoint_schedule_sha256'] == checkpoints.sha256
    assert AvailableRewardModel.load(output).metadata['available_label_counts'] == [4] * 5 + [0]


def test_actual_student_runner_crosses_checkpoint_schedule_and_paid_terminal(tmp_path):
    sim = simulator()
    checkpoints = schedule(START2022, sim.start + DAY)
    rows = labels(START2022, [[True] * 6] * 4, checkpoints)
    def scheduled_context(stamp):
        c = context(stamp)
        return replace(c, action_available=np.ones(6, dtype=bool), checkpoint_schedule=checkpoints,
                       binding=dict(c.binding, rank_checkpoint_sha256=checkpoints.at(stamp),
                                    rank_checkpoint_schedule_sha256=checkpoints.sha256))
    names, _ = causal_features(sim, scheduled_context(sim.start))
    for row in rows:
        row['feature_names'] = names
        row['features'] = [0.] * len(names)  # Synthetic constant training inputs.
    model = fitted(rows, checkpoints)
    experiment = NativeExperiment(sim, scheduled_context, linear_ramp_risk_mapper,
                                  binding=scheduled_context(sim.start).binding)
    directory = tmp_path / 'run'
    result = run(experiment, directory, 'student', model=model)
    records = [json.loads(line) for line in (directory / 'predictions.jsonl').read_text().splitlines()]
    assert records[0]['binding']['rank_checkpoint_sha256'] == '1' * 64
    assert records[1]['binding']['rank_checkpoint_sha256'] == '4' * 64
    assert all(r['e6_available'] == [True] * 6 for r in records)
    assert result.account.fees > 0 and all(p.quantity == 0 for p in result.account.positions.values())
    assert json.loads((directory / 'RUN.json').read_text())['status'] == 'COMPLETE'
