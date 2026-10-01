import math
from dataclasses import replace

import numpy as np
import pytest
from scipy.stats import pearsonr, spearmanr
from sklearn.preprocessing import StandardScaler

from quant.research_fast.dataset import START, TargetNormalizer, day_us, make_folds, protocol
from quant.research_fast.evaluation import (
    DAY_US,
    EconomicsResult,
    EvaluationBatch,
    FoldEvaluation,
    ObservedPrices,
    economics,
    evaluate_fold,
    first_round_screen,
    original_predictions,
    prediction_metrics,
    sample_id,
    sprint_screen,
)

BASE = day_us(START)
SHA = "a" * 64


@pytest.fixture
def common(tmp_path):
    from test_fast_dataset import write_dataset

    return write_dataset(tmp_path / "shared_evaluation_source")


def common_batch(offsets=(0, 60, 120), *, entry=100., exit=101., observed=None, end=None):
    decisions = BASE + np.asarray(offsets, dtype=np.int64) * 1_000_000
    n = len(decisions)
    truth = np.zeros((n, 2, 4))
    truth[:, :, 0] = np.linspace(-.4, .8, n)[:, None]
    truth[:, :, 1] = exit / entry - 1
    truth[:, :, 2] = np.linspace(.2, -.3, n)[:, None]
    truth[:, :, 3] = np.linspace(-12, -5, n)[:, None]
    if observed is None:
        marks = ObservedPrices([BASE - 5_000_000, BASE + DAY_US], [100., 100.])
        observed = (marks, marks)
    return EvaluationBatch(
        SHA, "engineering", BASE, end or BASE + DAY_US,
        tuple(sample_id(SHA, t) for t in decisions), decisions, truth,
        np.repeat((decisions + 5_100_000)[:, None], 2, axis=1),
        np.repeat((decisions + 305_100_000)[:, None], 2, axis=1),
        np.full((n, 2), entry), np.full((n, 2), exit), decisions + 310_000_000, observed,
    )


def predictions(batch, *, both=False, signal=.004):
    result = batch.truth.copy()
    result[:, :, 1] = signal if both else np.array([signal, 0.])
    return result


def test_original_units_inverse_and_scipy_metrics_keep_all_common_samples():
    batch = common_batch((0, 60, 120, 180, 240))
    truth = batch.truth.copy()
    truth[:, :, 1] = np.array([.01, -.02, .03, -.01, .02])[:, None]
    exit_prices = batch.entry_price * (1 + truth[:, :, 1])
    batch = replace(batch, truth=truth, exit_price=exit_prices)
    pred = truth.astype(np.float64)
    pred[:, :, 0] = truth[::-1, :, 0]
    pred[:, :, 1] = np.array([.1, -.1, .2, .05, 0.])[:, None]
    scaler = StandardScaler().fit(np.arange(80).reshape(10, 8))
    normalizer = TargetNormalizer(scaler, SHA, "engineering", BASE - 1, 10)
    restored = original_predictions(
        batch, normalizer.transform(pred), batch.sample_ids,
        units="standardized", normalizer=normalizer,
    )
    np.testing.assert_allclose(restored, pred, atol=1e-12)
    metrics = prediction_metrics(batch, restored)["spot_BTCUSDT"]
    assert metrics["samples"] == 5
    assert metrics["flow_IC"] == pytest.approx(-1.)
    assert metrics["return_Pearson_IC"] == pytest.approx(pearsonr(pred[:, 0, 1], truth[:, 0, 1])[0])
    assert metrics["return_Spearman_IC"] == pytest.approx(
        spearmanr(pred[:, 0, 1], truth[:, 0, 1])[0]
    )
    assert metrics["RV_rank_IC"] == pytest.approx(1.)
    assert metrics["flow_sign_accuracy"] == pytest.approx(.2)
    with pytest.raises(ValueError, match="target normalizer"):
        original_predictions(batch, pred, batch.sample_ids, units="standardized",
                             normalizer=replace(normalizer, fit_last_label_available_us=BASE))


