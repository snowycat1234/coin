"""Read-only saved-2025 mix arithmetic; never rebuild or score an account.

Uses only published targets/proofs, original p0/p1/funding, and saved rows.
No signal builder, risk.scale, economic kernel, provider, fitting or RNG runs.
Default prints the report; --write-new creates new explanation files only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = ROOT.parent / "inputs"
ARMS = ("CS", "SMA200", "STATIC50")
COST = .00135
CAPITAL = 10000.


def read_json(path):
    return json.loads(path.read_text())


def sum_all(x):
    return float(math.fsum(np.asarray(x, float).ravel()))


def date(us):
    return datetime.fromtimestamp(int(us) / 1e6, timezone.utc).date().isoformat()


def build_report():
    result_path = HERE / "results/RESULTS.json"
    results = read_json(result_path)
    manifest = read_json(HERE / "results/OUTPUTS_MANIFEST.json")
    sources = {}

    def verify(path, expected):
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Saved source identity mismatch: {path}")
        sources[str(path.relative_to(ROOT.parent))] = actual

    verify(result_path, manifest["files"]["RESULTS.json"])
    ipath = INPUTS / "Y2025.npz"
    tpath = HERE / "targets/Y2025.npz"
    ppath = HERE / "targets/Y2025_PROOF.json"
    verify(ipath, results["input_hashes"]["2025"])
    for path in (tpath, ppath, HERE / "core.py",
                 ROOT / "research/portfolio-risk-budget-20261012/risk_budget.py"):
        verify(path, results["code_target_hashes"][str(path.relative_to(ROOT))])
    with np.load(ipath, allow_pickle=False) as value:
        inputs = {key: value[key] for key in value.files}
    with np.load(tpath, allow_pickle=False) as value:
        targets = {key: value[key] for key in value.files}
    proof = read_json(ppath)
    days = targets["decision_us"]
    assert len(days) == len(proof) == 365
    assert np.array_equal(days, inputs["decision_us"])
    assert date(days[0]) == "2025-01-01" and date(days[-1]) == "2025-12-31"
    assert np.all(np.diff(days) == 86400_000000)
    assert np.all(targets["source_status"] == "READY")
    assert np.array_equal(targets["symbol_order"], inputs["symbol_order"])
    metrics = {arm: results["years"]["2025"]["arms"][arm]["metrics"] for arm in ARMS}
    rows = {}
    for arm in ARMS:
        published = results["years"]["2025"]["arms"][arm]
        path = HERE / "results" / published["quantity_rows_file"]
        verify(path, published["quantity_rows_SHA256"])
        assert manifest["files"][path.name] == published["quantity_rows_SHA256"]
        rows[arm] = read_json(path)
        assert np.array_equal([row["decision_us"] for row in rows[arm]], days)
        assert len(rows[arm]) == 365
    factors = {arm: np.array([p["arms"][arm]["factor"] for p in proof]) for arm in ARMS}
    assert all(np.all(f > 0) for f in factors.values())
    audits = {}
    for arm in ARMS:
        q = np.array([r["held_quantity"] for r in rows[arm]])
        nav = np.array([r["nav_before"] for r in rows[arm]])
        target_error = float(np.max(abs(q * inputs["p0"] - nav[:, None] * targets[arm])))
        scale_error = float(np.max(abs(targets[arm] - factors[arm][:, None] * targets["raw_" + arm])))
        audits[arm] = dict(saved_quantity_target_identity_max_error_USDT=target_error,
                           saved_scale_identity_max_weight_error=scale_error)
        assert target_error < 1e-8 and scale_error < 1e-12
    assert np.array_equal(targets["raw_STATIC50"], .5 * targets["raw_CS"] + .5 * targets["raw_SMA200"])

    coeff = {arm: .5 * factors["STATIC50"] / factors[arm] for arm in ARMS[:2]}
    summaries = {}
    for arm, a in coeff.items():
        summaries[arm] = dict(
            min=float(a.min()), p10=float(np.quantile(a, .1)),
            median=float(np.median(a)), mean=float(a.mean()),
            p90=float(np.quantile(a, .9)), max=float(a.max()),
            below_half_days=int(np.sum(a < .5 - 1e-12)),
            equal_half_days=int(np.sum(abs(a - .5) <= 1e-12)),
            above_half_days=int(np.sum(a > .5 + 1e-12)),
            min_date=date(days[int(np.argmin(a))]), max_date=date(days[int(np.argmax(a))]))
    w_identity = sum(coeff[arm][:, None] * targets[arm] for arm in ARMS[:2])
    audits["mix_weight_identity_max_error"] = float(np.max(abs(w_identity - targets["STATIC50"])))
    nav_m = np.array([r["nav_before"] for r in rows["STATIC50"]])
    p0, p1, funding = (inputs[k] for k in ("p0", "p1", "funding_per_unit"))
    q_m = np.array([r["held_quantity"] for r in rows["STATIC50"]])
    virtual = {arm: nav_m[:, None] * .5 * factors["STATIC50"][:, None]
               * targets["raw_" + arm] / p0 for arm in ARMS[:2]}
    q_identity = virtual["CS"] + virtual["SMA200"]
    audits["mix_virtual_quantity_identity_max_error_USDT"] = float(np.max(abs(q_identity - q_m) * p0))
    attribution = {}
    references = {}

    def price_cash(q):
        return dict(price_pnl_USDT=sum_all(q * (p1 - p0)),
                    funding_cash_USDT=sum_all(-q * funding))

    def endpoint_expense(q):
        previous = np.vstack((np.zeros(5), q[:-1]))
        return sum_all(abs(q - previous) * p0) * COST + sum_all(abs(q[-1]) * p1[-1]) * COST

    for arm, q in virtual.items():
        attribution[arm] = price_cash(q)
        reference_q = .5 * nav_m[:, None] * targets[arm] / p0
        ref = price_cash(reference_q)
        delta = price_cash(q - reference_q)
        references[arm] = dict(half_already_sized_target_at_actual_mix_NAV=ref,
                               actual_virtual_component=attribution[arm],
                               scaling_difference_at_same_NAV=delta)
    actual = metrics["STATIC50"]
    price_sum = sum(v["price_pnl_USDT"] for v in attribution.values())
    funding_sum = sum(v["funding_cash_USDT"] for v in attribution.values())
    net = price_sum + funding_sum - actual["trading_cost"]
    audits["price_attribution_reconciliation_error_USDT"] = abs(price_sum - actual["price_pnl"])
    audits["funding_attribution_reconciliation_error_USDT"] = abs(funding_sum - actual["funding_cash"])
    audits["net_reconciliation_error_USDT"] = abs(net - actual["net_USDT"])
    assert max(audits[key] for key in audits if key != "CS" and key != "SMA200" and key != "STATIC50") < 1e-8
    average = {key: .5 * (metrics["CS"][key] + metrics["SMA200"][key])
               for key in ("price_pnl", "funding_cash", "trading_cost", "net_USDT", "cumulative_net_return")}
    gap = dict(price_pnl_USDT=actual["price_pnl"] - average["price_pnl"],
               funding_cash_USDT=actual["funding_cash"] - average["funding_cash"],
               expense_contribution_USDT=average["trading_cost"] - actual["trading_cost"],
               net_USDT=actual["net_USDT"] - average["net_USDT"])
    assert abs(sum(gap[k] for k in ("price_pnl_USDT", "funding_cash_USDT", "expense_contribution_USDT")) - gap["net_USDT"]) < 1e-8
    ret = {arm: np.array([r["daily_return"] for r in rows[arm]]) for arm in ARMS}
    benchmark = float(np.prod(1 + .5 * ret["CS"] + .5 * ret["SMA200"]) - 1)
    first = dict(date=date(days[0]), raw_CS=targets["raw_CS"][0].tolist(),
                 raw_SMA200=targets["raw_SMA200"][0].tolist(),
                 scale_factors={arm: float(f[0]) for arm, f in factors.items()},
                 effective_coefficients={arm: float(a[0]) for arm, a in coeff.items()},
                 already_sized_targets={arm: targets[arm][0].tolist() for arm in ARMS},
                 half_already_sized_reference_weight=(.5 * targets["CS"][0] + .5 * targets["SMA200"][0]).tolist())
    virtual_cost = sum(endpoint_expense(q) for q in virtual.values())
    return dict(
        year=2025, days=365, units="USDT; percentage-point contribution = USDT / 10000 * 100",
        method="Read-only algebra on original saved targets, scale proof, quantity rows and market intervals; no account replay or newly scored strategy",
        actual_definition="w_STATIC50 = f_mix * (0.5*raw_CS + 0.5*raw_SMA200)",
        effective_coefficients_identity="w_STATIC50 = (0.5*f_mix/f_CS)*w_CS + (0.5*f_mix/f_SMA200)*w_SMA200",
        coefficient_caveat="These are time-varying virtual coefficients on already-sized target weights, not capital shares, probabilities, or independent executable wallets; they need not sum to one.",
        coefficient_summary=summaries, first_date_example=first,
        actual_metrics=actual, standalone_metrics={arm: metrics[arm] for arm in ARMS[:2]},
        exact_price_funding_attribution_at_actual_STATIC_NAV_and_p0=attribution,
        actual_reconciliation=dict(price_USDT=price_sum, funding_cash_USDT=funding_sum,
            rebalance_expense_USDT=actual["trading_cost"] - actual["terminal_cost_proxy_USDT"],
            terminal_expense_USDT=actual["terminal_cost_proxy_USDT"],
            total_expense_USDT=actual["trading_cost"], net_USDT=net,
            price_minus_expense_before_funding_USDT=price_sum - actual["trading_cost"],
            price_plus_funding_before_expense_USDT=price_sum + funding_sum),
        half_initial_separate_capital_linear_scaling_benchmark=average,
        half_initial_separate_capital_caveat="Each original wallet, quantity, NAV and proportional cost is hypothetically scaled by one half, with no sleeve reallocation and no cross-wallet netting. Arithmetic is exact under the original linear quantity/cost model; no new account, live fill, minQty or capital/capacity validation is claimed.",
        actual_minus_half_initial_separate_wallets=gap,
        daily_50_50_saved_return_descriptive_benchmark=dict(
            formula="prod_t(1 + 0.5*r_CS,t + 0.5*r_SMA200,t) - 1",
            cumulative_return=benchmark, final_10000_capital_arithmetic=CAPITAL * (1 + benchmark),
            caveat="Descriptive combination of saved standalone daily net returns, including saved terminal charges. Not an executed or validated 50/50 mix; additional allocation/reallocation turnover, netting, and account-path cost changes have not been modeled."),
        same_actual_NAV_half_already_sized_reference=references,
        reference_caveat="Same-date algebraic price/funding terms at actual STATIC50 NAV and p0 only. No NAV recursion or account scoring is run. The allocation of sizing vs NAV-path differences depends on the chosen reference and is descriptive, not a causal intervention.",
        same_virtual_endpoints_netting_expense_identity=dict(
            sum_virtual_component_endpoint_expenses_USDT=virtual_cost,
            actual_netted_endpoint_expense_USDT=endpoint_expense(q_m),
            algebraic_difference_USDT=virtual_cost - endpoint_expense(q_m),
            caveat="Triangle-inequality endpoint diagnostic on the virtual component decomposition only, not a separately replayed two-wallet alternative or a certified attainable trading-cost saving. Opposite-sign inventory netting lowers proportional endpoint expense for these same quantities."),
        limitations=["Known development year and conditional daily quantity proxy, not pristine out-of-sample evidence.",
                     "No providers, holdout, new target generation, fitting, search or account replay.",
                     "Cancellation alone cannot break additive price/funding PnL for fixed weights; the mixed raw intent is separately and nonlinearly risk-sized.",
                     "Common nominal risk budget does not establish equal realized risk."],
        source_SHA256=sources, arithmetic_audit=audits)


def render(report):
    c = report["coefficient_summary"]
    a = report["exact_price_funding_attribution_at_actual_STATIC_NAV_and_p0"]
    x = report["actual_reconciliation"]
    h = report["half_initial_separate_capital_linear_scaling_benchmark"]
    b = report["daily_50_50_saved_return_descriptive_benchmark"]
    g = report["actual_minus_half_initial_separate_wallets"]
    ref = report["same_actual_NAV_half_already_sized_reference"]
    text = f"""# 为什么 STATIC50 不是 CS/SMA 年收益的平均值

