"""Development-only oracle flow/impact and fixed horizon mechanism diagnostic.

Reuses the accepted four-stream SequenceDataset and exact five-minute labels.
Future flow is deliberately oracle information, never a deployable input.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import resource
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from scipy.stats import pearsonr, spearmanr
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from quant import resources
from quant.paths import ROOT, STATE
from quant.research_fast.dataset import (
    DAY_US, START, STREAMS, FastSequenceDataset, ShardSpec, day_us, file_sha, protocol,
)
from quant.research_fast.labels import BAR_US, EPS, LABEL_COLUMNS, label_table

HORIZONS = (5, 15, 30, 60)
MAX_LAG_US = (60 * 60 + 10) * 1_000_000
EMBARGO_US = 60 * 60 * 1_000_000
SEED = 20261001


def exclusive_json(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)


class Progress:
    """Publish actual stage counts to the existing local task window."""
    def __init__(self):
        self.pid = os.getpid()
        self.ticks = int(Path(f"/proc/{self.pid}/stat").read_text().split(") ", 1)[1].split()[19])
        self.value = {"pid": self.pid, "start_ticks": self.ticks,
                      "task_id": os.environ.get("COIN_TASK_ID"), "phase": "核对已接受来源",
                      "completed": 0, "total": 120, "unit": "文件", "metrics": {},
                      "detail": "future flow oracle 机制诊断，不是可交易收益"}
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.heartbeat, daemon=True)
        self.thread.start()

    def heartbeat(self):
        while not self.stop.is_set():
            value = {**self.value, "updated_at": time.time()}
            path = STATE / "task-progress" / f"sample-{self.pid}.json"
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False))
            os.replace(temporary, path)
            self.stop.wait(2)

    def update(self, phase, completed, total, unit, **metrics):
        self.value = {**self.value, "phase": phase, "completed": completed,
                      "total": total, "unit": unit, "metrics": metrics}
        print(json.dumps({"phase": phase, "completed": completed, "total": total,
                          "unit": unit, **metrics}, ensure_ascii=False), flush=True)


def horizon_labels(joint, minutes):
    """Thin extension of labels.label_table's flow and trade-open proxy anchors."""
    count = minutes * 60 // 5
    offset = count + 2
    expressions, valid, available = [], [], []
    for stream in STREAMS:
        def col(name, stream=stream):
            return pl.col(f"{stream}__{name}")
        buy, sell = col("aggressive_buy_notional"), col("aggressive_sell_notional")
        net = (buy - sell).rolling_sum(count, min_samples=count).shift(-count)
        total = (buy + sell).rolling_sum(count, min_samples=count).shift(-count)
        entry, exit_price = col("open").shift(-2), col("open").shift(-offset)
        entry_us, exit_us = col("first_trade_us").shift(-2), col("first_trade_us").shift(-offset)
        entry_anchor = pl.col("timestamp") + 2 * BAR_US
        exit_anchor = pl.col("timestamp") + offset * BAR_US
        wait_valid = entry_us.is_between(entry_anchor, entry_anchor + 2_000_000) & (
            exit_us.is_between(exit_anchor, exit_anchor + 2_000_000))
        expressions.extend([
            (net / (total + EPS)).alias(f"{stream}__flow_{minutes}m"),
            pl.when(wait_valid & (entry > 0) & (exit_price > 0)).then(exit_price / entry - 1)
            .otherwise(None).alias(f"{stream}__return_{minutes}m_proxy"),
            entry_us.alias(f"{stream}__entry_{minutes}m_us"),
            exit_us.alias(f"{stream}__exit_{minutes}m_us"),
        ])
        valid.append(col("quality").cast(pl.Int64).rolling_sum(offset, min_samples=offset)
                     .shift(-offset) == 0)
        available.append(col("available_us").shift(-offset))
    names = [f"{s}__{task}_{minutes}m" + ("_proxy" if task == "return" else "")
             for s in STREAMS for task in ("flow", "return")]
    result = joint.select((pl.col("timestamp") + BAR_US).alias("decision_us"),
                          pl.max_horizontal(available).alias(f"mature_{minutes}m_us"),
                          *expressions, pl.all_horizontal(valid).fill_null(False)
                          .alias(f"quality_{minutes}m_valid"))
    return result.with_columns((pl.all_horizontal([
        pl.col(n).is_not_null() & pl.col(n).is_finite() for n in names])
        & pl.col(f"quality_{minutes}m_valid")).alias(f"valid_{minutes}m"))