def test_missing_misaligned_nonfinite_predictions_and_mutated_truth_are_rejected():
    batch = common_batch()
    pred = predictions(batch)
    for ids in (batch.sample_ids[::-1], batch.sample_ids[:-1]):
        with pytest.raises(ValueError, match="sample IDs"):
            evaluate_fold(batch, pred, ids)
    with pytest.raises(ValueError, match="shape"):
        evaluate_fold(batch, pred[:-1], batch.sample_ids)
    pred[0, 0, 1] = np.nan
    with pytest.raises(ValueError, match="Nonfinite"):
        evaluate_fold(batch, pred, batch.sample_ids)
    with pytest.raises(ValueError, match="QA"):
        replace(batch, entry_price=np.full((3, 2), 1.))
    with pytest.raises(ValueError, match="binding"):
        replace(batch, sample_ids=batch.sample_ids[::-1])
    with pytest.raises(ValueError):
        batch.truth[0, 0, 0] = 1
    assert prediction_metrics(batch, batch.truth)["spot_BTCUSDT"]["return_Pearson_IC"] is None


def test_one_roundtrip_hand_accounting_cost_identity_and_return_only_signal():
    batch = common_batch((0,), entry=100., exit=110.)
    prediction = predictions(batch)
    prediction[0, 0, 0] = -1000  # flow never gates the policy
    result = economics(batch, prediction)
    budget = .3 * 10_000 / (1 + .6 * .0015)
    quantity = budget / 100
    gross = quantity * 10
    fee, extra = (budget + quantity * 110) * .001, (budget + quantity * 110) * .0005
    assert result.trades["reference_notional"].to_list() == pytest.approx([budget, budget * 1.1])
    assert result.summary["final_nav"] == pytest.approx(10_000 + gross - fee - extra)
    assert result.summary["fees"] == pytest.approx(fee)
    assert result.summary["execution_costs"] == pytest.approx(extra)
    assert result.summary["gross_pnl"] == pytest.approx(gross)
    assert result.summary["turnover"] == pytest.approx(2.1 * budget / 10_000)
    assert result.summary["gross_proxy_return"] - result.summary["estimated_cost"] == pytest.approx(
        result.summary["net_proxy_return"], abs=1e-14
    )
    assert not result.summary["implementable_strategy"]
    assert not result.summary["real_bbo"]
    flat = predictions(batch, signal=0)
    flat[:, :, 0] = 1000
    assert economics(batch, flat).summary["trade_count"] == 0


def test_same_symbol_no_overlap_pending_and_open_position_then_new_hold():
    batch = common_batch((0, 60, 120, 300, 360))
    result = economics(batch, predictions(batch))
    assert result.trades["side"].to_list() == ["buy", "sell", "buy", "sell"]
    assert result.summary["overlap_signals_blocked"] == 3
    assert result.trades["decision_us"].to_list() == [BASE, BASE, BASE + 360_000_000,
                                                    BASE + 360_000_000]
    assert all(sell > buy for buy, sell in zip(result.trades["event_us"][::2],
                                              result.trades["event_us"][1::2], strict=True))


def test_two_coins_post_cost_caps_cash_and_fixed_spread_sensitivities():
    batch = common_batch((0,), exit=100.)
    report = evaluate_fold(batch, predictions(batch, both=True), batch.sample_ids)
    final_nav = []
    for spread, result in report.economics.items():
        rate = .001 + (8 + spread) / 20_000
        budget = .3 * 10_000 / (1 + .6 * rate)
        assert result.summary["final_nav"] == pytest.approx(10_000 - 4 * budget * rate)
        buys = result.trades.filter(result.trades["side"] == "buy")
        assert buys["symbol_weight_after"].max() <= .3 + 1e-12
        assert buys["gross_weight_after"].max() <= .6 + 1e-12
        assert result.trades["cash_after"].min() >= 0
        final_nav.append(result.summary["final_nav"])
    assert final_nav[0] > final_nav[1] > final_nav[2]
    with pytest.raises(ValueError, match="spread"):
        economics(batch, predictions(batch), assumed_spread_bps=0)