2025 的 STATIC50 是“原始信号各一半，再对混合信号统一做风险缩放”，不是“各投一半资金到已完成风险管理的 CS/SMA 钱包”。后者在原模型线性缩放假设下是 **8.673582%**；当前 STATIC50 实际是 **2.724420%**。本报告只读保存结果，无账户重跑、目标再生成或新实验。

## 三种“50/50”是不同定义

1. **初始各 50% 资金、两个独立钱包、不调拨资金**：各用 5,000 USDT 执行原策略，其数量与比例费用也各缩半。总净收益是 {h['net_USDT']:.8f} USDT，即 {h['cumulative_net_return'] * 100:.8f}%，等于原两个钱包年收益的算术均值。只是在原线性成本/数量模型下的算术基准，未验证实际成交、最小数量或容量。
2. **每日重新分配到 50/50 已管理策略**：保存的每日净收益可给出描述性复利 prod(1 + 0.5*r_CS + 0.5*r_SMA) − 1 = {b['cumulative_return'] * 100:.8f}%。这不是执行过或验证过的组合账户，未模拟额外资金调拨换仓、净额成交及账户路径费用变化。
3. **当前 STATIC50**：先将 raw_CS 与 raw_SMA 各乘 0.5 相加，再用混合组合自己的 30 日协方差风险估计缩放，并受总敞口 60%/单资产 30% 上限约束。它不是前两种的收益基准。