def current_state(joint):
    """Only already-closed bars: preceding 60m RV/liquidity and contemporaneous basis."""
    expressions = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        spot, perp = f"spot_{symbol}", f"perp_{symbol}"
        ret = pl.col(f"{spot}__return_5s")
        expressions.extend([
            (ret.fill_null(0).pow(2).rolling_sum(720, min_samples=720) + EPS).log()
            .alias(f"{symbol}__past_logrv"),
            ret.is_not_null().cast(pl.Int32).rolling_sum(720, min_samples=720)
            .alias(f"{symbol}__past_valid_return_bars"),
            pl.col(f"{spot}__quote_notional").rolling_sum(720, min_samples=720).log1p()
            .alias(f"{symbol}__past_log_liquidity"),
            (pl.col(f"{perp}__close") / pl.col(f"{spot}__close") - 1)
            .alias(f"{symbol}__past_basis"),
        ])
    return joint.select((pl.col("timestamp") + BAR_US).alias("decision_us"), *expressions)


def compare_five_minute(original, extended):
    count = 0
    columns = []
    for stream in ("spot_BTCUSDT", "spot_ETHUSDT"):
        for old, new in ((f"{stream}__flow_5m", f"{stream}__flow_5m"),
                         (f"{stream}__return_5m_proxy", f"{stream}__return_5m_proxy"),
                         (f"{stream}__entry_trade_us", f"{stream}__entry_5m_us"),
                         (f"{stream}__exit_trade_us", f"{stream}__exit_5m_us")):
            left, right = original[old].to_numpy(), extended[new].to_numpy()
            if not np.array_equal(left, right, equal_nan=True):
                raise ValueError(f"Original five-minute label differs: {old}")
            count += len(left)
            columns.append(old)
    if not np.array_equal(original["label_available_us"].to_numpy(),
                          extended["mature_5m_us"].to_numpy(), equal_nan=True):
        raise ValueError("Original five-minute maturity differs")
    return count, columns


def correlations(flow, returns):
    if len(flow) < 3 or np.ptp(flow) == 0 or np.ptp(returns) == 0:
        return {"n": len(flow), "pearson": None, "spearman": None, "sign_accuracy": None}
    return {"n": len(flow), "pearson": float(pearsonr(flow, returns).statistic),
            "spearman": float(spearmanr(flow, returns).statistic),
            "sign_accuracy": float(np.mean(np.sign(flow) == np.sign(returns))),
            "signed_return_mean_bps": float(np.mean(np.sign(flow) * returns) * 10_000)}


