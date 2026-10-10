"""Synthetic counterexamples only; no historical economic scoring or fitting."""

import copy
import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import torch

from modules.temporal_episode_weighting_v2.gradient import (
    memory_bounded_gradients as original_replay,
)
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_short_expansion.adapter import append_episode
from modules.temporal_short_expansion.gradient import request_gradient as original_gradient
from modules.temporal_two_expert.exact import Episode, sha
from modules.temporal_two_expert.feature_windows import TRAINING_CUTOFF_US
from modules.temporal_two_expert.inputs import CORE5, DAY_US, FeatureTimeline, fit_standardizer
from modules.temporal_two_expert.training_packet import named_context

from .data import CausalInputs, admitted_runs, assemble, new_episodes
from .gradient import memory_bounded_gradients, request_gradient
from .packet import DELAY, END, ROOT, START, EconomicPacket, load_packet
from .readiness import proposed_protocol


def causal_fixture(prototype, n=8, start=START):
    clocks = np.arange(start - 63 * DAY_US, start + n * DAY_US, DAY_US, dtype=np.int64)
    x = np.sin(clocks[:, None, None] / DAY_US * 0.1 + np.arange(120).reshape(1, 5, 24))
    timeline = FeatureTimeline(
        x,
        np.ones_like(x, bool),
        np.ones((len(x), 5), bool),
        clocks,
        np.broadcast_to(clocks[:, None, None], x.shape),
        "a" * 64,
    )
    windows = timeline.windows(clocks[63:])
    contexts = tuple(
        named_context(
            prototype,
            int(t),
            np.array([[0] * 5, [0.1, 0.05, 0.02, 0.01, 0.01], [0.025, -0.025, 0.012, -0.012, 0.0]]),
            np.ones(3, bool),
            np.tile(np.array([-0.001, 0.001] * 15)[:, None], (1, 5)),
            np.zeros(13),
            np.full(3, t, np.int64),
        )
        for t in windows.decision_us
    )
    return CausalInputs(
        windows,
        contexts,
        np.tile([-0.015, -0.01, -0.005, 0.0, 0.0], (n, 1, 1)),
        np.ones((n, 1), bool),
        dict(synthetic=True),
    )


def economic_fixture(causal):
    n = len(causal.contexts)
    prices = 100 * np.exp(0.002 * np.sin(np.arange(n)[:, None] + np.arange(5)[None, :]))
    funding = np.tile([0.01, -0.01, 0.002, 0.0, -0.001], (n - 1, 1))
    return EconomicPacket(
        causal.windows.decision_us,
        prices,
        funding,
        np.ones((n, 5), bool),
        np.ones((n - 1, 5), bool),
        dict(synthetic=True),
    )


def original_abi(episode, prototype):
    base = episode.original.original
    original = Episode(
        base.wallet_id,
        base.windows,
        base.contexts,
        np.vstack((base.prices, base.prices[-1:])),
        np.vstack((base.funding_coeff, np.zeros((1, 5)))),
        base.label_available_us,
        base.start_us,
        base.end_us,
        base.split_cutoff_us,
        base.role,
        base.producer_sha256,
    )
    return expose_episode(
        append_episode(
            original,
            episode.expert_targets[:, 5:6],
            episode.eligible[:, 5:6],
            episode.target_available_us[:, 5:6],
            prototype,
            "c" * 64,
        )
    )


def test_gap_admission_rejects_unknown_prices_funding_and_context_without_splicing(prototype):
    causal = causal_fixture(prototype, 12)
    packet = economic_fixture(causal)
    prices, known = packet.prices.copy(), packet.price_known.copy()
    prices[3, 2], known[3, 2] = np.nan, False
    funding, fknown = packet.funding_coeff.copy(), packet.funding_known.copy()
    funding[7, 4], fknown[7, 4] = np.nan, False
    packet = replace(
        packet, prices=prices, price_known=known, funding_coeff=funding, funding_known=fknown
    )
    runs, audit = admitted_runs(packet, causal)
    assert runs == ((0, 2), (4, 7), (8, 11))
    assert audit["admitted_active_intervals"] == 8 and audit["rejected_active_intervals"] == 3
    added, _ = new_episodes(packet, causal, prototype)
    assert [len(e.contexts) for e in added] == [3, 4, 4]
    for e in added:
        assert e.prices.shape == (len(e.contexts), 5)
        assert e.funding_coeff.shape == (len(e.contexts) - 1, 5)
        assert not e.prices.flags.writeable and not e.contexts[0].past_returns30.flags.writeable
    contexts = list(causal.contexts)
    contexts[5] = None
    _, revised = admitted_runs(packet, replace(causal, contexts=tuple(contexts)))
    assert revised["rejection_counts_may_overlap"]["fixed5_covariance"] == 2
    with pytest.raises(ValueError, match="NaN"):
        replace(packet, prices=np.nan_to_num(packet.prices, nan=100.0))
    with pytest.raises(ValueError, match="calendar"):
        replace(packet, decision_us=np.r_[packet.decision_us[:4], packet.decision_us[3:-1]])


