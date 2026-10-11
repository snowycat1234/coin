"""Public cold restore of saved HAR evidence: no estimator fit or wallet replay."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

import numpy as np
from har import DAY,SYMBOLS,feature,forecast,haircut,qlike,bootstrap

PREFIX="research/har-rv-risk-20261011/"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run(commit,directory):
    directory.mkdir(parents=True,exist_ok=False)
    blocked=[]
    forbidden=("/workspace/har-rv-state","/workspace/btc-beta-residual-state",
               "/workspace/level-reversion-state","/workspace/short-funding-residual-state")
    def audit(event,args):
        if event=="open" and isinstance(args[0],(str,bytes)):
            name=str(Path(args[0]).absolute())
            if any(name==p or name.startswith(p+"/") for p in forbidden):
                blocked.append(name)
                raise RuntimeError("Original research STATE access forbidden")
    sys.addaudithook(audit)
    def fetch(sha,path):
        url="https://raw.githubusercontent.com/snowycat1234/coin/"+sha+"/"+path
        with urllib.request.urlopen(url,timeout=20) as response:
            return response.read()
    manifest=json.loads(fetch(commit,PREFIX+"PUBLIC_BUNDLE.json"))
    raw=fetch(commit,PREFIX+"RESULT_BUNDLE.zip")
    assert len(raw)==manifest["bytes"] and digest(raw)==manifest["SHA256"]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None and set(z.namelist())==set(manifest["members"])
        for name,proof in manifest["members"].items():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            b=z.read(name)
            assert len(b)==proof["bytes"] and digest(b)==proof["SHA256"]
            p=directory/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(b)
    result=json.loads((directory/"diagnostic/RESULT.json").read_bytes())
    recovery=json.loads((directory/"prepared/RECOVERY.json").read_bytes())
    for folder,record in (("diagnostic",result),("prepared",recovery)):
        for name,proof in record["artifacts"].items():
            assert digest((directory/folder/name).read_bytes())==proof
    assert digest((directory/"prepared/RECOVERY.json").read_bytes())==result["prepared_receipt_sha256"]
    source=result["source_commit"]
    checks=[]
    for line in fetch(source,PREFIX+"SOURCE_SHA256.txt").decode().splitlines():
        expected,path=line.split(maxsplit=1)
        assert digest(fetch(source,path))==expected
        checks.append(dict(path=path,SHA256=expected))
    data=np.load(directory/"prepared/DAILY_RV.npz",allow_pickle=False)
    context=np.load(directory/"diagnostic/CONTEXT_INPUTS.npz",allow_pickle=False)
    predictions=np.load(directory/"diagnostic/PREDICTIONS.npz",allow_pickle=False)
    targets=np.load(directory/"diagnostic/SAVED_TARGETS.npz",allow_pickle=False)
    model=json.loads((directory/"diagnostic/MODEL.json").read_bytes())
    assert list(data["symbol_order"])==list(targets["symbol_order"])==list(SYMBOLS)
    t=data["available_us"]
    rv=np.column_stack([data[s+"_RV"] for s in SYMBOLS])
    prices=np.column_stack([data[s+"_close"] for s in SYMBOLS])
    assert np.all(np.diff(t)==DAY) and len(t)==365 and np.isnan(rv[0]).all()
    # Explicit frozen February2 and June30, no date inference from results.
    training=np.flatnonzero((t>=1612224000000000)&(t<=1625011200000000))
    evaluation=np.searchsorted(t,targets["decision_us"])
    assert len(training)==149 and len(evaluation)==182
    assert t[training[-1]+1]==model["latest_label_maturity_us"]==1625097600000000
    normal_error=0.
    for asset in range(5):
        x=np.stack([feature(rv,int(i))[asset] for i in training])
        residual=np.log(rv[training+1,asset])-x@np.asarray(model["coefficients"][asset])
        normal_error=max(normal_error,float(abs(x.T@residual).max()))
        assert abs(np.exp(residual).mean()-model["smearing"][asset])<1e-12
    assert normal_error<1e-8
    train_scales=[]
    for i in training:
        j=np.searchsorted(context["decision_us"],t[i])
        r=prices[i-29:i+1]/prices[i-30:i]-1
        train_scales.append(haircut(context["expert_targets"][j,2],forecast(rv,int(i),model),r)[0])
    static=float(np.mean(train_scales))
    assert abs(static-result["static_training_scalar"])<1e-14
    maximum_prediction_error=maximum_target_error=0.
    losses={k:[] for k in ("HAR","LAST_RV","MEAN30_RV","DAILY_RETURN_VAR30")}
    for k,i in enumerate(evaluation):
        j=np.searchsorted(context["decision_us"],t[i])
        assert context["decision_us"][j]==t[i]==targets["decision_us"][k]
        r=prices[i-29:i+1]/prices[i-30:i]-1
        base=context["expert_targets"][j,2]
        predicted=dict(HAR=forecast(rv,int(i),model),LAST_RV=rv[i],MEAN30_RV=rv[i-29:i+1].mean(0),
                       DAILY_RETURN_VAR30=r.var(axis=0,ddof=1))
        expected=dict(BASE30=base,HAR=base*haircut(base,predicted["HAR"],r)[0],
                      LAST_RV=base*haircut(base,predicted["LAST_RV"],r)[0],STATIC_TRAIN_HAIRCUT=base*static)
        for arm,value in predicted.items():
            maximum_prediction_error=max(maximum_prediction_error,float(abs(value-predictions[arm][k]).max()))
            losses[arm].append(qlike(rv[i+1],value))
        for arm,value in expected.items():
            maximum_target_error=max(maximum_target_error,float(abs(value-targets[arm][k]).max()))
        np.testing.assert_array_equal(rv[i+1],predictions["actual_RV"][k])
    assert maximum_prediction_error<1e-14 and maximum_target_error<1e-14
    losses={k:np.asarray(v) for k,v in losses.items()}
    for arm,value in losses.items():
        assert abs(float(value.mean())-result["all_asset_mean_QLIKE"][arm])<1e-14
    delta=np.column_stack([(losses["HAR"]-losses[arm]).mean(1) for arm in ("LAST_RV","MEAN30_RV")])
    np.testing.assert_allclose(bootstrap(delta),result["joint_block_bootstrap95"],rtol=0,atol=1e-14)
    assert result["status"]=="STOP_FIXED_HAR_RV_SIZING" and result["wallets"]==0
    assert not blocked
    receipt=dict(status="PASS_PUBLIC_COLD_RESTORE_NO_REFIT",artifact_commit=commit,source_commit=source,
        members=len(manifest["members"]),bundle_SHA256=manifest["SHA256"],source_checks=checks,
        normal_equation_max_error=normal_error,max_prediction_error=maximum_prediction_error,
        max_target_error=maximum_target_error,common_mature_dates=182,bootstrap_reproduced=True,
        original_STATE_open_attempts=len(blocked),OLS_fits=0,wallets=0,
        scope="Saved historical forecasts/targets/losses reproduced; no new fit, no funding/real wallet profit inference.")
    (directory/"PUBLIC_RESTORE.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--commit",required=True)
    p.add_argument("--directory",type=Path,required=True)
    a=p.parse_args()
    run(a.commit,a.directory)
