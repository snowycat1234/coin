"""Active V8 label adapter V2; V1 sources and failed audit remain immutable.

Only target/chronology glue changes. Official scaler/Ridge/strict OOF helpers
are reused from the preserved V1 adapter. No market data or files are discovered.
"""
from __future__ import annotations

import numpy as np
import polars as pl

if __package__:
    from . import labels as _v1
else:
    import labels as _v1

from quant.research_fast.dataset import BAR_US, LOCKED, PAST_BARS, START, STREAMS, day_us

IMPLEMENTATION_VERSION = "V8_LABELS_V2_20261002"
US, EPS = _v1.US, _v1.EPS
RETURN_STREAMS, FLOW_COLUMNS, RETURN_COLUMNS = _v1.RETURN_STREAMS, _v1.FLOW_COLUMNS, _v1.RETURN_COLUMNS
require, contract = _v1.require, _v1.contract
fit_train_scaler, fit_conditional_expectation = _v1.fit_train_scaler, _v1.fit_conditional_expectation
OOFPredictionReceipt, flow_surprise = _v1.OOFPredictionReceipt, _v1.flow_surprise
assert_matched_direct_baseline = _v1.assert_matched_direct_baseline
MATCH_KEYS = _v1.MATCH_KEYS


def _grid(joint):
    times = joint["timestamp"].to_numpy()
    require(len(times) > 0 and np.all(np.diff(times) == BAR_US), "Exact dense 5s source, no interpolation")
    require(times[0] >= day_us(START) and times[-1] + BAR_US <= day_us(LOCKED), "Development dates only; locked access forbidden")
    return times


def past_features(joint, decision_us):
    # Future data is deliberately not passed to the original causal feature API.
    past = joint.filter(pl.col("timestamp").is_between(
        int(decision_us) - PAST_BARS * BAR_US, int(decision_us), closed="left"))
    return _v1.past_features(past, decision_us)


def _max_dependencies(availability, valid_availability, starts, stops):
    result = np.full(len(starts), np.nan)
    for i, (first, last) in enumerate(zip(starts, stops)):
        if np.all(valid_availability[first:last]):
            result[i] = np.max(availability[first:last])
    return result


