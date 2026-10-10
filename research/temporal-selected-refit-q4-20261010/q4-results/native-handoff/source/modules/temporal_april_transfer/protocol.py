"""One calendar-chosen continuation; retain all three original research folds."""

from pathlib import Path

from modules.temporal_prequential_transfer.protocol import CONTROLS as CONTROLS
from modules.temporal_prequential_transfer.protocol import PROTOCOL as ORIGINAL
from modules.temporal_prequential_transfer.protocol import sources as original_sources
from modules.temporal_two_expert.exact import sha

from .data import FOLD, START

FOLDS = {FOLD: START}
PROTOCOL = dict(
    ORIGINAL,
    schema="ONE_APRIL512_COVERAGE_CHOSEN_CONTINUATION_FOLD_V1",
    folds=FOLDS,
    planned_fits=1,
    training_decisions=749,
    expected_scaler_rows=878,
    selection="next_quarterly_start_after_JulyOctoberJanuary;calendar_and_verified_H1_coverage_only",
    classification="historical_prequential_research_seen_project_data;not_pristine_project_OOS",
    previous_folds="all_three_frozen_folds_retained;failed_worst_fold_screen_cannot_be_erased",
    prior_result_commit="38b86686e40a50c14f0499bd370e4a6bb3d0c339",
    prior_native_result_commit="e24e9004e733eddeebef8eedd0a76e8299447b06",
    maximum_slices=4,
    no_choice_of_alternative_period=True,
    no_parameter_or_seed_or_horizon_search=True,
    no_continuation_beyond512=True,
    limits=dict(ORIGINAL["limits"], maximum_concurrent_workers=1),
    numeric_failure="persist_precise_issue_and_last_atomic_checkpoint;stop_no_recipe_retry",
    forward_source="same_execution00:01:00.000001_event_rate_times_strictly_prior_mark;"
    "actual_H1_contexts_and_64real_feature_steps;onecontinuous63wallet_noMayreset",
)


def sources():
    root = Path(__file__).resolve().parents[2]
    extra = [
        *Path(__file__).parent.rglob("*.py"),
        root / "scripts/investment/momentum_cash_pool_target.py",
        root / "scripts/investment/public_sma_perpetual.py",
        root / "scripts/investment/public_sma_daily.py",
        *sorted((root / "modules/collector_research/pipeline").glob("*.py")),
    ]
    return {**original_sources(), **{str(p.relative_to(root)): sha(p) for p in extra}}