## 准确的每日权重关系

w_CS = f_CS × raw_CS，w_SMA = f_SMA × raw_SMA。

w_STATIC50 = f_mix × (0.5 × raw_CS + 0.5 × raw_SMA)
          = a_t × w_CS + b_t × w_SMA

a_t = 0.5 × f_mix/f_CS；b_t = 0.5 × f_mix/f_SMA。

这些是已缩放目标权重上的虚拟系数，不是资金比例，且不要求相加等于 1。共同风险政策中 f = min(10%/估计年波动率, 敞口上限允许系数)，取决于组合，因此不能把风险缩放与信号相加交换顺序。

| 每日系数 | 最小 | 中位数 | 平均 | 最大 | 小于 0.5 天数 | 大于 0.5 天数 |
|---|---:|---:|---:|---:|---:|---:|
| CS 的 a_t | {c['CS']['min']:.6f} | {c['CS']['median']:.6f} | {c['CS']['mean']:.6f} | {c['CS']['max']:.6f} | {c['CS']['below_half_days']} | {c['CS']['above_half_days']} |
| SMA 的 b_t | {c['SMA200']['min']:.6f} | {c['SMA200']['median']:.6f} | {c['SMA200']['mean']:.6f} | {c['SMA200']['max']:.6f} | {c['SMA200']['below_half_days']} | {c['SMA200']['above_half_days']} |

