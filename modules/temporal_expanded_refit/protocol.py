"""Exact authorized expansion recipe; prior study sources remain unchanged."""

from pathlib import Path

from modules.temporal_history_expansion.readiness import proposed_protocol
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

ROOT = Path(__file__).resolve().parents[2]
ARM = "EXPANDED1137_FIXED907_FRESH256"
SOURCE_COMMIT = "1009a6cf6d7c79e3cd914861dc2aeafc3d23709e"
CONSUMER_SHA = "3ba1e64d7c91150a73c28642bed46d1dd2325fcf8fa8aade9425164f526d66ba"
ECONOMICS_SHA = "107dc3f16c8dff2e34716ed3e33dda2340f5e1b5b62ee7ee15ee7f72a9b685ae"
SCALER = "5c0085131d590e64316de3cc558e906f418bff50bc5d934339609da2c4b045ad"


def protocol():
    p = dict(
        schema="ONE_EXPANDED1137_FIXED907_FRESH256_V1",
        arm=ARM,
        planned_fits=1,
        source_commit=SOURCE_COMMIT,
        consumer_SHA256=CONSUMER_SHA,
        economic_SHA256=ECONOMICS_SHA,
        adapter_commit="556fc9d157747a76f28a15d03dd953e6ca44529a",
        parameters=13699,
        architecture="same_GRU64_hidden32_160to32_plus18expertinputs",
        fresh_initialization=True,
        seed=20261009,
        dropout=0.1,
        input="24causal_features24validity_masks64realsteps;separate_time_masks18current_expert_inputs",
        normalization="original773_fit907row_scaler_UNCHANGED;isolates_added_economic_history",
        scaler_identity=SCALER,
        scaler_rows=907,
        scaler_refits=0,
        active_training_intervals=1137,
        training_decisions=1143,
        wallet_lengths=[365, 54, 88, 62, 144, 430],
        original_five_wallets_unchanged=True,
        chronology="earlier2021_separate_fresh_cash_wallet;original_five_gaps_boundaries_retained",
        initial_capital_each=10000.0,
        gross_cap=0.6,
        asset_cap=0.3,
        daily_L1_ramp=0.1,
        objective="unchanged_v2_date_weighted_complete_own_wallet;decision_weights_include_paid_close",
        mixing=0.0,
        lr=0.0003,
        updates=256,
        feature_batch_size=32,
        checkpoint_every=1,
        optimizer="Adam;betas.9/.999;eps1e-8;weight_decay0;foreachFalse;clip1",
        terminal="new2021_realN_Nminus1_ABI;original5_ABI_unchanged;paid_allclosures",
        risk="same_fixed5_real30_returns;dynamic_asset_eligibility;cost/funding/charged_risk_reductions",
        training_slice_seconds=1100.0,
        hard_slice_seconds=1200.0,
        maximum_slices=3,
        memory_bytes=2000000000,
        shared_memory_bytes=8000000000,
        swap=0,
        GPU=0,
        numerical_or_path_failure="restore_last_completed_update;record_precise_failure;stop_no_retry_recipe",
        checkpoint_selection="terminal256_only;no_early_stopping_or_epoch_selection",
        Q4="same_seen_historical_development;one_expanded_model_score_after_public_terminal_freeze",
        comparator="frozen773_model_and_three_controls_saved_results_REUSED;zero_reruns",
        compute="fixed_updates_not_matched_compute;added_history_changes_date_weight_mixture",
        native="export_source_bound_actual92requests;no_new_native_execution_in_this_stage",
        no_tuning=True,
        provider_downloads=0,
        full_December2021_native_tape_claimed=False,
    )
    return dict(p, identity=digest(p))


def task(task_id=ARM):
    if task_id != ARM:
        raise ValueError("Only one authorized expanded1137 fixed907 task")
    return dict(task_id=ARM, lr=0.0003, wallet_equal_mix=0.0)


def sources():
    return {
        **proposed_protocol({})["sources"],
        **{str(p.relative_to(ROOT)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }


DECISION_SHA = protocol()["identity"]