def label_table(joint, decisions, variant="LEAD_LAG_5M_5M", *, split="DEVELOPMENT_DIAGNOSTIC",
                signal_kind="PAST_ONLY_PREDICTED_FLOW"):
    spec = contract()["labels"].get(variant)
    require(spec is not None, "Only registered V8 label variants")
    require(split in ("TRAIN", "VALIDATION", "OOS_SCREENING", "DEVELOPMENT_DIAGNOSTIC"), "Explicit research split classification required")
    require(signal_kind in ("PAST_ONLY_PREDICTED_FLOW", "OBSERVED_FUTURE_FLOW_DIAGNOSTIC"), "Explicit signal availability mode required")
    times = _grid(joint)
    decisions = np.asarray(decisions, dtype=np.int64)
    require(decisions.ndim == 1 and len(decisions) > 0 and np.all(np.diff(decisions) > 0), "Unique chronological explicit decision IDs required")
    require(np.all(decisions % (60 * US) == 0), "Frozen minute decision frequency")
    bounds = [decisions + spec[key] * US for key in ("flow_start_offset_seconds", "flow_end_offset_seconds", "return_start_offset_seconds", "return_end_offset_seconds")]
    flow_start, flow_end, return_start, return_end = bounds
    first_flow = _v1._positions(times, flow_start)
    last_flow = _v1._positions(times, flow_end - BAR_US) + 1
    entry = _v1._positions(times, return_start - BAR_US)
    exit_row = _v1._positions(times, return_end - BAR_US)
    first_past = _v1._positions(times, decisions - PAST_BARS * BAR_US)
    decision_row = _v1._positions(times, decisions - BAR_US)
    require(np.all(last_flow - first_flow == spec["flow_bars"]), "Registered exact flow bar count changed")
    availability = np.column_stack([joint[f"{s}__available_us"].to_numpy().astype(np.float64) for s in STREAMS])
    available_valid = np.isfinite(availability) & (availability >= times[:, None] + BAR_US)
    row_available_valid = available_valid.all(axis=1)
    max_available = availability.max(axis=1)
    feature_available = _max_dependencies(max_available, row_available_valid, first_past, decision_row + 1)
    require(np.isfinite(feature_available).all() and np.all(feature_available <= decisions), "Feature availability after decision or unknown past source")
    quality = np.column_stack([joint[f"{s}__quality"].to_numpy() for s in STREAMS])
    require(all(np.all(quality[a:b] == 0) for a, b in zip(first_past, decision_row + 1)), "Past source quality invalid")
    flow_mature = _max_dependencies(max_available, row_available_valid, first_flow, last_flow)
    return_mature = _max_dependencies(max_available, row_available_valid, entry, exit_row + 1)
    # Every quality observation used by validity, including GAP10, is causal input
    # to knowing that label_valid is true/false, so its availability must mature.
    validity_mature = _max_dependencies(max_available, row_available_valid, first_flow, exit_row + 1)
    mature = np.maximum(np.maximum(flow_mature, return_mature), validity_mature)
    signal_available = decisions if signal_kind == "PAST_ONLY_PREDICTED_FLOW" else flow_mature
    earliest_order = signal_available + contract()["fixed_order_latency_seconds"] * US
    valid = np.asarray([np.all(quality[a:b] == 0) for a, b in zip(first_flow, exit_row + 1)])
    valid &= np.isfinite(mature) & np.isfinite(earliest_order) & (earliest_order <= return_start)
    columns = {"decision_us": decisions, "feature_available_us": feature_available,
        "predicted_signal_available_us": decisions, "signal_available_us": signal_available,
        "earliest_order_us": earliest_order, "earliest_permissible_order_us": earliest_order,
        "delayed_entry_us": return_start, "flow_label_start_us": flow_start,
        "flow_label_end_us": flow_end, "flow_label_mature_us": flow_mature,
        "observed_future_flow_available_us": flow_mature, "return_label_start_us": return_start,
        "return_label_end_us": return_end, "return_label_mature_us": return_mature,
        "validity_mature_us": validity_mature, "label_mature_us": mature,
        "implementation_version": [IMPLEMENTATION_VERSION] * len(decisions),
        "label_variant": [variant] * len(decisions), "flow_return_overlap": [False] * len(decisions),
        "split": [split] * len(decisions), "signal_kind": [signal_kind] * len(decisions),
        "price_proxy_kind": ["CLOSED_BAR_RETURN_PROXY_NOT_EXECUTABLE_FILL"] * len(decisions)}
    for stream in STREAMS:
        buy = joint[f"{stream}__aggressive_buy_notional"].to_numpy().astype(float)
        sell = joint[f"{stream}__aggressive_sell_notional"].to_numpy().astype(float)
        notional_valid = np.isfinite(buy) & np.isfinite(sell) & (buy >= 0) & (sell >= 0)
        # Zeroes here only enable prefix arithmetic. The invalid-window mask below
        # always turns affected labels into NaN; no imputed flow is exposed.
        net = np.r_[0., np.cumsum(np.where(notional_valid, buy - sell, 0))]
        total = np.r_[0., np.cumsum(np.where(notional_valid, buy + sell, 0))]
        bad = np.r_[0, np.cumsum(~notional_valid)]
        window_valid = bad[last_flow] == bad[first_flow]
        flow = (net[last_flow] - net[first_flow]) / (total[last_flow] - total[first_flow] + EPS)
        columns[f"{stream}__future_flow"] = flow
        valid &= window_valid & np.isfinite(flow) & (np.abs(flow) <= 1 + 1e-12)
    for stream in RETURN_STREAMS:
        prices = joint[f"{stream}__close"].to_numpy().astype(float)
        trades = joint[f"{stream}__last_trade_us"].to_numpy().astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            result = prices[exit_row] / prices[entry] - 1
        anchor_valid = (np.isfinite(prices[entry]) & np.isfinite(prices[exit_row]) & (prices[entry] > 0) & (prices[exit_row] > 0)
            & np.isfinite(trades[entry]) & np.isfinite(trades[exit_row])
            & (trades[entry] >= return_start - BAR_US) & (trades[entry] < return_start)
            & (trades[exit_row] >= return_end - BAR_US) & (trades[exit_row] < return_end)
            & (trades[entry] < trades[exit_row]))
        valid &= anchor_valid & np.isfinite(result)
        columns[f"{stream}__subsequent_return_proxy"] = result
        for name, rows, array in (("entry_price_proxy", entry, prices), ("exit_price_proxy", exit_row, prices),
                                  ("entry_price_trade_us", entry, trades), ("exit_price_trade_us", exit_row, trades),
                                  ("entry_price_available_us", entry, joint[f"{stream}__available_us"].to_numpy()),
                                  ("exit_price_available_us", exit_row, joint[f"{stream}__available_us"].to_numpy())):
            columns[f"{stream}__{name}"] = array[rows]
    columns["label_valid"] = valid
    for name in (*FLOW_COLUMNS, *RETURN_COLUMNS):
        columns[name] = np.where(valid, columns[name], np.nan)
    labels = pl.DataFrame(columns)
    assert_nonoverlap(labels)
    return labels