def test_decision_budget_uses_observed_price_never_future_entry_exit_or_label():
    batch = common_batch((0,), entry=100., exit=110.)
    changed = common_batch((0,), entry=200., exit=1000.)
    first = economics(batch, predictions(batch)).trades.row(0, named=True)
    second = economics(changed, predictions(changed)).trades.row(0, named=True)
    assert first["decision_nav"] == second["decision_nav"] == 10_000
    assert first["decision_observed_price"] == second["decision_observed_price"] == 100
    assert first["decision_quote_budget"] == second["decision_quote_budget"]
    assert first["reference_notional"] == second["reference_notional"]
    assert first["quantity"] == pytest.approx(2 * second["quantity"])


def test_midnight_observed_nav_hand_sharpe_mdd_and_cash_flow_conservation():
    observed = ObservedPrices([BASE - 5_000_000, BASE + DAY_US, BASE + 2 * DAY_US], [100, 90, 120])
    batch = common_batch((86_200,), exit=120., observed=(observed, observed),
                         end=BASE + 2 * DAY_US)
    result = economics(batch, predictions(batch))
    budget = .3 * 10_000 / (1 + .6 * .0015)
    first_cash = 10_000 - budget * 1.0015
    first_nav = first_cash + budget / 100 * 90
    final_nav = 10_000 + .2 * budget - 2.2 * budget * .0015
    assert result.daily_nav["nav"].to_list() == pytest.approx([first_nav, final_nav])
    assert result.daily_nav["cash"][0] == pytest.approx(first_cash)
    assert result.daily_nav["BTC_quantity"].to_list() == pytest.approx([budget / 100, 0])
    assert result.daily_nav["fees"].to_list() == pytest.approx([budget * .001, 1.2 * budget * .001])
    assert result.daily_nav["turnover"].to_list() == pytest.approx([budget / 10_000,
                                                                  budget * 1.2 / first_nav])
    returns = np.array([first_nav / 10_000 - 1, final_nav / first_nav - 1])
    sharpe = returns.mean() / returns.std(ddof=1) * math.sqrt(365)
    assert result.summary["sharpe"] == pytest.approx(sharpe)
    assert result.summary["max_drawdown"] == pytest.approx(1 - first_nav / 10_000)
    # Exit 120 was unavailable at midnight. Marking it early would erase this drawdown.
    assert result.daily_nav["nav"][0] < 10_000


def test_missing_decision_mark_blocks_without_model_specific_sample_drop():
    observed = ObservedPrices([BASE + 10_000_000, BASE + DAY_US], [100, 101])
    batch = common_batch((0,), observed=(observed, observed))
    result = evaluate_fold(batch, predictions(batch), batch.sample_ids)
    assert result.metadata["samples"] == 1
    assert result.metrics["spot_BTCUSDT"]["samples"] == 1
    assert result.economics[2].summary["missing_observed_price_signals"] == 1
    assert result.economics[2].summary["trade_count"] == 0


def fold_reports(values, *, formal=True, gross=.01, net=.001):
    """Small isolated reports to exercise fold aggregation, never marketed as OOS."""
    reports = []
    for fold, value in zip(make_folds(), values, strict=True):
        metrics = {stream: {"flow_IC": value, "return_Spearman_IC": 0.}
                   for stream in ("spot_BTCUSDT", "spot_ETHUSDT")}
        economic = EconomicsResult(
            None, None, {"gross_proxy_return": gross, "net_proxy_return": net}
        )
        reports.append(FoldEvaluation(
            {"fold": fold.name, "formal_fold": True, "status": "FORMAL_DATA_READY" if formal
             else "SMOKE_ONLY", "samples": 100, "batch_sha256": fold.name, "resources": {},
             "dataset_sha256": SHA},
            metrics, {spread: economic for spread in (2, 4, 8)},
        ))
    return reports


