"""One price-only calibration/seen-training test; economic wallets require gates."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from level import DAY, SYMBOLS, fit_model, spread, targets

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA_COMMIT = "e0d3400b23842f11f167a63e7d80856d76501de8"
DATA_DIR = "research/temporal-feature-data-20261009/"
ARCHIVE_SHA = "bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1_000_000)


def save(path, value):
    raw = json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n"
    with path.open("x") as f:
        f.write(raw)


def load_prices(archive=None):
    if archive is not None:
        raw = archive.read_bytes()
    else:
        index = json.loads(subprocess.check_output(["git", "show", DATA_COMMIT+":"+DATA_DIR+"INDEX.json"], cwd=ROOT))
        parts = [subprocess.check_output(["git", "show", DATA_COMMIT+":"+DATA_DIR+p["file"]], cwd=ROOT) for p in index["parts"]]
        assert all(sha(b) == p["SHA256"] and len(b) == p["bytes"] for b,p in zip(parts,index["parts"]))
        raw = b"".join(parts)
    assert sha(raw) == ARCHIVE_SHA
    clocks = np.arange(stamp("2020-01-02"), stamp("2021-12-28"), DAY, dtype=np.int64)
    prices = np.full((len(clocks), 2), np.nan)
    sources = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        manifest = json.loads(z.read("MEMBERS.json"))["files"]
        for j,s in enumerate(SYMBOLS):
            name = "source_tables_not_model_inputs/daily_features/"+s+".parquet"
            blob = z.read(name)
            assert sha(blob) == manifest[name]["SHA256"]
            dtype = pq.read_schema(io.BytesIO(blob)).field("dt").type
            table = pq.read_table(io.BytesIO(blob), columns=["dt", "close", "complete_kline"], filters=[
                ("dt", ">=", pa.scalar(datetime(2020,1,1,tzinfo=timezone.utc), type=dtype)),
                ("dt", "<", pa.scalar(datetime(2021,12,27,tzinfo=timezone.utc), type=dtype))])
            times = table["dt"].to_numpy().astype("datetime64[us]").astype(np.int64)+DAY
            assert len(np.unique(times)) == len(times) and (times<=stamp("2021-12-27")).all()
            good = np.asarray(table["complete_kline"].to_pylist(), bool)
            prices[(times-clocks[0])//DAY,j] = np.where(good, table["close"].to_numpy(), np.nan)
            sources.append(dict(symbol=s, member_sha256=sha(blob), projected_columns=["dt","close","complete_kline"],
                projected_rows=len(times), max_available_us=int(times.max())))
    assert np.isfinite(prices).all() and (prices>0).all()
    return clocks, prices, sources


def run(args):
    git = lambda *x: subprocess.check_output(["git", *x],cwd=ROOT).decode().strip()
    assert git("rev-parse","HEAD") == args.source_commit and not git("status","--porcelain")
    # Dependency is private task-local state; shared research venv is unchanged.
    sys.path.insert(0,str(args.dependencies.resolve()))
    import statsmodels
    from statsmodels.tsa import stattools
    assert statsmodels.__version__ == "0.14.5"
    output = args.output.resolve()
    output.mkdir()
    start = time.monotonic()
    save(output/"STARTED.json",dict(source_commit=args.source_commit,protocol_sha256=sha((HERE/"PROTOCOL.json").read_bytes()),
        scientific_attempt=1,seed=None,parameter_OLS_fits_planned=1,cointegration_internal_OLS_planned=2,wallets_constructed=0))
    t,p,sources = load_prices(args.archive)
    fit = (t>=stamp("2020-01-02")) & (t<=stamp("2021-01-01"))
    assert fit.sum() == 366
    model = fit_model(p[fit])
    statistic, prob, critical = stattools.coint(np.log(p[fit,1]),np.log(p[fit,0]),trend="c",maxlag=1,autolag=None)
    d = np.arange(stamp("2021-01-11"),stamp("2021-12-27"),DAY,dtype=np.int64)
    assert d[0]-t[fit][-1] > 7*DAY
    result = targets(p,t,model,d)
    labels = []
    for formation in result["formations"]:
        clock = formation["decision_us"]
        assert clock+7*DAY <= stamp("2021-12-27") and formation["ready"]
        i, k = int(np.searchsorted(d,clock)), int(np.searchsorted(t,clock))
        future = p[k+7]/p[k]-1
        delta = float(spread(p[k+7],model)-spread(p[k],model))
        returns = {arm:float(result["weights"][arm][i]@future) for arm in result["weights"]}
        cost_proxy = {arm:float(.0027*np.abs(result["weights"][arm][i]).sum()) for arm in result["weights"]}
        labels.append(dict(decision_us=clock,label_mature_us=clock+7*DAY,z=formation["z"],active=formation["active"],
            future_spread_change=delta,portfolio_simple_return_proxy=returns,entry_roundtrip_cost_proxy=cost_proxy,
            paired_gross_return_proxy=returns["reversion"]-returns["momentum"]))
    halves = {}
    for name, keep in (("H1",lambda r:r["decision_us"]<stamp("2021-07-01")),("H2",lambda r:r["decision_us"]>=stamp("2021-07-01"))):
        rows = [r for r in labels if keep(r) and r["active"]]
        halves[name] = dict(mature_active_count=len(rows), mean_reversion_gross_proxy=float(np.mean([r["portfolio_simple_return_proxy"]["reversion"] for r in rows])) if rows else 0.,
            mean_paired_gross_proxy=float(np.mean([r["paired_gross_return_proxy"] for r in rows])) if rows else 0.,
            mean_reversion_after_cost_proxy=float(np.mean([r["portfolio_simple_return_proxy"]["reversion"]-r["entry_roundtrip_cost_proxy"]["reversion"] for r in rows])) if rows else 0.)
    correlation = float(np.corrcoef([-r["z"] for r in labels],[r["future_spread_change"] for r in labels])[0,1])
    altered = p.copy()
    altered[t>=stamp("2021-07-01"),1] *= 1.9
    changed = targets(altered,t,model,d)
    prefix_error = max(float(np.max(np.abs(result["weights"][arm][d<stamp("2021-07-01")]-changed["weights"][arm][d<stamp("2021-07-01")])) ) for arm in result["weights"])
    assert prefix_error == 0
    gates = dict(calibration_cointegration_p_below_005=bool(prob<.05),positive_frozen_beta=bool(model["beta"]>0),
        pooled_reversion_correlation_positive=bool(correlation>0),causal_future_perturbation_pass=prefix_error==0)
    for name, half in halves.items():
        gates[name+"_active_count_at_least12"] = half["mature_active_count"]>=12
        gates[name+"_reversion_proxy_positive"] = half["mean_reversion_gross_proxy"]>0
        gates[name+"_paired_increment_positive"] = half["mean_paired_gross_proxy"]>0
    assert time.monotonic()-start < 120
    np.savez_compressed(output/"OBSERVED_INPUTS.npz", symbol_order=np.asarray(SYMBOLS),clocks=t,prices=p)
    np.savez_compressed(output/"SAVED_TARGETS.npz",symbol_order=np.asarray(SYMBOLS),decision_us=d,
        reversion=result["weights"]["reversion"],momentum=result["weights"]["momentum"],ready=result["ready"])
    save(output/"MODEL.json",model)
    save(output/"LABELS.json",labels)
    verdict = dict(status="PREDICTIVE_GATE_PASS" if all(gates.values()) else "STOP_FIXED_ETH_BTC_LEVEL_REVERSION",
        economic_wallet_status="PERMITTED_BY_FROZEN_GATE" if all(gates.values()) else "NOT_RUN_FAILED_PREDICTIVE_GATE",
        gates=gates,cointegration=dict(statistic=float(statistic),p_value=float(prob),critical_values=critical.tolist(),
            trend="c",maxlag=1,autolag=None,scope="Conditional on I(1) model assumptions; non-rejection is not proof of absence of every relation"),
        halves=halves,pooled_reversion_score_forward_spread_correlation=correlation,
        model=model,mature_formations=len(labels),fit_latest_available_us=int(t[fit][-1]),
        max_label_mature_us=max(r["label_mature_us"] for r in labels),future_perturbation_prefix_error=prefix_error,
        source_projection=sources,scientific_attempts=1,primary_parameter_OLS_fits=1,coint_internal_OLS=2,
        additional_prefix_parameter_fits=0,neural_fits=0,historical_wallets=0,
        elapsed_seconds=time.monotonic()-start,source_commit=args.source_commit,protocol_sha256=sha((HERE/"PROTOCOL.json").read_bytes()),
        dependencies=dict(statsmodels=statsmodels.__version__,stattools_sha256=sha(Path(stattools.__file__).read_bytes())),
        artifacts={f.name:sha(f.read_bytes()) for f in output.iterdir()},
        conclusion="One fixed pair/calibration/holding recipe; seen historical training development, no alpha or pristine-OOS qualification. No rescue search.")
    save(output/"RESULT.json",verdict)
    print(json.dumps({"status":verdict["status"],"p":float(prob),"halves":halves,"wallets":0},indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path)
    parser.add_argument("--dependencies",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source-commit",required=True)
    run(parser.parse_args())