def assert_nonoverlap(labels):
    """Full exported-frame contract check; invalid rows cannot become fit rows."""
    require(len(labels) > 0, "Nonempty label frame required")
    decisions = labels["decision_us"].to_numpy()
    require(np.issubdtype(decisions.dtype, np.integer) and np.all(np.diff(decisions) > 0)
            and np.all(decisions % (60 * US) == 0), "Unique chronological minute decision IDs")
    require(set(labels["implementation_version"].to_list()) == {IMPLEMENTATION_VERSION}, "Active V2 implementation required")
    require(set(labels["split"].to_list()) <= {"TRAIN", "VALIDATION", "OOS_SCREENING", "DEVELOPMENT_DIAGNOSTIC"}, "Invalid split metadata")
    require(set(labels["price_proxy_kind"].to_list()) == {"CLOSED_BAR_RETURN_PROXY_NOT_EXECUTABLE_FILL"}, "No executable fill qualification")
    feature = labels["feature_available_us"].to_numpy()
    require(np.isfinite(feature).all() and np.all(feature <= decisions), "Future feature overlap")
    predicted = labels["predicted_signal_available_us"].to_numpy()
    require(np.array_equal(predicted, decisions), "Past-only prediction availability must equal decision")
    flow_mature, return_mature = labels["flow_label_mature_us"].to_numpy(), labels["return_label_mature_us"].to_numpy()
    validity_mature, mature = labels["validity_mature_us"].to_numpy(), labels["label_mature_us"].to_numpy()
    require(np.array_equal(labels["observed_future_flow_available_us"].to_numpy(), flow_mature, equal_nan=True), "Observed future flow availability differs from actual flow maturity")
    expected_mature = np.maximum(np.maximum(flow_mature, return_mature), validity_mature)
    require(np.array_equal(mature, expected_mature, equal_nan=True), "All validity/value dependencies must enter maturity")
    valid = labels["label_valid"].to_numpy()
    require(valid.dtype == np.bool_, "Explicit boolean label validity required")
    require(np.isfinite(mature[valid]).all(), "Valid label has unknown maturity")
    for name in (*FLOW_COLUMNS, *RETURN_COLUMNS):
        if name in labels.columns:
            values = labels[name].to_numpy()
            require(np.isfinite(values[valid]).all() and np.isnan(values[~valid]).all(), "Invalid labels must remain NaN; valid labels finite")
    require(not labels["flow_return_overlap"].any(), "Signal observation and return label overlap")
    for variant in labels["label_variant"].unique().to_list():
        spec = contract()["labels"].get(variant)
        require(spec is not None, "Unknown registered variant")
        rows = labels["label_variant"].to_numpy() == variant
        for field, offset in (("flow_label_start_us", "flow_start_offset_seconds"), ("flow_label_end_us", "flow_end_offset_seconds"),
                              ("return_label_start_us", "return_start_offset_seconds"), ("return_label_end_us", "return_end_offset_seconds")):
            require(np.array_equal(labels[field].to_numpy()[rows], decisions[rows] + spec[offset] * US), f"Registered variant exact {field} changed")
    flow_end = labels["flow_label_end_us"].to_numpy()
    return_start, return_end = labels["return_label_start_us"].to_numpy(), labels["return_label_end_us"].to_numpy()
    require(np.all(flow_mature[np.isfinite(flow_mature)] >= flow_end[np.isfinite(flow_mature)]), "Flow maturity before observed flow end")
    require(np.all(return_mature[np.isfinite(return_mature)] >= return_end[np.isfinite(return_mature)]), "Return maturity before label end")
    require(np.all(validity_mature[np.isfinite(validity_mature)] >= return_end[np.isfinite(validity_mature)]), "Quality validity maturity before label end")
    require(np.array_equal(labels["delayed_entry_us"].to_numpy(), return_start), "Registered delayed entry changed")
    signal = labels["signal_available_us"].to_numpy()
    kinds = labels["signal_kind"].to_numpy()
    require(set(kinds.tolist()) <= {"PAST_ONLY_PREDICTED_FLOW", "OBSERVED_FUTURE_FLOW_DIAGNOSTIC"}, "Unknown signal kind")
    expected_signal = np.where(kinds == "PAST_ONLY_PREDICTED_FLOW", decisions, flow_mature)
    require(np.array_equal(signal, expected_signal, equal_nan=True), "Signal kind does not match actual observed/predicted availability")
    earliest = labels["earliest_permissible_order_us"].to_numpy()
    require(np.array_equal(earliest, signal + contract()["fixed_order_latency_seconds"] * US, equal_nan=True)
            and np.array_equal(earliest, labels["earliest_order_us"].to_numpy(), equal_nan=True), "Signal latency/order aliases changed")
    require(np.all(earliest[valid] <= return_start[valid]), "Order available after registered delayed entry")
    for stream in RETURN_STREAMS:
        for side, anchor in (("entry", return_start), ("exit", return_end)):
            trade = labels[f"{stream}__{side}_price_trade_us"].to_numpy()
            available = labels[f"{stream}__{side}_price_available_us"].to_numpy()
            price = labels[f"{stream}__{side}_price_proxy"].to_numpy()
            require(np.isfinite(trade[valid]).all() and np.all(trade[valid] >= anchor[valid] - BAR_US)
                    and np.all(trade[valid] < anchor[valid]), "Price trade timestamp outside registered boundary bar")
            require(np.isfinite(available[valid]).all() and np.all(available[valid] >= anchor[valid])
                    and np.all(available[valid] <= return_mature[valid]), "Price anchor availability outside return maturity")
            require(np.isfinite(price[valid]).all() and np.all(price[valid] > 0), "Invalid positive close-price anchor")
        entry = labels[f"{stream}__entry_price_proxy"].to_numpy()
        exit_price = labels[f"{stream}__exit_price_proxy"].to_numpy()
        returns = labels[f"{stream}__subsequent_return_proxy"].to_numpy()
        require(np.array_equal(exit_price[valid] / entry[valid] - 1, returns[valid]), "Return differs from exact registered price anchors")
    return True


