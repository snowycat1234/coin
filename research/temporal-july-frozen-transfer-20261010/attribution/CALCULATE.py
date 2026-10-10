"""Read saved wallets only: exact additive attribution, no policy/wallet execution."""

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

MODEL, VOL, STATIC, CASH = "APRIL_PREFIX_GRU512", "PREFIX_STATIC_VOL", "Static50", "Cash50"
POLICIES = (MODEL, VOL, STATIC, CASH)
ACTIVE, LEGS = (0, 1, 4, 5), ("CASH", "VOL", "CS", "SHORT")
PINNED = {
    "research/temporal-july-frozen-transfer-20261010/results/MANIFEST.json": "861ba1e5880f2cecbbc84c377aa5a9c63bc1e32bf8cffe768936553efe8ea75d",
    "research/temporal-prequential-transfer-20261009/interpretation/READ_FROZEN_PATHS.py": "ad1444797e567cdb8987e3638fffcf74e3517358e7e61a109ae1f38bd3eea7df",
    "research/temporal-prequential-transfer-20261009/interpretation/RESULT.json": "4c82a61e00eec0afefebd4f763fd89f5620cb335673352de794ac0b1ac5b4290",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def close(a, b, tolerance=2e-8):
    np.testing.assert_allclose(a, b, atol=tolerance, rtol=0)


def concentration(values):
    """Largest observed contributions; never delete/replay an interval."""
    values = np.asarray(values)
    positive = values[values > 0]
    order = np.argsort(values)[::-1]
    mass = float(positive.sum())
    result = dict(positive_mass=mass, negative_mass=float(values[values < 0].sum()),
                  positive_intervals=int((values > 0).sum()), negative_intervals=int((values < 0).sum()))
    for n in (3, 5, 10):
        selected = values[order[:n]]
        result[f"largest{n}_contribution_sum"] = float(selected.sum())
        result[f"largest{n}_positive_mass_share"] = float(np.maximum(selected, 0).sum() / mass) if mass else None
    return result


def carry_split(quantity, price):
    """q_t*delta_p = q_(t-1)*delta_p + (q_t-q_(t-1))*delta_p.

    Describes held units and current quantity change at the same observed price
    move. This is not a wallet with trades omitted; funding/costs remain actual.
    """
    prior = np.concatenate((np.zeros_like(quantity[:1]), quantity[:-1]))
    delta = np.diff(price, axis=0)
    if quantity.ndim == 3:
        delta = delta[:, None, :]
    inherited = (prior * delta).sum(-1)
    changed = ((quantity - prior) * delta).sum(-1)
    close(inherited + changed, (quantity * delta).sum(-1))
    return inherited, changed


def price_split(a, b, price):
    """Reuse the prior exact symmetric magnitude/composition/NAV identity."""
    ta, tb = a["targets"], b["targets"]
    ga, gb = np.abs(ta).sum(1), np.abs(tb).sum(1)
    ua = np.divide(ta, ga[:, None], out=np.zeros_like(ta), where=ga[:, None] > 0)
    ub = np.divide(tb, gb[:, None], out=np.zeros_like(tb), where=gb[:, None] > 0)
    returns = np.diff(price, axis=0) / price[:-1]
    na, nb = a["nav"][:-1], b["nav"][:-1]
    average = .5 * (na + nb)
    magnitude = .99 * average * .5 * (ga - gb) * ((ua + ub) * returns).sum(1)
    composition = .99 * average * .5 * (ga + gb) * ((ua - ub) * returns).sum(1)
    capital = .99 * .5 * (na - nb) * ((ta + tb) * returns).sum(1)
    close(magnitude + composition + capital, a["price"] - b["price"])
    return dict(magnitude=float(magnitude.sum()), signed_composition=float(composition.sum()), own_NAV=float(capital.sum()))


def calculate(repo, destination):
    repo, destination = Path(repo), Path(destination)
    if destination.exists():
        raise FileExistsError("Exclusive immutable attribution output required")
    for name, expected in PINNED.items():
        if sha(repo / name) != expected:
            raise ValueError("Pinned source/result changed: " + name)
    root = repo / "research/temporal-july-frozen-transfer-20261010/results"
    manifest = json.loads((root / "MANIFEST.json").read_text())
    for name, entry in manifest["files"].items():
        if sha(root / name) != entry["SHA256"] or (root / name).stat().st_size != entry["bytes"]:
            raise ValueError("Frozen input bytes changed")
    source = repo / "research/temporal-prequential-transfer-20261009/interpretation/READ_FROZEN_PATHS.py"
    spec = importlib.util.spec_from_file_location("_unchanged_saved_wallet_ledger", source)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    result = json.loads((root / "RESULT.json").read_text())
    with np.load(root / "PAIRED_PATHS.npz", allow_pickle=False) as z:
        paths = {k: z[k].copy() for k in z.files}
    with np.load(root / "CURRENT_CONTEXT.npz", allow_pickle=False) as z:
        context = {k: z[k].copy() for k in z.files}
    context["surrogate_prices"], context["surrogate_funding_coeff"] = context["prices"], context["funding_coeff"]
    # Reader schema aliases only; no financial transformation or new targets.
    for record in result["policies"].values():
        record["maximum_drawdown"] = record["maximum_daily_drawdown"]
        record["maximum_allocated_gross"] = record["maximum_allocated_leg_gross"]
        record["maximum_allocated_asset_gross"] = record["maximum_allocated_maximum_asset_gross"]
    close(paths["decision_us"], context["decision_us"], 0)
    if np.any(context["target_available_us"] > context["decision_us"][:, None]) or np.any(context["expert_input_available_us"] > context["decision_us"][:, None]):
        raise ValueError("Causal current context required")
    dates = paths["decision_us"].astype("datetime64[us]").astype("datetime64[D]").astype(str)
    months = np.array([d[:7] for d in dates])
    wallets, summaries, daily, monthly = {}, {}, [], []
    for name in POLICIES:
        wallet = legacy.ledger(name, paths, context, result)
        close(wallet["quantity"], paths[name + "_quantity"], 1e-12)
        close(wallet["quantity"], paths[name + "_boundary_held_quantity"], 1e-12)
        legs = wallet["budget"][:, :, None] * context["expert_targets"]
        legs[-1] = 0.
        leg_quantity = .99 * wallet["nav"][:-1, None, None] * legs / context["prices"][:-1, None, :]
        inherited, changed = carry_split(leg_quantity, context["prices"])
        close(inherited + changed, wallet["leg_price"])
        prior_budget = np.vstack((np.array([1., 0., 0., 0., 0., 0.]), wallet["budget"][:-1]))
        signed_net = wallet["actual_long"] - wallet["actual_short"]
        actual_short_price = np.where(wallet["quantity"] < 0, wallet["price_asset"], 0).sum(1)
        actual_long_price = np.where(wallet["quantity"] >= 0, wallet["price_asset"], 0).sum(1)
        close(actual_short_price + actual_long_price, wallet["price"])
        summary = wallet["summary"]
        # Omit old deletion-style diagnostics; only observed contribution mass.
        summary["net_PnL_concentration"] = concentration(wallet["net"])
        summary.update(mean_active_actual_net=float(signed_net[:-1].mean()), minimum_active_actual_net=float(signed_net[:-1].min()),
                       maximum_active_actual_net=float(signed_net[:-1].max()), actual_long_price_PnL=float(actual_long_price.sum()),
                       actual_short_price_PnL=float(actual_short_price.sum()), request_vs_mapper=legacy.stability(paths[name + "_requests"], wallet["budget"]))
        short_profitable = wallet["leg_price"][:-1, 5] > 0
        short_loss = wallet["leg_price"][:-1, 5] < 0
        summary["SHORT_carried_quantity_price_PnL"] = float(inherited[:, 5].sum())
        summary["SHORT_quantity_change_price_PnL"] = float(changed[:, 5].sum())
        summary["SHORT_profitable_intervals"] = int(short_profitable.sum())
        summary["SHORT_loss_intervals"] = int(short_loss.sum())
        summary["SHORT_profitable_price_mass"] = float(wallet["leg_price"][:-1, 5][short_profitable].sum())
        summary["SHORT_loss_price_mass"] = float(wallet["leg_price"][:-1, 5][short_loss].sum())
        wallets[name], summaries[name] = wallet, summary
        wallet["rows"] = []
        for i, date in enumerate(dates):
            row = dict(policy=name, decision_date=str(date), terminal_paid_close=i == 62, price_PnL=float(wallet["price"][i]),
                       funding=float(wallet["funding"][i]), account_execution_cost=float(wallet["cost"][i]), net_PnL=float(wallet["net"][i]),
                       actual_opening_gross=float(wallet["fill_gross"][i]), actual_opening_net=float(signed_net[i]),
                       actual_opening_long_gross=float(wallet["actual_long"][i]), actual_opening_short_gross=float(wallet["actual_short"][i]),
                       SHORT_prior_budget=float(prior_budget[i, 5]), SHORT_budget_change=float(wallet["budget"][i, 5] - prior_budget[i, 5]),
                       request_minus_prior_mapped_SHORT=float(paths[name + "_requests"][i, 5] - prior_budget[i, 5]),
                       actual_short_position_price_PnL=float(actual_short_price[i]), actual_long_position_price_PnL=float(actual_long_price[i]))
            for key, index in zip(LEGS, ACTIVE, strict=True):
                row.update({"requested_" + key: float(paths[name + "_requests"][i, index]), "mapped_" + key: float(wallet["budget"][i, index]),
                            "leg_price_" + key: float(wallet["leg_price"][i, index]), "leg_funding_" + key: float(wallet["leg_funding"][i, index]),
                            "carried_quantity_price_" + key: float(inherited[i, index]), "quantity_change_price_" + key: float(changed[i, index])})
            for j, symbol in enumerate(context["symbol_order"]):
                row["return_" + symbol] = float(context["prices"][i + 1, j] / context["prices"][i, j] - 1)
                row["signed_target_" + symbol] = float(wallet["targets"][i, j])
            wallet["rows"].append(row)
            daily.append(row)
        for month in np.unique(months):
            mask = months == month
            active = mask & (np.arange(63) < 62)
            monthly.append(dict(policy=name, decision_month=str(month), active_intervals=int(active.sum()), terminal_paid_close=bool(mask[-1]),
                                net_PnL=float(wallet["net"][mask].sum()), price_PnL=float(wallet["price"][mask].sum()),
                                funding=float(wallet["funding"][mask].sum()), account_execution_cost=float(wallet["cost"][mask].sum()),
                                mean_actual_gross=float(wallet["fill_gross"][active].mean()) if active.any() else None,
                                mean_actual_net=float(signed_net[active].mean()) if active.any() else None,
                                expert_price_PnL={k: float(wallet["leg_price"][mask, j].sum()) for k, j in zip(LEGS, ACTIVE, strict=True)},
                                expert_funding={k: float(wallet["leg_funding"][mask, j].sum()) for k, j in zip(LEGS, ACTIVE, strict=True)},
                                mean_requested={k: float(paths[name + "_requests"][active, j].mean()) if active.any() else None for k, j in zip(LEGS, ACTIVE, strict=True)},
                                mean_mapped={k: float(wallet["budget"][active, j].mean()) if active.any() else None for k, j in zip(LEGS, ACTIVE, strict=True)}))
    model = wallets[MODEL]
    comparisons = {}
    for control in (VOL, STATIC):
        other = wallets[control]
        excess = model["net"] - other["net"]
        price, funding, saving = model["price"] - other["price"], model["funding"] - other["funding"], other["cost"] - model["cost"]
        close(excess, price + funding + saving)
        comparisons[control] = dict(net_PnL_excess=float(excess.sum()), price_PnL_excess=float(price.sum()), funding_excess=float(funding.sum()),
                                   account_cost_saving=float(saving.sum()), symmetric_descriptive_price_split=price_split(model, other, context["prices"]),
                                   expert_price_excess={k: float((model["leg_price"] - other["leg_price"])[:, j].sum()) for k, j in zip(LEGS, ACTIVE, strict=True)},
                                   expert_funding_excess={k: float((model["leg_funding"] - other["leg_funding"])[:, j].sum()) for k, j in zip(LEGS, ACTIVE, strict=True)},
                                   concentration=concentration(excess),
                                   top5_excess=[dict(model["rows"][i], control_net_PnL=float(other["net"][i]), excess=float(excess[i])) for i in np.argsort(excess)[::-1][:5]],
                                   monthly=[dict(decision_month=str(month), price_PnL_excess=float(price[months == month].sum()), funding_excess=float(funding[months == month].sum()),
                                                 account_cost_saving=float(saving[months == month].sum()), net_PnL_excess=float(excess[months == month].sum())) for month in np.unique(months)])
    old = json.loads((repo / "research/temporal-prequential-transfer-20261009/interpretation/RESULT.json").read_text())
    earlier = {}
    for fold, record in old["folds"].items():
        earlier[fold] = dict(model_net_PnL=record["model"]["net_PnL"], excess_over_own_Static50=record["PnL_excess"],
                             expert_leg_price_PnL=record["model"]["expert_leg_price_PnL"], mean_actual_gross=record["model"]["actual_fill_gross_active"]["mean"],
                             mean_actual_short_gross=record["model"]["actual_short_gross_active"]["mean"], price_excess_split=record["price_excess_split"],
                             top3_model_contribution=record["model"]["net_PnL_concentration"]["top3_positive_sum"],
                             top5_model_positive_mass_share=record["model"]["net_PnL_concentration"]["top5_share_of_positive_mass"],
                             short_flat_target_budget=record["model"]["flat_expert_targets"]["SHORT"])
    april_path = repo / "research/temporal-april-transfer-20261009/forward/FOLD_20240401/RESULT.json"
    april = json.loads(april_path.read_text())
    earlier["FOLD_20240401"] = dict(model_net_PnL=april["policies"]["FRESH_GRU"]["net_PnL"], excess_over_own_Static50=april["primary_PnL_excess"],
                                       same_checkpoint_as_July2024=True, source_SHA256=sha(april_path))
    summary = dict(schema="READ_ONLY_FIXED_JULY2024_WALLET_ATTRIBUTION_V1", source_commit="90b8fd65d092b52091b3fee7717c0478b265bc6e",
                   input_SHA256=dict(PINNED, **{str(p.relative_to(repo)): sha(p) for p in root.iterdir() if p.is_file()}),
                   wallets=summaries, monthly=monthly, comparisons=comparisons,
                   top5_model_profit_intervals=[model["rows"][i] for i in np.argsort(model["net"])[::-1][:5]],
                   top5_SHORT_leg_profit_intervals=[model["rows"][i] for i in np.argsort(model["leg_price"][:, 5])[::-1][:5]],
                   worst5_SHORT_leg_intervals=[model["rows"][i] for i in np.argsort(model["leg_price"][:, 5])[:5]],
                   previous_documented_folds=earlier, ledger_rows=252, economic_rollouts=0, model_inferences=0, fits=0, optimizer_updates=0, provider_downloads=0, native_wallets=0,
                   semantics=dict(month="decision/start month; July31 interval ends August1; September1 is paid flatten only",
                                  expert_legs="actual mapped budgets and own saved NAV; price/funding additive; net account costs not allocated to legs",
                                  carry="previous held leg units plus actual quantity change; descriptive algebra only, not deleted-trade wallets or timing causation",
                                  requested_vs_mapped="current intents differ from carried L1-ramped budgets; expert target and signed net underlier exposure remain distinct",
                                  concentration="largest observed intervals only; no interval deletion or tradable oracle",
                                  prior_comparison="different frozen prefix snapshots/scalers/starts across2023/January; April and July2024 share exact frozen snapshot; historical development, no statistical robustness claim",
                                  native="daily surrogate only; missing all5 mark bars August12 10:02/10:03; native repair API451 stopped; no fill or native inference"))
    destination.mkdir(parents=True)
    (destination / "RESULT.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    with (destination / "DAILY_ATTRIBUTION.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(daily[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(daily)
    print(json.dumps(dict(comparisons={n: {k: v for k, v in r.items() if k in ("net_PnL_excess", "price_PnL_excess", "funding_excess", "account_cost_saving", "symmetric_descriptive_price_split")} for n, r in comparisons.items()},
                         model_legs=summaries[MODEL]["expert_leg_price_PnL"], model_short_carried=summaries[MODEL]["SHORT_carried_quantity_price_PnL"], model_short_changed=summaries[MODEL]["SHORT_quantity_change_price_PnL"])))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    calculate(args.repo, args.destination)