def daily_correlations(decisions, flow, returns):
    result = []
    for day in np.unique(decisions // DAY_US):
        mask = decisions // DAY_US == day
        result.append({"utc_day": datetime.fromtimestamp(int(day * 86400), UTC).date().isoformat(),
                       **correlations(flow[mask], returns[mask])})
    return result


def oracle_trade_diagnostic(frame, prediction, symbol, minutes):
    """Fixed 35bps, greedy nonoverlap; equal-notional bps, not portfolio PnL/APR."""
    stream = f"spot_{symbol}"
    enter = frame[f"{stream}__entry_{minutes}m_us"].to_numpy()
    leave = frame[f"{stream}__exit_{minutes}m_us"].to_numpy()
    returns = frame[f"{stream}__return_{minutes}m_proxy"].to_numpy()
    selected, previous_exit = [], -1
    for index in range(len(frame)):
        if prediction[index] >= 0.0035 and enter[index] >= previous_exit:
            selected.append(index)
            previous_exit = int(leave[index])
    edge = returns[selected] * 10_000
    return {"status": "ORACLE_ONLY_NOT_TRADING_OR_NET_APR", "threshold_bps": 35,
            "roundtrips": len(selected), "same_symbol_overlap": False,
            "gross_mean_bps": float(edge.mean()) if len(edge) else None,
            "gross_median_bps": float(np.median(edge)) if len(edge) else None,
            "break_even_equal_notional_roundtrip_cost_bps": float(edge.mean()) if len(edge) else None,
            "positive_gross_fraction": float(np.mean(edge > 0)) if len(edge) else None,
            "gross_sum_equal_notional_bps_not_nav": float(edge.sum()),
            "cost_sensitivity": [{"roundtrip_fee_bps": 20, "extra_slippage_bps": 8,
                                  "spread_bps": spread, "total_bps": 28 + spread,
                                  "oracle_net_mean_bps_not_apr": float(edge.mean() - 28 - spread)
                                  if len(edge) else None} for spread in (2, 4, 8)],
            "portfolio_net_apr": None,
            "warning": "Future-flow conditioned selection and future-valid endpoints; trade-open proxies lack BBO/impact. No executable result."}


def run(args, progress):
    started = time.monotonic()
    directory = args.run_dir.resolve()
    if not directory.is_relative_to(STATE.resolve()) or directory.exists():
        raise ValueError("New exclusive native STATE run directory required")
    directory.mkdir()
    qa_path = ROOT / "reports/fast_research/FR_HISTORY_FIRST_30D_QA_20261002_V1.json"
    qa = json.loads(qa_path.read_text())
    if qa["status"] != "FR_HISTORY_FIRST_30D_INDEPENDENT_DIAGNOSTIC_QA_PASS":
        raise ValueError("Accepted 30-day source QA required")
    for key, value in qa["source_hashes"].items():
        if file_sha(ROOT / key) != value:
            raise ValueError("Accepted original source code changed")
    sources, manifests = [], {}
    for offset, item in enumerate(qa["daily_results"]):
        path = ROOT / "data/research_fast/trade_flow_5s_v2" / item["market"] / item["symbol"] / (
            item["day"] + ".manifest.json")
        if item["status"] != "PASS" or file_sha(path) != item["manifest_sha256"]:
            raise ValueError("Accepted manifest changed")
        shard = ShardSpec.from_manifest(path)
        if shard.sha256 != item["parquet_sha256"]:
            raise ValueError("Accepted parquet binding changed")
        sources.append(shard)
        manifests[str(path.relative_to(ROOT))] = item["manifest_sha256"]
        progress.update("核对已接受来源", offset + 1, 120, "文件")
    dataset = FastSequenceDataset(sources, mode="smoke")
    if len(dataset.complete_days) != 30:
        raise ValueError("Exactly first thirty complete common days required")
    source_hashes = {str(Path(__file__).resolve().relative_to(ROOT)): file_sha(Path(__file__)),
                     "src/quant/research_fast/dataset.py": file_sha(ROOT / "src/quant/research_fast/dataset.py"),
                     "src/quant/research_fast/labels.py": file_sha(ROOT / "src/quant/research_fast/labels.py"),
                     "protocols/fast_research_v6.json": file_sha(ROOT / "protocols/fast_research_v6.json")}
    config = next(c for c in protocol()["configs"] if c["id"] == "XGB-S")
    binding = {"status": "PREREGISTERED_DEVELOPMENT_ORACLE_MECHANISM_DIAGNOSTIC",
               "horizons_minutes": HORIZONS, "all_horizons_shared_endpoint_set": True,
               "dataset_sha256": dataset.contract_sha256, "source_hashes": source_hashes,
               "accepted_30d_qa_sha256": file_sha(qa_path), "manifests": manifests,
               "initial_train_days": 12, "validation_days": 2, "test_days": 7,
               "maximum_label_lag_seconds": 3610, "embargo_seconds": 3600,
               "oracle_impact_config": config, "seed": SEED, "search_budget": "one fixed XGB-S oracle-impact configuration across four horizons/two Spot instruments",
               "model_inputs": "four true FUTURE flows + current 60m Spot RV/liquidity + current Spot/Perp basis",
               "validation_used_for_selection": False,
               "split_classification": "DEVELOPMENT_DIAGNOSTIC; rolling00 already inspected, NOT unseen OOS",
               "no_net_apr_or_candidate_qualification": True}
    exclusive_json(directory / "RUN_BINDING.json", binding)
    first, last = day_us(START), day_us(START + timedelta(days=30))
    chunks, before, total_comparisons, compared_columns = [], 0, 0, []
    for offset in range(30):
        lower = max(first, first + offset * DAY_US - 3600_000_000)
        upper = min(last, first + (offset + 1) * DAY_US + MAX_LAG_US)
        joint = dataset.joint_rows(lower, upper)
        original = label_table(joint)
        five = horizon_labels(joint, 5)
        compared, compared_columns = compare_five_minute(original, five)
        total_comparisons += compared
        labels = five
        for minutes in HORIZONS[1:]:
            labels = labels.join(horizon_labels(joint, minutes), on="decision_us", validate="1:1")
        labels = labels.join(current_state(joint), on="decision_us", validate="1:1").with_columns(
            original["label_valid"].alias("original_5m_all_aux_valid"))
        candidates = labels.filter((pl.col("decision_us") % 60_000_000 == 0)
                                   & pl.col("decision_us").is_between(first + offset * DAY_US,
                                                                      first + (offset + 1) * DAY_US, closed="left")
                                   & (pl.col("decision_us") >= first + 3600_000_000))
        before += candidates.height
        conditions = [pl.col(f"valid_{h}m") for h in HORIZONS] + [pl.col("original_5m_all_aux_valid")]
        for symbol in ("BTCUSDT", "ETHUSDT"):
            conditions.extend([pl.col(f"{symbol}__{n}").is_finite() for n in
                               ("past_logrv", "past_log_liquidity", "past_basis")])
            conditions.append(pl.col(f"{symbol}__past_valid_return_bars") >= 684)
        selected = candidates.filter(pl.all_horizontal(conditions))
        chunks.append(selected)
        progress.update("构建四周期共同标签 / 校核原 5m", offset + 1, 30, "UTC 日",
                        本日样本=selected.height, 累计样本=sum(c.height for c in chunks))
    frame = pl.concat(chunks).sort("decision_us")
    decisions = frame["decision_us"].to_numpy()
    if np.any(np.diff(decisions) <= 0):
        raise ValueError("Decision IDs must be unique and ordered")
    validation_start, test_start, test_end = first + 12 * DAY_US, first + 14 * DAY_US, first + 21 * DAY_US
    train_mask = (decisions < validation_start - EMBARGO_US - MAX_LAG_US)
    validation_mask = (decisions >= validation_start) & (decisions + MAX_LAG_US <= test_start - EMBARGO_US)
    test_mask = (decisions >= test_start) & (decisions + MAX_LAG_US <= test_end)
    if not all(np.any(m) for m in (train_mask, validation_mask, test_mask)):
        raise ValueError("All common chronological splits required")
    frame.write_parquet(directory / "oracle_common_endpoints.parquet")
    exclusive_json(directory / "LABEL_CHECK.json", {"five_minute_exact_match": True,
        "original_columns": compared_columns, "value_pairs_compared_including_overlap": total_comparisons,
        "all_horizons_common_candidates": before, "all_horizons_common_valid_endpoints": len(frame),
        "excluded_endpoints": before - len(frame), "common_selection_is_future_conditional": True,
        "counts": {"train": int(train_mask.sum()), "validation": int(validation_mask.sum()), "test": int(test_mask.sum())},
        "max_train_label_available_us": int(decisions[train_mask].max() + MAX_LAG_US),
        "train_label_deadline_us": validation_start - EMBARGO_US,
        "max_validation_label_available_us": int(decisions[validation_mask].max() + MAX_LAG_US),
        "validation_label_deadline_us": test_start - EMBARGO_US,
        "max_test_label_available_us": int(decisions[test_mask].max() + MAX_LAG_US),
        "test_label_deadline_us": test_end,
        "past_state_last_availability_equals_decision": True})
    results, models, cuts = [], [], {}
    test = frame.filter(pl.Series(test_mask))
    test_decisions = decisions[test_mask]
    for model_index, (minutes, symbol) in enumerate((h, s) for h in HORIZONS for s in ("BTCUSDT", "ETHUSDT")):
        stream = f"spot_{symbol}"
        returns = frame[f"{stream}__return_{minutes}m_proxy"].to_numpy()
        flows = {s: frame[f"{s}__flow_{minutes}m"].to_numpy() for s in STREAMS}
        state_names = [f"{symbol}__{n}" for n in ("past_logrv", "past_log_liquidity", "past_basis")]
        state = frame.select(state_names).to_numpy()
        conditions = []
        for state_index, name in enumerate(state_names):
            values = np.abs(state[:, state_index]) if name.endswith("basis") else state[:, state_index]
            thresholds = np.quantile(values[train_mask], [1 / 3, 2 / 3])
            cuts[name] = thresholds.tolist()
            bins = np.searchsorted(thresholds, values, side="right")
            for bucket in range(3):
                mask = test_mask & (bins == bucket)
                conditions.append({"state": name, "training_tercile": bucket,
                    "training_only_thresholds": thresholds.tolist(),
                    **correlations(flows[stream][mask], returns[mask]),
                    "mean_return_bps": float(returns[mask].mean() * 10000) if mask.any() else None})
        associations = [{"oracle_flow_stream": s, **correlations(flow[test_mask], returns[test_mask]),
                         "daily": daily_correlations(test_decisions, flow[test_mask], returns[test_mask])}
                        for s, flow in flows.items()]
        results.append({"horizon_minutes": minutes, "spot_target": symbol,
                        "oracle_associations": associations, "conditional_impact": conditions})
        x = np.column_stack([*(flows[s] for s in STREAMS), state])
        y_scaler = StandardScaler().fit(returns[train_mask].reshape(-1, 1))
        settings = {k: v for k, v in config.items() if k not in ("id", "kind")}
        progress.update("Oracle impact 拟合 / 固定 XGB-S", model_index, 8, "模型", 当前周期分钟=minutes, 当前资产=symbol)
        model = XGBRegressor(**settings, random_state=SEED)
        fit_start = time.monotonic()
        model.fit(x[train_mask], y_scaler.transform(returns[train_mask].reshape(-1, 1)).ravel())
        prediction = y_scaler.inverse_transform(model.predict(x[test_mask]).reshape(-1, 1)).ravel()
        validation_prediction = y_scaler.inverse_transform(model.predict(x[validation_mask]).reshape(-1, 1)).ravel()
        model_path = directory / f"oracle-{symbol}-{minutes}m.json"
        model.save_model(model_path)
        np.save(directory / f"oracle-{symbol}-{minutes}m-predictions.npy", prediction, allow_pickle=False)
        models.append({"horizon_minutes": minutes, "spot_target": symbol,
            "config": "fixed XGB-S; future-flow oracle only", "fit_seconds": time.monotonic() - fit_start,
            "validation_association_diagnostic_only": correlations(validation_prediction, returns[validation_mask]),
            "development_test_association": correlations(prediction, returns[test_mask]),
            "daily_development_test_association": daily_correlations(test_decisions, prediction, returns[test_mask]),
            "gross_edge_diagnostic": oracle_trade_diagnostic(test, prediction, symbol, minutes),
            "model_sha256": file_sha(model_path), "future_flow_input_is_explicit_oracle": True,
            "training_only_target_mean": float(y_scaler.mean_[0]), "training_only_target_scale": float(y_scaler.scale_[0]),
            "feature_gain_importance": dict(zip([f"FUTURE_{s}_flow" for s in STREAMS] + state_names,
                                                map(float, model.feature_importances_)))})
        progress.update("Oracle impact 拟合 / 固定 XGB-S", model_index + 1, 8, "模型", 当前周期分钟=minutes, 当前资产=symbol)
    output = {"status": "DEVELOPMENT_ORACLE_HORIZON_MECHANISM_DIAGNOSTIC_COMPLETE",
              "created_utc": datetime.now(UTC).isoformat(), "run_dir": str(directory),
              "binding": binding, "binding_sha256": file_sha(directory / "RUN_BINDING.json"),
              "source_snapshot": "120 original immutable daily files; source parquet SHA independently checked by FastSequenceDataset",
              "label_check": json.loads((directory / "LABEL_CHECK.json").read_text()),
              "train_only_regime_cutpoints": cuts, "oracle_flow_return_associations": results,
              "oracle_impact_models": models, "elapsed_seconds": time.monotonic() - started,
              "process_peak_ram_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
              "shared_cgroup": resources.status(), "gpu_hours": 0,
              "source_sha256_after": {k: file_sha(ROOT / k) for k in source_hashes},
              "artifacts": {p.name: file_sha(p) for p in directory.iterdir() if p.is_file()},
              "claim_limits": ["Already-viewed July development history, not unseen OOS or locked test.",
                  "True future flow overlaps the return holding interval: association need not imply causal/predictable impact.",
                  "Oracle XGB is an empirical information diagnostic, not a mathematical maximum or deployable trading ceiling.",
                  "Future-valid synchronized sample selection is conditional and not an implementable inference filter.",
                  "No BBO, queue, funding, borrow or market-impact evidence. No net geometric APR claim.",
                  "Overlapping minute outcomes: correlation p-values deliberately not reported; daily persistence descriptive only.",
                  "The 95% past return availability floor and train-only terciles are fixed before this run; no posthoc threshold tuning."]}
    if output["source_sha256_after"] != source_hashes:
        raise ValueError("Sources changed during this run")
    exclusive_json(args.output, output)
    exclusive_json(directory / "COMPLETE.json", {"status": output["status"], "report": str(args.output),
                                                 "report_sha256": file_sha(args.output)})
    progress.update("Oracle / 四周期诊断完成", 8, 8, "模型", 共同测试样本=int(test_mask.sum()))
    print(json.dumps({"status": output["status"], "output": str(args.output), "models": len(models),
                      "test_endpoints": int(test_mask.sum())}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.output.is_relative_to((ROOT / "reports/fast_research").resolve()) or args.output.exists():
        raise ValueError("New exclusive small research report required")
    resources.status()
    progress = Progress()
    try:
        with (STATE / ".fr-first-round.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run(args, progress)
    finally:
        progress.stop.set()
        progress.thread.join(timeout=3)


if __name__ == "__main__":
    main()
