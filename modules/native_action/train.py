"""One fixed gap-weighted multi-output ridge fit on matured H1 native rewards.

    Predict six next-day native USDT increments, then argmax request -> the same
    ramp/mapper. Student self-state and teacher-state distributions can differ.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC,datetime
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.investment.perpetual_directional import need,DAY
from .teacher import E6,SCHEMA,causal_features
from .student_labels import validate_student_label_clock

MODEL_SCHEMA='NATIVE_E6_REWARD_RIDGE_V1'
TRAIN_START=int(datetime(2024,1,1,tzinfo=UTC).timestamp()*1_000_000)
TRAIN_END=int(datetime(2024,7,1,tzinfo=UTC).timestamp()*1_000_000)
EVAL_START=int(datetime(2024,8,13,tzinfo=UTC).timestamp()*1_000_000)
EVAL_END=int(datetime(2025,1,2,tzinfo=UTC).timestamp()*1_000_000)
RIDGE_ALPHA=10.


def frozen_identity(binding):
    keys=('expert_order','rank_checkpoint_sha256','mapper_sha256','expert_identity_sha256')
    return {k:binding.get(k) for k in keys}


@dataclass
class NativeRewardModel:
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    feature_names: tuple[str,...]
    metadata: dict

    def predict(self,features,feature_names,binding):
        need(tuple(feature_names)==self.feature_names,'Exact causal input schema')
        need(frozen_identity(binding)==self.metadata['frozen_identity'],
             'Same frozen experts, rank checkpoint and ramp/risk mapper required')
        x=np.asarray(features,dtype=np.float64)
        need(x.shape==(len(self.feature_names),) and np.isfinite(x).all(),'Finite current-state inputs')
        z=(x-self.mean)/self.scale
        return np.r_[1.,z]@self.coefficients

    def request(self,sim,context):
        need(context.action_available is None or context.action_mask().all(),
             'Partial candidate inference requires the explicit availability model')
        names,features=causal_features(sim,context)
        reward=self.predict(features,names,context.binding)
        return np.eye(6)[int(np.argmax(reward))],reward

    def save(self,path):
        # Exclusive create; historical models and labels are never overwritten.
        with Path(path).open('xb') as f:
            np.savez_compressed(f,mean=self.mean,scale=self.scale,coefficients=self.coefficients,
                                feature_names=np.asarray(self.feature_names),
                                metadata_json=np.asarray(json.dumps(self.metadata,sort_keys=True)))

    @classmethod
    def load(cls,path):
        with np.load(path,allow_pickle=False) as data:
            meta=json.loads(str(data['metadata_json']))
            need(meta['schema']==MODEL_SCHEMA and meta['action_order']==list(E6),'Native model schema')
            model=cls(data['mean'].copy(),data['scale'].copy(),data['coefficients'].copy(),
                      tuple(data['feature_names'].tolist()),meta)
        need(model.scale.shape==model.mean.shape and np.all(model.scale>0) and
             model.coefficients.shape==(len(model.mean)+1,6) and
             np.isfinite(model.coefficients).all(),'Valid six-reward model arrays')
        return model


def fit(rows,*,asof_us=TRAIN_END):
    """Only matured Jan-Jun2024 rows. Later seen history never tunes this fit."""
    need(asof_us<=TRAIN_END,'This experiment trains only within 2024H1')
    admitted=[]
    for row in rows:
        validate_student_label_clock(row)
        need(row.get('schema')==SCHEMA,'Independent native-action teacher schema required')
        d=int(row['decision_us'])
        if not TRAIN_START<=d<TRAIN_END:continue
        if int(row['label_available_us'])>asof_us:continue
        if row.get('forced_terminal_day',False):continue
        need(row['feature_available_us']<=d and row['interval_end_us']==d+DAY,
             'Daily causal inputs and full next-day labels')
        need(row['label_available_us']>=row['interval_end_us'],'Label cannot mature before next-day events')
        need(row['action_order']==list(E6) and all(row['e6_valid']) and
             row['state_role'] in ('TEACHER_SELF','ACTUAL_SELECTOR_STATE','STUDENT_TRAIN_RELABEL'),
             'Six complete native labels and declared state distribution')
        need(not row.get('global_native_upper_bound',True),'One-step optimal labels only')
        admitted.append(row)
    need(len(admitted)>=2,'At least two matured H1 labels required')
    keys=[(r['state_role'],r['decision_us'],r['state_hash']) for r in admitted]
    need(len(keys)==len(set(keys)),'Duplicate native state labels rejected')
    names=tuple(admitted[0]['feature_names'])
    need(all(name.startswith(('market.','expert.','wallet.','budget.')) and
             not any(word in name.lower() for word in ('winner','reward','regret','label','future','utility'))
             for name in names),'Only the native causal feature whitelist is trainable')
    identity=frozen_identity(admitted[0]['binding'])
    need(identity['expert_order']==list(E6) and identity['rank_checkpoint_sha256'] and
         identity['mapper_sha256'],'Frozen E6 rank and mapper identity required')
    symbol_order=admitted[0]['symbol_order']
    need(all(tuple(r['feature_names'])==names and frozen_identity(r['binding'])==identity and
             r['symbol_order']==symbol_order for r in admitted),'Frozen feature/expert/ranker identity within fit')
    X=np.asarray([r['features'] for r in admitted],dtype=np.float64)
    y=np.asarray([r['e6_rewards_USDT'] for r in admitted],dtype=np.float64)
    need(X.shape==(len(admitted),len(names)) and y.shape==(len(admitted),6) and
         np.isfinite(X).all() and np.isfinite(y).all(),'Native feature and six-reward arrays')
    gap=np.sort(y,axis=1)[:,-1]-np.sort(y,axis=1)[:,-2]
    positive=gap[gap>0]
    gap_scale=float(np.median(positive)) if len(positive) else 1.
    weights=1+np.minimum(gap/gap_scale,5.)
    mean=np.average(X,axis=0,weights=weights)
    scale=np.sqrt(np.average((X-mean)**2,axis=0,weights=weights))
    scale[scale<1e-12]=1.
    z=np.column_stack((np.ones(len(X)),(X-mean)/scale))
    weighted=z*np.sqrt(weights[:,None])
    penalty=np.diag(np.r_[0.,np.full(len(names),RIDGE_ALPHA)])
    coefficients=np.linalg.solve(weighted.T@weighted+penalty,weighted.T@(y*np.sqrt(weights[:,None])))
    metadata=dict(schema=MODEL_SCHEMA,action_order=list(E6),symbol_order=symbol_order,
                  frozen_identity=identity,train_start_us=TRAIN_START,train_end_us=TRAIN_END,
                  asof_us=asof_us,admitted_rows=len(admitted),latest_label_available_us=max(r['label_available_us'] for r in admitted),
                  training_state_roles=sorted(set(r['state_role'] for r in admitted)),
                  fit='GAP_WEIGHTED_MULTI_OUTPUT_RIDGE',ridge_alpha=RIDGE_ALPHA,gap_scale_USDT=gap_scale,
                  objective='SIX_NATIVE_NEXT_DAY_NET_REWARDS_USDT',inference='ARGMAX_REQUEST_THEN_SAME_L1_RAMP_AND_RISK_MAPPER',
                  distribution_shift='Teacher or actual-selector state labels differ from student self-state; train-only relabel hook is available.',
                  evaluation_history_role='PREVIOUSLY_SEEN_TEMPORAL_EVALUATION_NOT_SEALED_OR_UNSEEN_OOS',
                  evaluation_start_us=EVAL_START,evaluation_end_us=EVAL_END,
                  training_states_sha256=hashlib.sha256(json.dumps(keys,separators=(',',':')).encode()).hexdigest(),
                  hyperparameter_search=False)
    return NativeRewardModel(mean,scale,coefficients,names,metadata)


def label_metrics(model,rows):
    """Diagnostic accuracy/regret on label states; does not replace self-run NAV."""
    hits=[]
    regrets=[]
    for row in rows:
        if row.get('forced_terminal_day',False):continue
        need(row['schema']==SCHEMA and all(row['e6_valid']),'Complete native labels')
        pred=model.predict(row['features'],row['feature_names'],row['binding'])
        y=np.asarray(row['e6_rewards_USDT'])
        winner=int(np.argmax(pred))
        hits.append(bool(y[winner]==np.max(y)))
        regrets.append(float(np.max(y)-y[winner]))
    return dict(label_state_rows=len(hits),winner_hit_rate=float(np.mean(hits)) if hits else None,
                mean_one_step_regret_USDT=float(np.mean(regrets)) if regrets else None,
                metric_scope='LABEL_STATES_ONLY_NOT_A_REALIZABLE_EQUITY_CURVE')
