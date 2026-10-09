"""One fixed three-fold protocol; controls and criteria precede execution."""

from datetime import datetime, timezone
from pathlib import Path

from modules.temporal_expert_input.stage import sources as old_sources
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.model import SEED

FOLDS = {
    name: int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()) * 1000000
    for name, day in (
        ("FOLD_20230703", "2023-07-03"),
        ("FOLD_20231002", "2023-10-02"),
        ("FOLD_20240101", "2024-01-01"),
    )
}
CONTROLS = {
    "CASH": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "VOL": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    "CS": [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
    "SHORT": [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    "VOL50_CS50": [0.0, 0.5, 0.0, 0.0, 0.5, 0.0],
    "CASH50_VOL25_CS25": [0.5, 0.25, 0.0, 0.0, 0.25, 0.0],
}
PROTOCOL = dict(
    schema="FRESH512_THREE_FOLD_PREQUENTIAL_OWN_PATH_V1",
    folds=FOLDS,
    classification="historical_prequential_research_seen_project_data;not_pristine_unseen",
    seed=SEED,
    planned_fits=3,
    fixed_updates=512,
    diagnostics=[0, 128, 256, 512],
    parameter_count=13699,
    feature_batch_size=32,
    dropout=0.1,
    architecture="unchanged_CORE5_64x24values24masks_GRU32_joint160to32_plus18currentexpertinputs",
    initialization="fresh_eachfold_same_seed_model_Adam_Python_NumPy_Torch_RNG;all_births0;no778warmstart",
    normalization="fresh_union_of_unique_prefix_training_feature_rows;no_forward_rows;no907scaler",
    objective="unchanged_charged_daily_boundary_own_path_v2;date_weighted_complete_natural_wallet_prefixes",
    chronology="natural_gaps_retained;declared_prefix_paidclose;forwardwallet63decisions_including_paidclose",
    additional_embargo_days=0,
    purge="actual_active_outcome_and_paid_close_availability_strictly_before_forwardfirstdecision",
    label_overlap="no_rolling63day_training_labels;full_prefix_adjoint_matures_at_prefix_paidclose",
    terminal_suffix="known_flat_CASH_identity;no_future_terminal_price_or_funding_read",
    controls=CONTROLS,
    primary_control="VOL50_CS50",
    screen="mean_block_own_path_utility_excess>0_AND_worst_block_excess>=0_vs_fixed_primary",
    reporting="all_controls_and_folds;no_block_winner_or_forward_checkpoint_selection",
    forward="freeze_at512;eval_only_deterministic;never_forward_loss_in_optimizer",
    mapper="unchanged_L1<=.1_gross<=.6_asset<=.3;eligibility_release_separate;endogenous_wallet",
    capital=10000.0,
    observed_wallet=False,
    costs_and_funding="unchanged;paid_terminal_flattening",
    evidence="approximate_daily_surrogate_until_independent_native_replay;not_exchange_native",
    limits=dict(
        maximum_concurrent_workers=2,
        seconds_per_slice=1200.0,
        maximum_worker_memory=2000000000,
        shared_memory=8000000000,
        swap=0,
        GPU=0,
    ),
    numeric_failure="persist_precise_issue;continue_other_independent_folds;no_recipe_retry_or_tuning",
)


def sources():
    root = Path(__file__).resolve().parents[2]
    weighting = "modules/temporal_episode_weighting_v2/gradient.py"
    return {
        **old_sources(),
        weighting: sha(root / weighting),
        **{
            str(p.relative_to(Path(__file__).resolve().parents[2])): sha(p)
            for p in sorted(Path(__file__).parent.glob("*.py"))
        },
    }