def test_sprint_gate_uses_equal_folds_sign_and_positive_concentration_not_pooling():
    reports = fold_reports([.04, .04, .04, .04, -.01, -.01])
    assert not sprint_screen(reports)["passed"]  # mean .0233 fails .03 despite positive pooled IC
    reports = fold_reports([.06, .06, .06, .06, -.01, -.01])
    gate = sprint_screen(reports)
    assert gate["passed"]
    item = gate["diagnostics"]["spot_BTCUSDT"]["flow_IC"]
    assert item["equal_fold_mean"] == pytest.approx(.22 / 6)
    assert item["positive_fold_fraction"] == pytest.approx(4 / 6)
    assert item["largest_positive_fold_IC_fraction"] == pytest.approx(.25)
    assert not sprint_screen(fold_reports([.5, .01, .01, .01, -.01, -.01]))["passed"]
    assert not sprint_screen(fold_reports([.1, .1, .1, -.01, -.01, -.01]))["passed"]
    assert sprint_screen(reports[:-1])["status"] == "INSUFFICIENT_EVIDENCE"
    assert sprint_screen(fold_reports([.06] * 6, formal=False))["status"] == "INSUFFICIENT_EVIDENCE"
    assert sprint_screen(fold_reports([.06] * 6, net=-.001))["status"] == (
        "PREDICTIVE_BUT_COST_LIMITED"
    )
    with pytest.raises(ValueError, match="Duplicate"):
        sprint_screen(reports + reports[:1])
    changed = list(reports)
    changed[0] = replace(changed[0], metadata={**changed[0].metadata, "dataset_sha256": "b" * 64})
    with pytest.raises(ValueError, match="one dataset"):
        sprint_screen(changed)


def test_complete_ten_config_binding_and_top_three_or_no_partial_leaderboard():
    reports = fold_reports([.04] * 6)
    assert first_round_screen({"RIDGE-1": reports})["leaderboard"] == []
    models = {config["id"]: reports for config in protocol()["configs"]}
    complete = first_round_screen(models)
    assert len(complete["leaderboard"]) == 10 and len(complete["top_directions"]) == 3
    assert len({item["direction"] for item in complete["top_directions"]}) == 3
    # Related configs cannot take three direction slots even when they rank highest.
    clustered = {**models, "XGB-S": fold_reports([.09] * 6),
                 "XGB-M": fold_reports([.08] * 6), "TCN-S": fold_reports([.07] * 6),
                 "TCN-M": fold_reports([.06] * 6), "TS2VEC-LINEAR-1": fold_reports([.05] * 6),
                 "TS2VEC-LGB-1": fold_reports([.045] * 6)}
    assert first_round_screen(clustered)["top_directions"] == [
        {"direction": "XGB", "best_config": "XGB-S", "score": pytest.approx(3.)},
        {"direction": "TCN", "best_config": "TCN-S", "score": pytest.approx(7 / 3)},
        {"direction": "TS2Vec", "best_config": "TS2VEC-LINEAR-1", "score": pytest.approx(5 / 3)},
    ]
    assert not complete["production_or_candidate_qualification"]
    changed = list(reports)
    changed[0] = replace(changed[0], metadata={**changed[0].metadata, "batch_sha256": "different"})
    with pytest.raises(ValueError, match="identical"):
        first_round_screen({**models, "RIDGE-1": changed})


def test_batch_dataset_thin_adapter_matches_existing_common_labels_and_ids(common):
    # The source fixture is from FR64; all files and negative work stay in native STATE.
    from test_fast_dataset import mini_fold

    dataset, _ = common
    fold = mini_fold()
    indices = dataset.split_indices(fold, "test")
    batch = EvaluationBatch.from_dataset(dataset, indices, fold=fold)
    sample = dataset[int(indices[0])]
    assert batch.sample_ids[0] == sample["sample_id"]
    assert batch.truth.dtype == np.float32
    for offset, index in enumerate(indices):
        sample = dataset[int(index)]
        np.testing.assert_array_equal(batch.truth[offset], sample["y_raw"])
        for s, stream in enumerate(("spot_BTCUSDT", "spot_ETHUSDT")):
            assert batch.entry_us[offset, s] == sample["qa"][f"{stream}__entry_trade_us"]
            assert batch.exit_us[offset, s] == sample["qa"][f"{stream}__exit_trade_us"]
            assert batch.entry_price[offset, s] == sample["qa"][f"{stream}__entry_price_proxy"]
            assert batch.exit_price[offset, s] == sample["qa"][f"{stream}__exit_price_proxy"]
    assert batch.observed[0].asof(batch.decision_us[0])[0] <= batch.decision_us[0]
    with pytest.raises(ValueError, match="complete common"):
        EvaluationBatch.from_dataset(dataset, indices[:-1], fold=fold)