def test_cash_only_dates_do_not_create_extra_history_and_future_clocks_rejected(prototype):
    causal = causal_fixture(prototype)
    contexts = [
        replace(c, eligible=np.array([True, False, False, False, False])) for c in causal.contexts
    ]
    empty = replace(causal, contexts=tuple(contexts), short_eligible=np.zeros((8, 1), bool))
    assert admitted_runs(economic_fixture(causal), empty)[0] == ()
    contexts = list(causal.contexts)
    contexts[3] = empty.contexts[3]
    short_eligible = causal.short_eligible.copy()
    short_eligible[3] = False
    interior_cash = replace(causal, contexts=tuple(contexts), short_eligible=short_eligible)
    runs, audit = admitted_runs(economic_fixture(causal), interior_cash)
    assert runs == ((0, 7),) and audit["admitted_real_interior_cash_dates"] == 1
    added, _ = new_episodes(economic_fixture(causal), causal, prototype)
    base = added[0].original.original
    labels = base.label_available_us.copy()
    labels[0] = TRAINING_CUTOFF_US
    with pytest.raises(ValueError, match="mature"):
        replace(base, label_available_us=labels)
    clocks = base.windows.available_us.copy()
    clocks[0, -1, 0, 0] = base.windows.decision_us[0] + 1
    with pytest.raises(ValueError, match="available at completed"):
        replace(base.windows, available_us=clocks)


def test_real_terminal_request_vjp_exact_original_parity_and_finite_difference(prototype):
    causal = causal_fixture(prototype)
    episode = new_episodes(economic_fixture(causal), causal, prototype)[0][0]
    original = original_abi(episode, prototype)
    requests = np.tile([0.2, 0.35, 0.0, 0.0, 0.3, 0.15], (8, 1))
    actual = request_gradient(requests, episode, prototype)
    expected = original_gradient(requests, original, prototype)
    assert actual[0] == expected[0] and actual[2]["terminal_cash_realized"]
    np.testing.assert_array_equal(actual[1], expected[1])
    assert float(actual[2]["fees"]) > 0
    for i, j in ((0, 1), (3, 4), (6, 5)):
        left, right = requests.copy(), requests.copy()
        left[i, j] -= 1e-6
        left[i, 0] += 1e-6
        right[i, j] += 1e-6
        right[i, 0] -= 1e-6
        difference = (
            request_gradient(right, episode, prototype)[0]
            - request_gradient(left, episode, prototype)[0]
        ) / 2e-6
        np.testing.assert_allclose(
            actual[1][i, j] - actual[1][i, 0], difference, rtol=2e-4, atol=2e-9
        )
    np.testing.assert_array_equal(actual[1][:, 2:4], 0)
    np.testing.assert_array_equal(actual[1][-1], 0)


def test_feature_masks_dropout_replay_date_weights_and_old_kernel_unchanged(prototype):
    causal = causal_fixture(prototype)
    valid, values = causal.windows.valid.copy(), causal.windows.values.copy()
    valid[:, :, 2, 7] = False
    values[:, :, 2, 7] = np.nan
    causal = replace(causal, windows=replace(causal.windows, valid=valid, values=values))
    episode = new_episodes(economic_fixture(causal), causal, prototype)[0][0]
    original = original_abi(episode, prototype)
    scaler = fit_standardizer([episode.windows], training_cutoff_us=TRAINING_CUTOFF_US)
    model, optimizer = initialize(scaler)
    rng = torch.get_rng_state().clone()
    model.train()
    loss, requests = memory_bounded_gradients(model, [episode], prototype, feature_batch_size=3)
    gradients = [p.grad.clone() for p in model.parameters()]
    final_rng = torch.get_rng_state().clone()
    model.zero_grad(set_to_none=True)
    torch.set_rng_state(rng)
    other_loss, other_requests = original_replay(model, [original], prototype, feature_batch_size=3)
    assert loss == other_loss and not optimizer.state
    np.testing.assert_array_equal(requests, other_requests)
    assert torch.equal(final_rng, torch.get_rng_state())
    assert all(torch.equal(p.grad, g) for p, g in zip(model.parameters(), gradients, strict=True))
    # Original wallets use the original request VJP through the dispatcher.
    expected = original_gradient(requests, original, prototype)
    actual = request_gradient(requests, original, prototype)
    assert actual[0] == expected[0]
    np.testing.assert_array_equal(actual[1], expected[1])
    assert model.parameter_count == 13699