例如 1 月 1 日，f_CS=0.856597、f_SMA=0.266836、f_mix=0.608674，所以当日有效关系是 0.355286×CS + 1.140541×SMA，而非各一半。SOL 的实际目标是 −0.913011% NAV；如果各取已缩放目标的一半则是 −4.823465% NAV。原始信号等权不等于风险管理后等权。

## 同一实际 STATIC50 NAV 的精确价格/资金费拆解

只作代数拆解 q_CS虚拟 = NAV_STATIC/p0 × 0.5×f_mix×raw_CS，SMA 同理；两项数量相加等于实际保存持仓。

| 虚拟来源 | 价格损益 USDT | 资金费现金 USDT |
|---|---:|---:|
| CS 原始信号 | {a['CS']['price_pnl_USDT']:+.8f} | {a['CS']['funding_cash_USDT']:+.8f} |
| SMA 原始信号 | {a['SMA200']['price_pnl_USDT']:+.8f} | {a['SMA200']['funding_cash_USDT']:+.8f} |
| 合计 | {x['price_USDT']:+.8f} | {x['funding_cash_USDT']:+.8f} |

实际净收益 = {x['price_USDT']:.8f} − {-x['funding_cash_USDT']:.8f} − {x['total_expense_USDT']:.8f} = **{x['net_USDT']:.8f} USDT**。

