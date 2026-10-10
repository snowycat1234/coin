"""Executable local readiness/protocol audit. Intentionally has no fit action."""

import argparse
import json
from pathlib import Path

import numpy as np

from modules.temporal_selected_refit.protocol import sources as original_sources
from modules.temporal_selected_refit.stage import inputs
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

from .data import RISK_SOURCES, SHORT_SOURCE_SHA, assemble, cached_inputs, new_episodes
from .packet import ROOT, load_packet

COMPARATOR_COMMIT = "657aeaff93889da600ad88b3603739508ba03216"
COMPARATOR_CHECKPOINT = "58db72621c9596a195267869a9cfa75f56c52162521f3ff77bf5d69c7d7bb88a"
COMPARATOR_MODEL = "38eb7275e4f69382083cbc3d81463d5fd2de955be2ad55919bed42c55c435e84"
INVENTORY_COMMIT = "f7cf1354c35c5a04f3ecc5464664391ae730ae12"


def proposed_protocol(data):
    result = dict(
        schema="SINGLE_EXPANDED2021_REFIT_REVIEW_PROPOSAL_V1",
        status="NOT_RUN_REQUIRES_COMPLETE_PACKET_AND_FINAL_SOURCE_BOUND_PROTOCOL_REVIEW",
        planned_fits=1,
        architecture="unchanged_CORE5_GRU64_hidden32_160to32_plus18expertinputs",
        parameters=13699,
        seed=20261009,
        fresh_initialization=True,
        empty_Adam=True,
        lr=0.0003,
        updates_cap=256,
        dropout=0.1,
        feature_batch_size=32,
        optimizer="Adam;betas.9/.999;eps1e-8;weight_decay0;foreachFalse;clip1",
        objective="same_v2_complete_own_wallet_date_weights_including_paid_close;mixing0",
        capital_each=10000,
        daily_L1_ramp=0.1,
        gross_cap=0.6,
        asset_cap=0.3,
        covariance="unchanged_complete_fixed5_real30_returns;dynamic_expert_asset_eligibility",
        chronology="original5_boundaries_unchanged;new_maximal_source_complete2021_runs;no_gap_splice",
        new_terminal_ABI="existing_Q4_terminal_kernel;N_real_prices,Nminus1_real_intervals;paid_close",
        normalization="same_train_only_unique_valid_window_row_union;expanded_rows_refit;comparator907_unchanged",
        comparator=dict(
            commit=COMPARATOR_COMMIT,
            model_identity=COMPARATOR_MODEL,
            checkpoint_SHA256=COMPARATOR_CHECKPOINT,
            rerun=False,
        ),
        evaluation="same_ALREADY_SEEN_historical_blocks;parameters_frozen;no_untouched_OOS_claim",
        compute="fixed256_update_cap_is_not_matched_compute;expanded_data_changes_date_weight_mixture",
        no_tuning=True,
        no_architecture_change=True,
        no_model_observed_wallet=True,
        fit_entrypoint_available=False,
        data=data,
        sources={
            **original_sources(),
            **{
                str(p.relative_to(ROOT)): sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))
            },
            "modules/temporal_q4_reserved/terminal.py": sha(
                ROOT / "modules/temporal_q4_reserved/terminal.py"
            ),
            **{
                str(p.relative_to(ROOT)): sha(p)
                for p in [
                    *(ROOT / "modules/temporal_july_transfer").glob("*.py"),
                    *(ROOT / "modules/temporal_july_transfer/upstream").glob("*.py"),
                ]
            },
            **RISK_SOURCES,
            "modules/temporal_april_transfer/upstream/momentum_short_pool_target.py": (
                SHORT_SOURCE_SHA
            ),
            **{
                name: sha(ROOT / name)
                for name in (
                    "research/temporal-history-expansion-20261010/requirements.txt",
                    "research/temporal-history-expansion-20261010/PACKET_CONTRACT.json",
                )
            },
        },
    )
    return dict(result, identity=digest(result))