def synthetic_originals(prototype):
    output, start = [], END
    for i, length in enumerate([54, 88, 62, 144, 430]):
        c = causal_fixture(prototype, length, start)
        p = economic_fixture_outside_2021(c)
        original = Episode(
            f"ORIGINAL{i}",
            c.windows,
            c.contexts,
            p[0],
            p[1],
            np.r_[c.windows.decision_us[1:] + DELAY, c.windows.decision_us[-1] + DELAY],
            start,
            start + length * DAY_US,
            TRAINING_CUTOFF_US,
            "TRAIN",
            "b" * 64,
        )
        output.append(
            expose_episode(
                append_episode(
                    original,
                    c.short_targets,
                    c.short_eligible,
                    c.windows.decision_us[:, None],
                    prototype,
                    "c" * 64,
                )
            )
        )
        start += (length + ([10, 16, 20, 20, 0][i])) * DAY_US
    return tuple(output)


def economic_fixture_outside_2021(causal):
    n = len(causal.contexts)
    return np.ones((n + 1, 5)) * 100.0, np.zeros((n, 5))


def test_before_after_counts_preserve_original_five_and_deduplicate_warmup(prototype):
    original = synthetic_originals(prototype)
    scaler = fit_standardizer([e.windows for e in original], training_cutoff_us=TRAINING_CUTOFF_US)
    assert scaler.provenance["real_row_count"] == 907
    causal = causal_fixture(prototype, 365)
    added, _ = new_episodes(economic_fixture(causal), causal, prototype)
    combined, expanded, receipt = assemble(original, added, scaler)
    assert all(a is b for a, b in zip(combined[-5:], original, strict=True))
    assert receipt["before"]["active_dates"] == 773
    assert receipt["after"]["active_dates"] == 1137
    assert receipt["after"]["decisions"] == 1143
    assert receipt["additional_paid_closures"] == 1
    assert receipt["added_feature_rows_overlapping_old_warmup"] == 63
    assert receipt["added_unique_feature_rows"] == 365
    assert expanded.provenance["real_row_count"] == 1272
    assert receipt["date_weight_lengths"] == [365, 54, 88, 62, 144, 430]
    assert receipt["date_weight_coefficients"][-1] == 430 / 1143
    with pytest.raises(ValueError, match="overlap"):
        assemble(original, added + added, scaler)


def write_source_fixture(directory):
    d = np.arange(START, END, DAY_US, dtype=np.int64)
    p, f = np.ones((365, 5)) * 100.0, np.ones((364, 5)) * 0.27
    np.savez(
        directory / "ECONOMICS.npz",
        symbol_order=np.array(CORE5),
        decision_us=d,
        execution_us=d + DELAY,
        funding_interval_start_us=d[:-1] + DELAY,
        funding_interval_end_us=d[1:] + DELAY,
        prices=p,
        funding_coeff=f,
    )
    artifacts = []
    times = np.repeat(d, 3) + np.tile(np.array([0, 8, 16]) * (DAY_US // 24), 365)
    for symbol in CORE5:
        tables = {
            f"normalized/data/normalized/{symbol}_daily.parquet": pd.DataFrame(
                dict(
                    dt=pd.to_datetime(d, unit="us", utc=True),
                    exec_price=p[:, 0],
                    complete_kline=True,
                    unique_minutes=1440,
                )
            ),
            f"normalized/data/normalized/{symbol}_funding_events.parquet": pd.DataFrame(
                dict(
                    calc_time_ms=times // 1000,
                    funding_interval_hours=8.0,
                    past_mark_price=90.0,
                    last_funding_rate=0.001,
                    past_mark_available_us=(times - 1) // 60000000 * 60000000,
                )
            ),
            f"normalized/economics/{symbol}_funding_intervals.parquet": pd.DataFrame(
                dict(funding_interval_complete=True, mark_funding_per_unit=f[:, 0])
            ),
        }
        for name, frame in tables.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.Table.from_pandas(frame), path)
            artifacts.append(dict(path=name, bytes=path.stat().st_size, SHA256=sha(path)))
    index = dict(
        symbols_order=list(CORE5),
        source_download_complete=True,
        official_archive_receipts_verified=True,
        execution_and_held_funding_ready=True,
        normalization_source_SHA256={
            "modules/collector_research/pipeline/normalize.py": sha(
                ROOT / "modules/collector_research/pipeline/normalize.py"
            )
        },
        economic_SHA256=sha(directory / "ECONOMICS.npz"),
        economic_table_artifacts=artifacts,
    )
    path = directory / "CONSUMER_INDEX.json"
    path.write_text(json.dumps(index))
    return path, index


def test_source_hash_completeness_clock_and_independent_funding_gates(tmp_path):
    path, index = write_source_fixture(tmp_path)
    args = dict(source_commit="d" * 40, consumer_sha256=sha(path))
    packet = load_packet(tmp_path, **args)
    assert packet.prices.shape == (365, 5) and packet.funding_coeff.shape == (364, 5)
    assert max(packet.receipt["independent_funding_max_error"].values()) < 1e-15
    changed = dict(index, source_download_complete=False)
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="consumer bytes"):
        load_packet(tmp_path, **args)
    with pytest.raises(ValueError, match="Complete source"):
        load_packet(tmp_path, source_commit=args["source_commit"], consumer_sha256=sha(path))
    path.write_text(json.dumps(index))
    artifact = index["economic_table_artifacts"][1]
    event_path = tmp_path / artifact["path"]
    events = pq.read_table(event_path).to_pandas()
    events.loc[1, "past_mark_price"] += 1.0
    pq.write_table(pa.Table.from_pandas(events), event_path)
    with pytest.raises(ValueError, match="table bytes"):
        load_packet(tmp_path, **args)
    artifact.update(bytes=event_path.stat().st_size, SHA256=sha(event_path))
    path.write_text(json.dumps(index))
    with pytest.raises(AssertionError):
        load_packet(tmp_path, source_commit=args["source_commit"], consumer_sha256=sha(path))