全部费用含再平衡 {x['rebalance_expense_USDT']:.8f} 与已支付假设性终端费用 {x['terminal_expense_USDT']:.8f}。价格减交易费但尚未扣资金费是 {x['price_minus_expense_before_funding_USDT']:.8f}，所以不能把约 295.75 误当最终净收益。以上虚拟分项不是各自独立收益率，也不是可交易的新子策略。

在同一实际 STATIC NAV 下，再与“各半已缩放目标”作纯代数比较，CS 价格贡献 {ref['CS']['half_already_sized_target_at_actual_mix_NAV']['price_pnl_USDT']:+.8f} → {a['CS']['price_pnl_USDT']:+.8f}，差 {ref['CS']['scaling_difference_at_same_NAV']['price_pnl_USDT']:+.8f}；SMA {ref['SMA200']['half_already_sized_target_at_actual_mix_NAV']['price_pnl_USDT']:+.8f} → {a['SMA200']['price_pnl_USDT']:+.8f}，差 {ref['SMA200']['scaling_difference_at_same_NAV']['price_pnl_USDT']:+.8f}。这显示该年差额主要集中在风险缩放对 SMA 路的时变配置上；此参考只分解已有路径，不能冒充因果干预或新账户。

## 不是费用或“抵消”单独导致

相对两个独立钱包各缩半的算术基准，净额少 {abs(g['net_USDT']):.8f} USDT，其中价格少 {abs(g['price_pnl_USDT']):.8f}、资金费多支出 {abs(g['funding_cash_USDT']):.8f}、交易费多支出 {abs(g['expense_contribution_USDT']):.8f}。交易费只解释约 0.07777 个百分点，不能解释约 5.94916 个百分点的净收益差。

对于固定数量，价格/资金费线性相加；多空净额相消本身不会让相加失效，净额成交通常还降低比例成本。改变结果的是混合 raw 后独立风险缩放、每日有效组成及 NAV 路径。相同名义 10% 风险预算也不等于实际风险相同：实际 2025 年波动率 CS 9.6951%、SMA 10.4576%、STATIC50 11.1025%。

JSON 保存完整数字、来源 SHA256 与数量/权重/价格/资金费/净额恒等式审计。只读复核：python mix_explanation.py。已见开发年份、每日数量参考模型，非纯净样本外或实盘资格证明。
"""
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-new", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.write_new:
        destinations = [HERE / "MIX_EXPLANATION.json", HERE / "MIX_EXPLANATION.md"]
        if any(path.exists() for path in destinations):
            raise FileExistsError("Explanation output already exists; original or existing files will not be overwritten.")
        destinations[0].write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        destinations[1].write_text(render(report))
        print(json.dumps(dict(created=[str(p) for p in destinations], arithmetic_audit=report["arithmetic_audit"]), indent=2))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