def audit(state, *, packet_directory=None, source_commit=None, consumer_sha256=None):
    old, prototype, original_data, scaler = inputs(state)
    causal = cached_inputs(state, prototype)
    old_rows = {int(t) for e in old for t in e.windows.completed_us.ravel()}
    candidate_rows = set(map(int, np.unique(causal.windows.completed_us)))
    records = dict(
        original_data_identity=digest(original_data),
        inventory_commit=INVENTORY_COMMIT,
        cached_2021=causal.receipt,
        original_wallets=[
            dict(
                wallet_id=e.wallet_id,
                identity=e.identity,
                start_us=e.start_us,
                end_us=e.end_us,
                decisions=len(e.contexts),
                active_dates=len(e.contexts) - 1,
            )
            for e in old
        ],
        before=dict(
            active_dates=773,
            decisions=778,
            wallets=5,
            normalization_rows=907,
            scaler_identity=scaler.identity,
        ),
    )
    if packet_directory is None:
        records.update(
            status="CACHED_INPUTS_READY_ECONOMIC_PACKET_PENDING",
            admitted_new_active_dates=0,
            candidate_new_active_dates=364,
            possible_total_active_dates=1137,
            missing_input=[
                "completed official-source2021 packet; no duplicate acquisition",
                "immutable source commit and exact CONSUMER_INDEX SHA256",
                "365 real 00:01 execution prices x5;364 signed held-funding intervals x5",
                "bound daily/event/interval tables, normalization sources and archive receipts",
                "source completeness flags; explicit NaN/known masks for any retained gaps",
                "final expanded dates/boundaries/scaler/source protocol review before fitting",
            ],
            feature_only_upper_bound=dict(
                candidate_window_rows=len(candidate_rows),
                overlapping_original_warmup_rows=len(candidate_rows & old_rows),
                genuinely_new_feature_rows=len(candidate_rows - old_rows),
                possible_expanded_normalization_rows=len(candidate_rows | old_rows),
                added_training_dates_certified_by_these_rows=0,
                scaler_fitted_on_candidates=False,
            ),
        )
    else:
        packet = load_packet(
            packet_directory, source_commit=source_commit, consumer_sha256=consumer_sha256
        )
        added, admission = new_episodes(packet, causal, prototype)
        _, expanded_scaler, counts = assemble(old, added, scaler)
        records.update(
            status="SOURCE_BOUND_INPUTS_READY_FIT_STILL_REQUIRES_PROTOCOL_REVIEW",
            economic_receipt=packet.receipt,
            packet_identity=packet.identity,
            admission=admission,
            counts=counts,
            added_wallets=[
                dict(
                    wallet_id=e.wallet_id,
                    identity=e.identity,
                    start_us=e.start_us,
                    end_us=e.end_us,
                    decisions=len(e.contexts),
                )
                for e in added
            ],
            expanded_scaler_identity=expanded_scaler.identity,
        )
    return dict(
        readiness=records,
        proposed_protocol=proposed_protocol(records),
        economic_training_runs=0,
        real_wallets_run=0,
        optimizer_updates=0,
        historical_scores=0,
        comparator_reruns=0,
        provider_downloads=0,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--consumer-sha256")
    args = parser.parse_args()
    if bool(args.packet) != bool(args.source_commit and args.consumer_sha256):
        parser.error("Packet, immutable source commit and consumer SHA must be provided together")
    result = audit(
        args.state,
        packet_directory=args.packet,
        source_commit=args.source_commit,
        consumer_sha256=args.consumer_sha256,
    )
    with args.output.open("x") as output:
        json.dump(result, output, sort_keys=True, indent=2)
        output.write("\n")
    print(
        json.dumps(
            dict(
                status=result["readiness"]["status"],
                output=str(args.output),
                optimizer_updates=0,
                real_wallets_run=0,
            )
        )
    )


if __name__ == "__main__":
    main()