def test_proposal_is_one_fixed_recipe_and_cannot_authorize_fitting():
    proposal = proposed_protocol(dict(source_status="PENDING"))
    assert proposal["planned_fits"] == 1 and proposal["lr"] == 0.0003
    assert proposal["updates_cap"] == 256 and proposal["seed"] == 20261009
    assert proposal["fit_entrypoint_available"] is False
    assert proposal["comparator"]["rerun"] is False
    assert "modules/temporal_july_transfer/data.py" in proposal["sources"]
    assert (
        "modules/temporal_july_transfer/upstream/conditional_selector_inputs.py"
        in proposal["sources"]
    )
    assert "not_matched_compute" in proposal["compute"]
    changed = copy.deepcopy(proposal)
    changed["data"]["source_status"] = "COMPLETE"
    assert changed["status"] == proposal["status"]


def update_source_table(directory, index, name, frame):
    path = directory / name
    pq.write_table(pa.Table.from_pandas(frame), path)
    artifact = next(row for row in index["economic_table_artifacts"] if row["path"] == name)
    artifact.update(bytes=path.stat().st_size, SHA256=sha(path))


def test_source_reader_rejects_missing_bracket_even_with_three_held_events(tmp_path):
    path, index = write_source_fixture(tmp_path)
    name = "normalized/data/normalized/BTCUSDT_funding_events.parquet"
    events = pq.read_table(tmp_path / name).to_pandas().iloc[1:].reset_index(drop=True)
    update_source_table(tmp_path, index, name, events)
    path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="both-sided"):
        load_packet(tmp_path, source_commit="d" * 40, consumer_sha256=sha(path))


def test_source_reader_retains_unknown_mark_interval_and_rejects_shifted_clock(tmp_path):
    path, index = write_source_fixture(tmp_path)
    with np.load(tmp_path / "ECONOMICS.npz", allow_pickle=False) as z:
        arrays = {k: z[k].copy() for k in z.files}
    arrays["price_known"] = np.ones((365, 5), bool)
    arrays["funding_known"] = np.ones((364, 5), bool)
    arrays["funding_known"][10, 0] = False
    arrays["funding_coeff"][10, 0] = np.nan
    np.savez(tmp_path / "ECONOMICS.npz", **arrays)
    index["economic_SHA256"] = sha(tmp_path / "ECONOMICS.npz")
    index["execution_and_held_funding_ready"] = False
    name = "normalized/data/normalized/BTCUSDT_funding_events.parquet"
    events = pq.read_table(tmp_path / name).to_pandas()
    events.loc[10 * 3 + 1, "past_mark_price"] = np.nan
    update_source_table(tmp_path, index, name, events)
    name = "normalized/economics/BTCUSDT_funding_intervals.parquet"
    intervals = pq.read_table(tmp_path / name).to_pandas()
    intervals.loc[10, "funding_interval_complete"] = False
    intervals.loc[10, "mark_funding_per_unit"] = np.nan
    update_source_table(tmp_path, index, name, intervals)
    path.write_text(json.dumps(index))
    packet = load_packet(tmp_path, source_commit="d" * 40, consumer_sha256=sha(path))
    assert np.isnan(packet.funding_coeff[10, 0]) and not packet.funding_known[10, 0]
    assert packet.funding_known.sum() == 364 * 5 - 1
    arrays["execution_us"][0] += 1
    np.savez(tmp_path / "ECONOMICS.npz", **arrays)
    index["economic_SHA256"] = sha(tmp_path / "ECONOMICS.npz")
    path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="execution.*clocks"):
        load_packet(tmp_path, source_commit="d" * 40, consumer_sha256=sha(path))
