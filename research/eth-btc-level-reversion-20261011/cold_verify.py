"""Restore public small artifacts and independently audit saved targets, zero fits."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

import numpy as np

DAY = 86_400_000_000
PREFIX = "research/eth-btc-level-reversion-20261011/"


def run(commit, directory):
    directory.mkdir(exist_ok=False)
    blocked = []
    forbidden = ("/workspace/coin-liquidation-next", "/workspace/btc-beta-residual-state",
                 "/workspace/short-funding-residual-state", "/workspace/level-reversion-state")

    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes)):
            name = str(Path(args[0]).absolute())
            if any(name == p or name.startswith(p+"/") for p in forbidden):
                blocked.append(name)
                raise RuntimeError("Original workspace/STATE access forbidden")
    sys.addaudithook(audit)

    def fetch(sha, path):
        url = "https://raw.githubusercontent.com/snowycat1234/coin/"+sha+"/"+path
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.read()

    def digest(raw):
        return hashlib.sha256(raw).hexdigest()

    raw_result = fetch(commit,PREFIX+"results/RESULT.json")
    (directory/"RESULT.json").write_bytes(raw_result)
    result = json.loads(raw_result)
    for name, sha in result["artifacts"].items():
        blob = fetch(commit,PREFIX+"results/"+name)
        assert digest(blob) == sha
        (directory/name).write_bytes(blob)
    source = result["source_commit"]
    bound = fetch(source,PREFIX+"SOURCE_SHA256.txt").decode()
    source_checks = []
    for row in bound.splitlines():
        sha,path = row.split(maxsplit=1)
        blob = fetch(source,path)
        assert digest(blob) == sha
        source_checks.append(dict(path=path,sha256=sha))
    inputs = np.load(directory/"OBSERVED_INPUTS.npz",allow_pickle=False)
    saved = np.load(directory/"SAVED_TARGETS.npz",allow_pickle=False)
    model = json.loads((directory/"MODEL.json").read_bytes())
    labels = json.loads((directory/"LABELS.json").read_bytes())
    assert list(inputs["symbol_order"]) == list(saved["symbol_order"]) == ["BTCUSDT","ETHUSDT"]
    t,p,d = inputs["clocks"],inputs["prices"],saved["decision_us"]
    assert np.all(np.diff(t)==DAY) and np.all(np.diff(d)==DAY) and np.isfinite(p).all()
    fit = t<=result["fit_latest_available_us"]
    x,y = np.log(p[fit]).T
    residual = y-model["alpha"]-model["beta"]*x
    # Check OLS normal equations and normalization without fitting another model.
    assert fit.sum() == model["observations"] == 366
    assert abs(residual.mean()-model["mean"]) < 1e-14
    assert abs((x-x.mean())@residual) < 1e-10
    assert abs(residual.std(ddof=1)-model["sigma"]) < 1e-14
    beta, alpha = model["beta"],model["alpha"]
    calculated = {arm:np.zeros((len(d),2)) for arm in ("reversion","momentum")}
    directions = dict.fromkeys(calculated,0.)
    events = []
    for i,clock in enumerate(d):
        k = np.searchsorted(t,clock)
        assert t[k] == clock and k>=30
        level = np.log(p[k,1])-alpha-beta*np.log(p[k,0])
        if (int(clock)//DAY)%7 == 4:
            z = (level-model["mean"])/model["sigma"]
            past_level = np.log(p[k-7,1])-alpha-beta*np.log(p[k-7,0])
            directions = dict(reversion=-np.sign(z) if abs(z)>=1 else 0.,
                              momentum=np.sign(level-past_level) if abs(z)>=1 else 0.)
            events.append((i,k,float(z),bool(abs(z)>=1)))
        past = p[k-29:k+1]/p[k-30:k]-1
        covariance = np.cov(past,rowvar=False,ddof=1)*365
        for arm,direction in directions.items():
            w = np.array([-beta*.3*direction,.3*direction])
            w *= min(1.,.3/max(abs(w).max(),1e-30),.6/max(abs(w).sum(),1e-30))
            w = np.clip(w,-.3,.3)
            if abs(w).sum()>.6:
                w *= .6/abs(w).sum()
            sigma = np.sqrt(max(0.,w@covariance@w))
            if sigma>.10:
                w *= .10/sigma
            calculated[arm][i] = w
    target_error = max(float(abs(calculated[a]-saved[a]).max()) for a in calculated)
    assert target_error < 1e-14 and saved["ready"].all()
    label_error = 0.
    assert len(events) == len(labels) == 50
    for (i,k,z,active),r in zip(events,labels):
        assert int(d[i]) == r["decision_us"] and r["label_mature_us"] == int(d[i])+7*DAY and active == r["active"]
        delta = (np.log(p[k+7,1])-beta*np.log(p[k+7,0]))-(np.log(p[k,1])-beta*np.log(p[k,0]))
        label_error = max(label_error,abs(delta-r["future_spread_change"]),abs(z-r["z"]))
        future = p[k+7]/p[k]-1
        for a in calculated:
            label_error = max(label_error,abs(calculated[a][i]@future-r["portfolio_simple_return_proxy"][a]))
    assert label_error < 1e-13 and result["status"] == "STOP_FIXED_ETH_BTC_LEVEL_REVERSION"
    assert not blocked
    receipt = dict(status="PASS_PUBLIC_RESTORE_AND_INDEPENDENT_TARGET_LABEL_RECONSTRUCTION",
        artifact_commit=commit,source_commit=source,result_sha256=digest(raw_result),source_checks=source_checks,
        parameter_fits=0,statistical_test_fits=0,wallets=0,original_workspace_STATE_open_attempts=len(blocked),
        max_target_error=target_error,max_label_error=label_error,mature_labels=len(labels),
        scope="Restored saved statistical result; no second cointegration fit or new historical outcome. Verified fixed OLS normal equations, targets and labels independently.")
    (directory/"PUBLIC_RESTORE.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit",required=True)
    parser.add_argument("--directory",type=Path,required=True)
    args = parser.parse_args()
    run(args.commit,args.directory)
