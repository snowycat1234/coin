"""One fixed-student training-state pass, with one-day fork labels only.

The frozen artifact may replay its own training interval retrospectively. This
is offline label collection, not a claim of historical deployability. A policy
sees only a detached causal observation; outcomes never select the main path.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import inspect
import json
from pathlib import Path
import time
from typing import Callable

import numpy as np

from scripts.investment.perpetual_directional import DAY, need
from .availability_contract import digest, label_mask, masked_rewards, scheduled_identity
from .interface import NativeExperiment
from .teacher import DayContext, Proposal, causal_features, identity_digest, replay_candidates

COLLECTION_SCHEMA = 'NATIVE_FIXED_STUDENT_TRAINING_STATE_1D_V1'


@dataclass(frozen=True)
class TrainingWindow:
    training_start_us: int
    training_end_us: int
    evaluation_start_us: int
    label_asof_us: int
    collect_start_us: int
    collect_end_us: int
    sample_decisions_us: tuple[int, ...] | None = None

    def validate(self, sim):
        fields = vars(self)
        need(all(type(v) is int for k, v in fields.items() if k != 'sample_decisions_us'),
             'Integer microsecond collection clocks')
        need(0 <= self.training_start_us <= sim.start < sim.end <= self.training_end_us
             <= self.evaluation_start_us, 'Collection wallet restricted to training; evaluation forbidden')
        need(sim.cursor == sim.start and sim.rows_written == 0 and sim.stop is None,
             'One fresh fixed-student pass from the declared wallet start')
        need(all(t % DAY == 0 for t in (sim.start, sim.end, self.training_start_us,
                                      self.training_end_us, self.collect_start_us, self.collect_end_us)),
             'Complete fixed UTC daily windows')
        need(sim.start <= self.collect_start_us < self.collect_end_us <= sim.end
             and self.collect_end_us <= self.label_asof_us <= self.training_end_us,
             'Collection labels must mature inside training as-of')
        if self.sample_decisions_us is not None:
            dates = self.sample_decisions_us
            need(isinstance(dates, tuple) and len(dates) > 0
                 and all(type(d) is int and d % DAY == 0
                         and self.collect_start_us <= d < self.collect_end_us for d in dates)
                 and len(set(dates)) == len(dates), 'Unique specified training decision dates')

    def samples(self, decision_us):
        return (self.collect_start_us <= decision_us < self.collect_end_us
                and (self.sample_decisions_us is None or decision_us in self.sample_decisions_us))


@dataclass(frozen=True)
class StudentObservation:
    decision_us: int
    state_hash: str
    feature_names: tuple[str, ...]
    features: tuple[float, ...]
    budget: tuple[float, ...]
    context: DayContext
    forced_terminal_day: bool


@dataclass(frozen=True)
class FixedStudent:
    """Generic exact-proposal policy, including mixed requests and custom targets.

    fingerprint must hash the actual fixed model/configuration at call time.
    It is checked around every decision and probe. Model and adapter identities
    are separate; the callback receives no simulator or future market tape.
    """
    feature_names: tuple[str, ...]
    model_sha256: str
    proposal_adapter_sha256: str
    training_label_end_us: int
    artifact_asof_us: int
    propose: Callable[[StudentObservation], Proposal]
    fingerprint: Callable[[], str]
    adapter_fingerprint: Callable[[], str]
    model_artifact_sha256: str | None = None

    def binding(self):
        return dict(model_sha256=self.model_sha256,
                    proposal_adapter_sha256=self.proposal_adapter_sha256,
                    feature_schema_sha256=identity_digest(self.feature_names),
                    training_label_end_us=self.training_label_end_us,
                    artifact_asof_us=self.artifact_asof_us,
                    model_artifact_sha256=self.model_artifact_sha256)

    def validate(self, window):
        for key in ('model_sha256', 'proposal_adapter_sha256'):
            digest(getattr(self, key), key)
        if self.model_artifact_sha256 is not None:
            digest(self.model_artifact_sha256, 'model_artifact_sha256')
        need(type(self.training_label_end_us) is int and type(self.artifact_asof_us) is int
             and 0 <= self.training_label_end_us <= self.artifact_asof_us <= window.training_end_us,
             'Frozen student cannot use evaluation labels or a post-training artifact')
        need(self.fingerprint() == self.model_sha256, 'Fixed student model/configuration changed')
        need(self.adapter_fingerprint() == self.proposal_adapter_sha256,
             'Fixed student proposal adapter/configuration changed')


def reward_model_fingerprint(model):
    h = hashlib.sha256()
    h.update(type(model).__name__.encode())
    h.update(identity_digest(dict(feature_names=model.feature_names, metadata=model.metadata)).encode())
    for value in (model.mean, model.scale, model.coefficients):
        a = np.ascontiguousarray(value)
        h.update(str((a.dtype.str, a.shape)).encode())
        h.update(a.tobytes())
    return h.hexdigest()


def callable_fingerprint(function):
    """Source plus JSON configuration for ordinary function-based mappers.

    Opaque/stateful mappers should use the generic FixedStudent interface and
    provide their own explicit complete adapter/configuration fingerprint.
    """
    closure = inspect.getclosurevars(function)
    config = dict(closure.nonlocals)
    for key, value in closure.globals.items():
        if not inspect.ismodule(value) and not callable(value):
            config['global.' + key] = value
    return identity_digest(dict(source=inspect.getsource(function), config=config,
                                module=function.__module__, name=function.__qualname__))


def student_from_reward_model(model, mapper, *, artifact_sha256=None):
    """Reuse existing frozen ridge/availability predict and the bound exact mapper.

    Deliberately use predict, not the deployment request's as-of guard: the
    collector declares retrospective training replay and never evaluates here.
    """
    from .availability import AvailableRewardModel

    def propose(observation):
        c = observation.context
        if isinstance(model, AvailableRewardModel):
            rewards = model.predict(observation.features, observation.feature_names, c.binding,
                                    decision_us=c.decision_us, available=c.action_mask())
        else:
            need(c.action_available is None or c.action_mask().all(),
                 'Partial candidate inference requires the explicit availability model')
            rewards = model.predict(observation.features, observation.feature_names, c.binding)
        mask = c.action_mask()
        need(np.isfinite(rewards[mask]).all(), 'Finite available student predictions')
        winner = np.flatnonzero(mask)[np.argmax(rewards[mask])]
        if observation.forced_terminal_day:
            need(mask[0], 'Original forced final-day student request requires CASH')
            winner = 0
        return mapper(np.asarray(observation.budget), np.eye(6)[winner], c)

    def adapter_fingerprint():
        return identity_digest(dict(proposal_source=inspect.getsource(propose),
                                    mapper_sha256=callable_fingerprint(mapper)))

    return FixedStudent(tuple(model.feature_names), reward_model_fingerprint(model), adapter_fingerprint(),
                        model.metadata['latest_label_available_us'], model.metadata['asof_us'],
                        propose, lambda: reward_model_fingerprint(model), adapter_fingerprint, artifact_sha256)


def validate_student_label_clock(row):
    """Fail closed at fit admission too; never silently filter tainted new rows."""
    contract = row.get('student_collection')
    if contract is None:
        return  # Existing teacher/legacy label schemas retain their contract.
    need(contract['schema'] == COLLECTION_SCHEMA and row['state_role'] == 'STUDENT_TRAIN_RELABEL'
         and contract['data_role'] == 'TRAINING_ONLY', 'Student collection training role required')
    d, end, mature = row['decision_us'], row['interval_end_us'], row['label_available_us']
    clocks = [d, end, mature, row['feature_available_us']]
    clocks += [contract[k] for k in ('training_start_us', 'training_end_us', 'evaluation_start_us',
                                    'label_asof_us', 'collect_start_us', 'collect_end_us')]
    need(all(type(t) is int for t in clocks), 'Integer student sample clocks')
    need(contract['training_start_us'] <= contract['collect_start_us'] <= d
         < contract['collect_end_us'] <= contract['training_end_us'] <= contract['evaluation_start_us']
         and d % DAY == 0 and row['feature_available_us'] <= d and end == d + DAY
         and end <= mature <= contract['label_asof_us'] <= contract['training_end_us'],
         'Student label maturity/interval cannot cross training or evaluation boundary')
    need(all(contract[k] % DAY == 0 for k in ('training_start_us', 'training_end_us',
                                             'collect_start_us', 'collect_end_us', 'global_terminal_us'))
         and end <= contract['global_terminal_us'] <= contract['training_end_us']
         and contract['collect_end_us'] <= contract['global_terminal_us']
         and row['forced_terminal_day'] == bool(contract['final_day_target_zero']
                                               and end == contract['global_terminal_us']),
         'Fixed daily collection/global terminal clock and forced-day identity')
    dates = contract.get('sample_decisions_us')
    need(dates is None or d in dates, 'Unrequested training date cannot enter student labels')
    student = contract['student_binding']
    need(0 <= student['training_label_end_us'] <= student['artifact_asof_us'] <= contract['training_end_us'],
         'Student artifact used evaluation labels')
    need(student['feature_schema_sha256'] == identity_digest(row['feature_names']),
         'Fixed student feature schema binding')
    for key in ('model_sha256', 'proposal_adapter_sha256'):
        digest(student[key], key)
    digest(contract['source_binding_sha256'], 'source_binding_sha256')
    need(identity_digest(contract['source_binding']) == contract['source_binding_sha256'],
         'Exact source/input binding must accompany student labels')
    digest(contract['feature_builder_sha256'], 'feature_builder_sha256')
    mask = label_mask(row)
    masked_rewards(row, mask)


def detached_observation(sim, context, names, features):
    c = deepcopy(context)
    for value in (c.expert_targets, c.expert_available_us, c.past_returns30,
                  c.expert_eligible, c.action_available):
        if isinstance(value, np.ndarray):
            value.flags.writeable = False
    return StudentObservation(sim.cursor, sim.state_hash(), tuple(names), tuple(features),
                              tuple(sim.budget), c,
                              bool(sim.final_day_target_zero and sim.cursor + DAY >= sim.end))


def collect_pass(experiment: NativeExperiment, student: FixedStudent, window: TrainingWindow, *,
                 limit_seconds=900, save_label=lambda row: None, save_decision=lambda row: None):
    """Advance one continuous main wallet, sampling only declared training dates.

    Returns the wallet and small manifest. Writers receive labels only after
    maturity checks and main-path equivalence; no fitting/DAgger loop is called.
    """
    sim = experiment.simulator
    window.validate(sim)
    student.validate(window)
    need(0 < limit_seconds <= 900 and experiment.binding is not None,
         'Bounded pass with explicit complete source/input binding')
    source_sha = identity_digest(experiment.binding)
    feature_builder_sha = hashlib.sha256(inspect.getsource(causal_features).encode()).hexdigest()
    contract = dict(vars(window), schema=COLLECTION_SCHEMA, data_role='TRAINING_ONLY',
                    student_binding=student.binding(), source_binding_sha256=source_sha,
                    source_binding=deepcopy(experiment.binding), feature_builder_sha256=feature_builder_sha,
                    policy_use='OFFLINE_RETROSPECTIVE_FIXED_TRAINING_ARTIFACT',
                    label_horizon_days=1, refit_count=0, cost_profile=deepcopy(sim.cost),
                    funding_unit=deepcopy(sim.unit), native_simulator_version=sim.VERSION,
                    symbol_order=list(sim.symbols),
                    main_initial_state_hash=sim.state_hash(),
                    global_terminal_us=sim.end, final_day_target_zero=sim.final_day_target_zero,
                    terminal_rule='UNCHANGED_NATIVE_CHARGED_GLOBAL_END_MINUS_6_MINUTES')
    started = time.monotonic()
    identity = None
    sampled = days = replays = 0
    while sim.cursor < sim.end and sim.stop is None:
        need(time.monotonic() - started < limit_seconds, 'Fixed student pass budget exhausted')
        student.validate(window)
        need(identity_digest(experiment.binding) == source_sha, 'Fixed source binding changed')
        need(hashlib.sha256(inspect.getsource(causal_features).encode()).hexdigest() == feature_builder_sha,
             'Fixed causal feature builder changed')
        context = experiment.context_at(sim.cursor)
        names, features = causal_features(sim, context)
        need(tuple(names) == student.feature_names, 'Fixed student feature schema changed')
        current = (scheduled_identity(context.binding) if context.action_available is not None else
                   {k: v for k, v in context.binding.items() if k != 'market_binding_sha256'})
        if identity is None:
            identity = deepcopy(current)
        need(current == identity, 'Fixed experts/mapper/checkpoint schedule changed')
        observation = detached_observation(sim, context, names, features)
        # This happens before any branch sees future outcomes. Never recompute.
        proposal = student.propose(observation)
        need(isinstance(proposal, Proposal), 'Student must return its exact executable Proposal')
        proposal.validate(sim.budget, len(sim.symbols))
        mask = context.action_mask()
        need(np.all(np.asarray(proposal.request)[~mask] == 0)
             and np.all(np.asarray(proposal.budget)[~mask] == 0), 'Student uses unavailable action')
        need(sim.state_hash() == observation.state_hash, 'Student decision mutated main wallet')
        student.validate(window)
        exact_proposal = deepcopy(vars(proposal))
        proposal = replace(proposal, name='FIXED_STUDENT_EXACT')
        label = actual = None
        if window.samples(sim.cursor):
            label, _, actual = replay_candidates(
                sim, context, experiment.mapper, baseline=proposal, state_role='STUDENT_TRAIN_RELABEL',
                time_limit_seconds=limit_seconds - (time.monotonic() - started))
            label['student_collection'] = deepcopy(contract)
            label['student_proposal'] = exact_proposal
            label['e6_available'] = mask.tolist()
            validate_student_label_clock(label)
            replays += int(mask.sum()) + 1
        student.validate(window)
        before, decision = float(sim.account.nav()), sim.cursor
        sim.budget = list(proposal.budget)
        result = sim.advance_day(dict(zip(sim.symbols, proposal.targets, strict=True)))
        need(result['completed'] and sim.cursor == decision + DAY, 'Incomplete student day; stop collection')
        after_hash = sim.state_hash()
        if label is not None:
            need(after_hash == actual.state_hash(), 'Main wallet differs from exact student branch')
            need(abs(float(sim.account.nav()) - before - label['candidates'][6]['net_increment_USDT']) < 1e-9,
                 'Main student reward differs from its fair comparison branch')
            label['main_state_after_hash'] = after_hash
            save_label(label)
            sampled += 1
        save_decision(dict(decision_us=decision, state_hash=observation.state_hash,
                           state_after_hash=after_hash, proposal=exact_proposal,
                           applied_targets=[sim.weights[decision][s] for s in sim.symbols],
                           net_increment_USDT=float(sim.account.nav()) - before,
                           sampled=label is not None, forced_terminal_day=observation.forced_terminal_day))
        days += 1
        need(time.monotonic() - started <= limit_seconds, 'Fixed student pass budget exhausted after day')
    need(sim.cursor == sim.end and sim.stop is None
         and all(p.quantity == 0 for p in sim.account.positions.values()),
         'Full student calendar and charged global terminal cash close required')
    return sim, dict(contract, status='COMPLETE', completed_days=days, sampled_days=sampled,
                     candidate_day_replays=replays, main_day_replays=days,
                     elapsed_seconds=time.monotonic() - started, main_state_after_hash=sim.state_hash(),
                     local_regret_must_not_be_summed_as_NAV=True, model_improvement='NOT_TESTED')


def main():
    from .availability import AvailableRewardModel
    from .runner import exclusive_json, load_experiment, write_row
    from .train import NativeRewardModel

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--options', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--availability-aware', action='store_true')
    parser.add_argument('--window', required=True, help='Local TrainingWindow JSON, UTC microseconds')
    parser.add_argument('--output', required=True)
    parser.add_argument('--limit-seconds', type=float, default=900)
    args = parser.parse_args()
    experiment = load_experiment(args.adapter, json.loads(Path(args.options).read_text()))
    config = json.loads(Path(args.window).read_text())
    if config.get('sample_decisions_us') is not None:
        config['sample_decisions_us'] = tuple(config['sample_decisions_us'])
    window = TrainingWindow(**config)
    model_type = AvailableRewardModel if args.availability_aware else NativeRewardModel
    model = model_type.load(args.model)
    student = student_from_reward_model(model, experiment.mapper,
                                       artifact_sha256=hashlib.sha256(Path(args.model).read_bytes()).hexdigest())
    window.validate(experiment.simulator)
    student.validate(window)
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / 'student_train_labels.jsonl').open('x') as labels:
        with (directory / 'student_decisions.jsonl').open('x') as decisions:
            def record_decision(row):
                write_row(decisions, row)
                sim = experiment.simulator
                print(json.dumps(dict(stage='student_state_collect',
                    completed_days=(sim.cursor - sim.start) // DAY,
                    total_days=(sim.end - sim.start) // DAY, sampled=row['sampled'],
                    NAV=float(sim.account.nav()))), flush=True)

            try:
                sim, manifest = collect_pass(experiment, student, window, limit_seconds=args.limit_seconds,
                    save_label=lambda row: write_row(labels, row),
                    save_decision=record_decision)
            except BaseException as exc:
                exclusive_json(directory / 'FAILED.json', dict(status='FAILED_PREFIX_RETAINED',
                               type=type(exc).__name__, message=str(exc)))
                raise
    exclusive_json(directory / 'RUN.json', manifest)
    exclusive_json(directory / 'summary.json', sim.result()['summary'])
    print(json.dumps(manifest, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
