"""Opt-in masked native reward fit; no acquisition, expert fitting or wallet run.

Dates and one frozen RANK checkpoint schedule are supplied by the caller.
Each output uses only its genuinely available mature rewards. Unobserved heads
remain NaN and cannot be selected when they first become available.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.investment.perpetual_directional import DAY, need
from .availability_contract import (CheckpointSchedule, candidate_mask, digest,
                                    label_mask, masked_rewards, scheduled_identity)
from .teacher import E6, SCHEMA, causal_features
from .train import NativeRewardModel, RIDGE_ALPHA

MODEL_SCHEMA = 'NATIVE_AVAILABLE_REWARD_RIDGE_V1'


@dataclass
class AvailableRewardModel(NativeRewardModel):
    def predict(self, features, feature_names, binding, *, decision_us, available):
        mask = candidate_mask(available)
        need(scheduled_identity(binding) == self.metadata['scheduled_identity'],
             'Same fixed experts, mapper and checkpoint schedule required')
        schedule = CheckpointSchedule(self.metadata['checkpoint_schedule'])
        schedule.validate_binding(binding, decision_us, mask)
        need(tuple(feature_names) == self.feature_names, 'Exact causal input schema')
        x = np.asarray(features, dtype=float)
        need(x.shape == self.mean.shape and np.isfinite(x).all(), 'Finite current-state inputs')
        supported = np.asarray(self.metadata['available_label_counts']) > 0
        need(np.all(supported[mask]), 'Available action has no mature training labels; refit required')
        prediction = np.full(6, np.nan)
        prediction[mask] = np.r_[1., (x - self.mean) / self.scale] @ self.coefficients[:, mask]
        need(np.isfinite(prediction[mask]).all(), 'Finite predictions on available candidates')
        return prediction

    def request(self, sim, context):
        need(sim.cursor >= self.metadata['asof_us'], 'Student artifact must be available before self-run use')
        names, features = causal_features(sim, context)
        mask = context.action_mask()
        prediction = self.predict(features, names, context.binding,
                                  decision_us=context.decision_us, available=mask)
        winner = np.flatnonzero(mask)[np.argmax(prediction[mask])]
        return np.eye(6)[winner], prediction

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data['metadata_json']))
            need(meta['schema'] == MODEL_SCHEMA and meta['action_order'] == list(E6),
                 'Availability model schema')
            model = cls(data['mean'].copy(), data['scale'].copy(), data['coefficients'].copy(),
                        tuple(data['feature_names'].tolist()), meta)
        supported = np.asarray(meta['available_label_counts']) > 0
        need(model.mean.shape == model.scale.shape == (len(model.feature_names),)
             and np.isfinite(model.mean).all() and np.isfinite(model.scale).all()
             and np.all(model.scale > 0) and model.coefficients.shape == (len(model.mean) + 1, 6)
             and np.isfinite(model.coefficients[:, supported]).all()
             and np.isnan(model.coefficients[:, ~supported]).all(), 'Valid masked reward model arrays')
        CheckpointSchedule(meta['checkpoint_schedule'])
        return model


def fit_available(rows, *, start_us, end_us, asof_us, checkpoint_schedule):
    """Fit one fixed ridge recipe on a declared interval, end exclusive."""
    need(type(start_us) is int and type(end_us) is int and type(asof_us) is int
         and start_us % DAY == end_us % DAY == 0 and start_us < end_us <= asof_us,
         'Explicit daily training interval and mature as-of clock')
    need(isinstance(checkpoint_schedule, CheckpointSchedule), 'Frozen checkpoint schedule required')
    admitted, masks, rewards = [], [], []
    for row in rows:
        need(row.get('schema') == SCHEMA, 'Independent native-action teacher schema required')
        d = int(row['decision_us'])
        if not start_us <= d < end_us or row.get('forced_terminal_day', False):
            continue
        need(d % DAY == 0 and row['feature_available_us'] <= d
             and row['interval_end_us'] == d + DAY
             and row['label_available_us'] >= row['interval_end_us'],
             'Causal feature clocks and next-day label maturity required')
        if row['label_available_us'] > asof_us:
            continue
        need(row['action_order'] == list(E6)
             and row['state_role'] in ('TEACHER_SELF', 'ACTUAL_SELECTOR_STATE', 'STUDENT_TRAIN_RELABEL')
             and not row.get('global_native_upper_bound', True), 'Declared native one-step label scope')
        mask = label_mask(row)
        checkpoint_schedule.validate_binding(row['binding'], d, mask)
        admitted.append(row)
        masks.append(mask)
        rewards.append(masked_rewards(row, mask))
    need(len(admitted) >= 2, 'At least two mature native state labels required')
    keys = [(r['state_role'], r['decision_us'], r['state_hash']) for r in admitted]
    need(len(keys) == len(set(keys)), 'Duplicate native state labels rejected')
    names = tuple(admitted[0]['feature_names'])
    need(len(names) > 0 and len(set(names)) == len(names)
         and all(name.startswith(('market.', 'expert.', 'wallet.', 'budget.'))
                 and not any(word in name.lower() for word in
                             ('winner', 'reward', 'regret', 'label', 'future', 'utility')) for name in names),
         'Only unique causal native features are trainable')
    identity = scheduled_identity(admitted[0]['binding'])
    need(identity['expert_order'] == list(E6), 'Fixed E6 expert order')
    digest(identity['mapper_sha256'], 'mapper_sha256')
    symbols = admitted[0]['symbol_order']
    need(all(tuple(r['feature_names']) == names and r['symbol_order'] == symbols
             and scheduled_identity(r['binding']) == identity for r in admitted),
         'Fixed feature, symbol, non-RANK expert and mapper identity')
    X = np.asarray([r['features'] for r in admitted], dtype=float)
    mask, y = np.asarray(masks), np.asarray(rewards)
    need(X.shape == (len(admitted), len(names)) and np.isfinite(X).all(), 'Finite native feature matrix')
    gaps = []
    for values, present in zip(y, mask, strict=True):
        ordered = np.sort(values[present])
        gaps.append(ordered[-1] - ordered[-2] if len(ordered) > 1 else 0.)
    gap = np.asarray(gaps)
    need(np.isfinite(gap).all(), 'Finite available-action utility gaps')
    gap_scale = float(np.median(gap[gap > 0])) if (gap > 0).any() else 1.
    weights = 1 + np.minimum(gap / gap_scale, 5.)
    mean = np.average(X, axis=0, weights=weights)
    scale = np.sqrt(np.average((X - mean) ** 2, axis=0, weights=weights))
    scale[scale < 1e-12] = 1.
    z = np.column_stack((np.ones(len(X)), (X - mean) / scale))
    penalty = np.diag(np.r_[0., np.full(len(names), RIDGE_ALPHA)])
    coefficients = np.full((len(names) + 1, 6), np.nan)
    if mask.all():
        # Preserve the exact old joint solve for the all-E6 case.
        weighted = z * np.sqrt(weights[:, None])
        coefficients = np.linalg.solve(weighted.T @ weighted + penalty,
                                       weighted.T @ (y * np.sqrt(weights[:, None])))
    else:
        for k in range(6):
            present = mask[:, k]
            if not present.any():
                continue
            weighted = z[present] * np.sqrt(weights[present, None])
            coefficients[:, k] = np.linalg.solve(weighted.T @ weighted + penalty,
                weighted.T @ (y[present, k] * np.sqrt(weights[present])))
    prediction = z @ coefficients
    need(np.isfinite(prediction[mask]).all(), 'Finite fitted predictions for all available labels')
    mse = float(np.average((prediction[mask] - y[mask]) ** 2,
                           weights=np.broadcast_to(weights[:, None], mask.shape)[mask]))
    metadata = dict(schema=MODEL_SCHEMA, action_order=list(E6), symbol_order=symbols,
                    scheduled_identity=identity, checkpoint_schedule=checkpoint_schedule.entries,
                    train_start_us=start_us, train_end_us=end_us, asof_us=asof_us,
                    admitted_rows=len(admitted), available_label_counts=mask.sum(axis=0).tolist(),
                    latest_label_available_us=max(r['label_available_us'] for r in admitted),
                    ridge_alpha=RIDGE_ALPHA, gap_scale_USDT=gap_scale,
                    loss='GAP_WEIGHTED_SQUARED_ERROR_ON_AVAILABLE_CANDIDATES_ONLY',
                    masked_training_MSE_USDT2=mse, unavailable_reward='NULL_OR_NAN_NEVER_ZERO',
                    unsupported_head='NAN_AND_FAIL_CLOSED_ON_INFERENCE',
                    distribution_shift='Label states can differ from student self-state.',
                    training_states_sha256=hashlib.sha256(json.dumps(keys, separators=(',', ':')).encode()).hexdigest(),
                    hyperparameter_search=False)
    return AvailableRewardModel(mean, scale, coefficients, names, metadata)


def label_metrics_available(model, rows):
    hits, regrets = [], []
    for row in rows:
        if row.get('forced_terminal_day', False):
            continue
        need(row['schema'] == SCHEMA, 'Native teacher schema')
        need(row['feature_available_us'] <= row['decision_us']
             and row['interval_end_us'] == row['decision_us'] + DAY
             and row['label_available_us'] >= row['interval_end_us'],
             'Causal clocks required for available-label diagnostics')
        mask = label_mask(row)
        y = masked_rewards(row, mask)
        prediction = model.predict(row['features'], row['feature_names'], row['binding'],
                                   decision_us=row['decision_us'], available=mask)
        winner = np.flatnonzero(mask)[np.argmax(prediction[mask])]
        best = float(np.max(y[mask]))
        hits.append(bool(y[winner] == best))
        regrets.append(best - float(y[winner]))
    return dict(label_state_rows=len(hits), winner_hit_rate=float(np.mean(hits)) if hits else None,
                mean_one_step_regret_USDT=float(np.mean(regrets)) if regrets else None,
                metric_scope='AVAILABLE_LABEL_STATES_ONLY_NOT_REALIZABLE_NAV')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--start-us', type=int, required=True)
    parser.add_argument('--end-us', type=int, required=True)
    parser.add_argument('--asof-us', type=int, required=True)
    parser.add_argument('--checkpoint-schedule', required=True, help='Local JSON array of explicit causal intervals')
    args = parser.parse_args()
    rows, hashes = [], {}
    for path in args.labels:
        data = Path(path).read_bytes()
        hashes[str(Path(path).resolve())] = hashlib.sha256(data).hexdigest()
        rows.extend(json.loads(line) for line in data.splitlines() if line)
    schedule = CheckpointSchedule(json.loads(Path(args.checkpoint_schedule).read_text()))
    model = fit_available(rows, start_us=args.start_us, end_us=args.end_us,
                          asof_us=args.asof_us, checkpoint_schedule=schedule)
    model.metadata['teacher_file_sha256'] = hashes
    model.save(args.output)
    print(json.dumps(model.metadata, allow_nan=False))


if __name__ == '__main__':
    main()
