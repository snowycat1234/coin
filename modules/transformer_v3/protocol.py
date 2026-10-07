"""Freeze the user-specified small policy experiment only after v2 replay analysis."""
import argparse,json,time
from pathlib import Path
from modules.transformer_v2.train import atomic,sha
from .train_policy import FAMILIES,SEEDS
from .funding_bridge import SCENARIOS

def freeze(state,repo):
    state=Path(state);repo=Path(repo);replay=state/'V2_BYBIT_LIQUIDATION_REPLAY.json';analysis=state/'V2_REPLAY_ANALYSIS.json'
    r=json.loads(replay.read_text());a=json.loads(analysis.read_text())
    if r['status']!='COMPLETE' or r['errors'] or len(r['cases'])!=864 or a['replay_results_sha256']!=sha(replay):raise ValueError('Full replay and neutral analysis must precede protocol freeze')
    teacher=json.loads((state/'TEACHER_AUDIT_PRELIMINARY.json').read_text())
    if teacher['status']!='PASS_TRAINING_TEACHER_CHRONOLOGY_AUDIT' or teacher['new_fits']!=0:raise ValueError('Training teacher audit must precede fits')
    ordering=json.loads((state/'EVENT_ORDERING_REPAIR_RECEIPT.json').read_text())
    if ordering['status']!='PASS_EVENT_ORDERING_AND_DEFAULT_GOLDEN' or any(sha(repo/n)!=v for n,v in ordering['sources'].items()):raise ValueError('Validated and committed event ordering must precede protocol freeze')
    old=json.loads((repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json').read_text())
    result=dict(experiment='TRANSFORMER_V3_ORACLE_POLICY_20261007',status='FROZEN_AFTER_V2_REPLAY_NEUTRAL_ANALYSIS_BEFORE_POLICY_FITS',
        v2_base_HEAD='0350589199d4566ac519b0e581ff86eb065ba934',replay_results_sha256=sha(replay),replay_analysis_sha256=sha(analysis),
        protected_v2_receipt_sha256=sha(state/'PHASE0_V2_PRESERVATION.json'),funding_bridges_sha256=sha(state/'LOCKED_BRIDGE_PREREGISTRATION.json'),
        teacher_audit_sha256=sha(state/'TEACHER_AUDIT_PRELIMINARY.json'),data_manifest_sha256=old['data_manifest_sha256'],
        independent_event_ordering_receipt_sha256=sha(state/'EVENT_ORDERING_REPAIR_RECEIPT.json'),
        models=list(FAMILIES),frozen_patch_control='PATCH_CROSS_ASSET_MULTITASK',seeds=list(SEEDS),
        architecture=dict(width=128,heads=4,temporal_layers=3,cross_asset_layers=1,lookback=256,patches=[1,8],
                          new_parameters_over_matching_v2=516,pooling='FIXED_CLS_ATTENTION_LAST_MEAN',no_size_search=True),
        teachers=dict(direction='FULL30DAY_PRICE_DIRECTION',relative='FULL7_30_60DAY_CROSS_SECTIONAL_RETURNS_PRIMARY30',
                      expert='FULL60DAY_SMA_HOLD_CASH_EXISTING_COST_AWARE_CONTINUOUS_DAILY_PROXY',
                      no_gap_bridging=True,purge_full_label_end=True,embargo_days=60,no_locked_gradient=True,no_teacher_inference_input=True,
                      expert_minute_wallet_equivalent=False),
        objective=dict(primary='ACTION_POLICY_GAP_WEIGHTED_CROSS_ENTROPY',gap_scale='TRAIN_VALID_POSITIVE_GAP_MEDIAN',gap_weight_clip=[0.,5.],
                       expected_action_regret_clip=[0.,5.],coefficients=dict(policy_CE=1.,expected_regret=.1,utility_aux=.1,pairwise_rank=.2,direction30_BCE=.1,regime_aux=.1)),
        training=dict(optimizer='AdamW',learning_rate=.0007,weight_decay=.001,batch_size=16,maximum_inner_epochs=40,inner_patience=7,
                      gradient_norm=1.,outer_refit_epochs='PAST_INNER_BEST_EPOCH',final_epochs='FIXED_MEDIAN_OF_FIVE_PAST_INNER_EPOCHS',
                      final_training_cutoff='2026-03-01_MINUS60D_WITH_FULL60D_LABEL_MATURITY',development_fits=60,final_fits=12),
        inference=dict(primary_directional='DIRECT_POLICY_SOFTMAX_SMA_HOLD_CASH',temperature=1.,temperature_search=False,
                       readout_rule='MEAN_PROBABILITIES_FOR_POLICY_MEAN_SCORES_FOR_RELATIVE',seed_rule='THREE_FIXED_PREDICTION_ENSEMBLE_NO_WINNER_SEED',
                       numerical_probability_renormalization='FLOAT64_SUM_TO_ONE_ONLY',relative_primary_horizon=30,mappings=['DIRECTIONAL','NEUTRAL','COMBINED'],
                       combined='.5_DIRECTIONAL_PLUS_.5_NEUTRAL_IN_ONE_NETTED_WALLET'),
        risk_profiles=dict(FULL=dict(gross=.6,K=2),HALF=dict(gross=.3,K=2)),capital_USDT=10000,asset_cap=.3,leverage=1,
        financial_source_binding={str(p.relative_to(repo)):sha(p) for p in sorted((repo/'src/quant').glob('*.py'))+sorted((repo/'scripts/investment').glob('*.py'))+[repo/'modules/transformer_v3/isolated_audit.py']},
        native_semantics='PER_POSITION_MARK_TRIGGER_BANKRUPTCY_TAKEOVER; NO_INSURANCE_SURPLUS_REFUND; OTHER_POSITIONS_AND_WALLET_CONTINUE; NORMAL_REBALANCE_REENTRY',
        native_risk_snapshot_status='UNAVAILABLE10_HTTP403',risk_assumption='LEGACY_MMR0.005_MMD0; UNKNOWN_NATIVE_TIER_LIMITS',
        native_or_historical_risk_certified=False,observations='CAUSALLY_AVAILABLE_MINUTE_MARK; NOT_INTRAMINUTE_NATIVE_CERTIFICATION',
        wallets=dict(replayed_full_v2=864,frozen_half_controls=348,policy_development=576,locked_bridge_ensemble_comparisons=400,
                     incomplete_cases='RETAIN_EXPLICIT_N_E_FULL_DENOMINATOR_NO_PARTIAL_RETURN_IMPUTATION',independent_capital='NO_RESET_WALLET_RETURN_ADDITION'),
        development_selection=dict(models=['PATCH_CROSS_ASSET_MULTITASK',*FAMILIES],profile_order=['FULL','HALF'],mapping_order=['DIRECTIONAL','NEUTRAL','COMBINED'],
            rank='WORST_TWO_FUNDING_MEDIAN_NET_THEN_WORST_PAIRED_STRONGEST_STATIC_DELTA; STABLE_REGISTERED_ORDER_FOR_TIES',
            gate='REUSE_V2_SIX_WINDOW_COMPLETENESS_4POSITIVE_MEDIANPOSITIVE_POSITIVE_GAIN_CONCENTRATION_LE0.5_AND_THREE_SEED_ENSEMBLE_STABILITY'),
        neutral_replay_gate=a['stable_neutral_gate_pass'],neutral_replay_priority='FULL_REPLAY_AND_NEUTRAL_ANALYSIS_BEFORE_ANY_FIT; IF_OLD_NEUTRAL_GATE_PASSES_HALF_CONTROLS_FIRST; OTHERWISE_GPU_FITS_PARALLEL_CPU_HALF_CONTROLS; NO_EXTRA_ARCHITECTURES',
        execution_capacity='GPU_FIT_CONCURRENCY_FROM_ACTUAL_GPU_MEMORY_AND_CPU_AFFINITY; NO_CPU_RAM_TIME_QUOTAS; BATCH_AND_MODEL_BUDGET_UNCHANGED',
        locked=dict(range=['2026-03-01','2026-08-31'],days=184,bridges=list(SCENARIOS),classification='IMPUTED_LOCKED_SENSITIVITY',
                    original_formal_v2='PERMANENT_NOT_EVALUABLE_UNCHANGED',headline='ALL_FIVE_MIN_MEDIAN_MAX_AND_ECONOMIC_DECISION_CONSISTENCY',
                    predictions='RECOMPUTE_CAUSAL_INPUTS_SEPARATELY_PER_BRIDGE_WITH_IDENTICAL_FROZEN_WEIGHTS; NO_SOURCE_POOL_REUSE',
                    no_post_locked_tuning=True),
        final_decision=dict(
            paper='DEVELOPMENT_GATE_PASS_AND_EACH_BRIDGE_COMPLETE_IN_BOTH_FUNDING_INTERPRETATIONS_AND_NET_POSITIVE_AND_ABOVE_STRONGEST_STATIC_AND_NATIVE_RISK_CERTIFIED',
            continue_research='IF_NOT_PAPER: REGISTERED_DEV_NEUTRAL_GATE_OR_ENSEMBLE_POSITIVE_RANK_IC_IN_AT_LEAST4_OF5_FOLDS_IN_BOTH_UNITS_OR_POLICY_SOFT_PROXY_REGRET_REDUCTION_IN_AT_LEAST3_OF5_MATCHED_FOLDS_IN_BOTH_UNITS',
            stop='OTHERWISE_STOP_THIS_TRANSFORMER_PUBLIC_DATA_DIRECTION',
            bridge_economic_vote='SAME_CHOSEN_MODEL_MAPPING_PROFILE_IN_BOTH_UNITS; COMPLETE_POSITIVE_NET_AND_PAIRED_STRONGEST_STATIC_DELTA_POSITIVE; OTHERWISE_FAIL_OR_N_E',
            qualifications='DESCRIPTIVE_FINITE_EXPERIMENT; NO_P_VALUE_OR_APR_CERTIFICATION; NO_POST_LOCKED_THRESHOLD_CHANGE'),
        no_optuna=True,investment_state='NONE/CASH',frozen_at=time.time())
    path=repo/'reports/transformer_v3/TRANSFORMER_V3_PROTOCOL.json'
    if path.exists():raise ValueError('Protocol already frozen; do not overwrite')
    atomic(path,result);atomic(state/'TRANSFORMER_V3_PROTOCOL_RECEIPT.json',dict(path=str(path),sha256=sha(path),replay_analysis_sha256=sha(analysis),new_fits=0))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args()
    result=freeze(a.state,Path(__file__).resolve().parents[2]);print(result['status'],flush=True)

if __name__=='__main__':main()