def direct_return_labels(labels):
    assert_nonoverlap(labels)
    return labels.select([name for name in labels.columns if "__future_flow" not in name])


def assert_fit_chronology(*, fit_cutoff_us, validation_start_us, embargo_us, max_label_lag_us,
                         fitting_label_mature_us, fitting_decision_us):
    actual = np.asarray(fitting_label_mature_us) - np.asarray(fitting_decision_us)
    require(len(actual) > 0 and np.isfinite(actual).all() and np.all(actual >= 0), "Aligned finite actual fitting label lag")
    require(max_label_lag_us >= int(actual.max()), "Declared lag smaller than actual observed label lag")
    _v1.assert_fit_chronology(fit_cutoff_us=fit_cutoff_us, validation_start_us=validation_start_us,
        embargo_us=embargo_us, max_label_lag_us=max_label_lag_us, fitting_label_mature_us=fitting_label_mature_us)


def assert_split_chronology(labels, *, train_ids, validation_ids, test_ids, fit_cutoff_us,
                            validation_start_us, test_start_us, test_end_us, embargo_us,
                            max_label_lag_us, row_id_column="decision_us"):
    """Verify actual labels/IDs/all splits; no trusted nominal-lag shortcut."""
    assert_nonoverlap(labels)
    require(0 <= embargo_us and validation_start_us < test_start_us < test_end_us, "Ordered explicit split boundaries and embargo")
    ids = labels[row_id_column].to_list()
    require(len(ids) == len(set(ids)), "Unique split row IDs")
    groups = [list(train_ids), list(validation_ids), list(test_ids)]
    require(all(len(group) > 0 and len(group) == len(set(group)) and set(group) <= set(ids) for group in groups), "Explicit nonempty unique known split IDs")
    require(all(not set(groups[a]) & set(groups[b]) for a, b in ((0, 1), (0, 2), (1, 2))), "Split IDs overlap")
    positions = {value: index for index, value in enumerate(ids)}
    indices = [np.asarray([positions[value] for value in group]) for group in groups]
    decisions, maturity = labels["decision_us"].to_numpy(), labels["label_mature_us"].to_numpy()
    used = np.concatenate(indices)
    require(labels["label_valid"].to_numpy()[used].all() and np.isfinite(maturity[used]).all(), "Unknown or invalid label cannot enter fitting/scored split")
    actual_lag = maturity[used] - decisions[used]
    require(np.all(actual_lag >= 0) and max_label_lag_us >= actual_lag.max(), "Declared lag smaller than actual observed maximum across splits")
    train, validation, test = indices
    assert_fit_chronology(fit_cutoff_us=fit_cutoff_us, validation_start_us=validation_start_us,
        embargo_us=embargo_us, max_label_lag_us=max_label_lag_us,
        fitting_label_mature_us=maturity[train], fitting_decision_us=decisions[train])
    require(np.all(decisions[train] < fit_cutoff_us), "Train decision at/after actual fit cutoff")
    require(np.all(decisions[validation] >= validation_start_us)
            and np.all(maturity[validation] < test_start_us - embargo_us), "Validation label maturity must precede test minus embargo")
    require(np.all(decisions[test] >= test_start_us) and np.all(maturity[test] <= test_end_us), "Test label not mature by explicit exclusive test end")
    for rows, split in ((train, "TRAIN"), (validation, "VALIDATION"), (test, "OOS_SCREENING")):
        require(all(labels["split"][int(row)] == split for row in rows), "Row split metadata differs from explicit IDs")
    return {"implementation_version": IMPLEMENTATION_VERSION, "actual_observed_max_label_lag_us": int(actual_lag.max()),
            "registered_max_label_lag_us": int(max_label_lag_us), "fit_cutoff_us": int(fit_cutoff_us),
            "max_train_label_mature_us": int(maturity[train].max()),
            "max_validation_label_mature_us": int(maturity[validation].max()),
            "max_test_label_mature_us": int(maturity[test].max()),
            "counts": {"train": len(train), "validation": len(validation), "test": len(test)}}
