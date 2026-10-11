"""Restore published2022 source panels and independently reconstruct measured RV."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile
import numpy as np

PREFIX="research/core5-2022-rv-source-20261011/"


def run(commit,directory):
    directory.mkdir(parents=True,exist_ok=False)
    blocked=[]
    def audit(event,args):
        if event=="open" and isinstance(args[0],(str,bytes)):
            name=str(Path(args[0]).absolute())
            if name.startswith("/workspace/core5-2022-rv-state/"):
                blocked.append(name)
                raise RuntimeError("Original STATE access prohibited")
    sys.addaudithook(audit)
    def fetch(sha,path):
        with urllib.request.urlopen("https://raw.githubusercontent.com/snowycat1234/coin/"+sha+"/"+path,timeout=20) as response:
            return response.read()
    digest=lambda raw:hashlib.sha256(raw).hexdigest()
    manifest=json.loads(fetch(commit,PREFIX+"PUBLIC_BUNDLE.json"))
    blob=fetch(commit,PREFIX+"DATA_BUNDLE.zip")
    assert len(blob)==manifest["bytes"] and digest(blob)==manifest["SHA256"]
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert z.testzip() is None and set(z.namelist())==set(manifest["members"])
        for name,proof in manifest["members"].items():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            b=z.read(name)
            assert len(b)==proof["bytes"] and digest(b)==proof["SHA256"]
            p=directory/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(b)
    receipt=json.loads((directory/"prepared/RECOVERY.json").read_bytes())
    for name,proof in receipt["artifacts"].items():
        assert digest((directory/"prepared"/name).read_bytes())==proof
    bound=[]
    for line in fetch(receipt["source_commit"],PREFIX+"SOURCE_SHA256.txt").decode().splitlines():
        expected,path=line.split(maxsplit=1)
        assert digest(fetch(receipt["source_commit"],path))==expected
        bound.append(dict(path=path,SHA256=expected))
    sample=np.load(directory/"prepared/FIVE_MIN_CLOSES.npz",allow_pickle=False)
    daily=np.load(directory/"prepared/DAILY_RV.npz",allow_pickle=False)
    assert list(sample["symbol_order"])==list(daily["symbol_order"])==["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"]
    assert len(sample["available_us"])==8640 and np.all(np.diff(sample["available_us"])==300_000_000)
    assert np.array_equal(sample["available_us"][287::288],daily["available_us"])
    maximum_RV_error=0.
    for domain in ("klines","markPriceKlines"):
        for symbol in sample["symbol_order"]:
            key=domain+"_"+symbol
            prices=sample[key]
            assert len(prices)==8640 and np.isfinite(prices).all() and (prices>0).all()
            value=np.square(np.r_[np.nan,np.diff(np.log(prices))].reshape(30,288)).sum(1)
            assert np.isnan(value[0]) and np.isnan(daily[key+"_RV"][0])
            maximum_RV_error=max(maximum_RV_error,float(abs(value[1:]-daily[key+"_RV"][1:]).max()))
            np.testing.assert_array_equal(prices.reshape(30,288)[:,-1],daily[key+"_close"])
    assert maximum_RV_error==0 and receipt["thirty_day_RV_mature_nextday_rows"]=={"klines":0,"markPriceKlines":0}
    assert all(x["observed_minutes"]==43200 and x["CHECKSUM"] and x["CRC"] for x in receipt["source_members"])
    assert receipt["parameter_fits"]==receipt["wallets"]==receipt["provider_downloads"]==0 and not blocked
    result=dict(status="PASS_PUBLIC_2022_RV_COLD_RESTORE",artifact_commit=commit,source_commit=receipt["source_commit"],
        restored_members=len(manifest["members"]),source_checks=bound,maximum_RV_error=maximum_RV_error,
        first_RV_missing_preserved=True,valid_asset_domain_days=290,eligible30day_plus_nextlabel_rows=0,
        original_STATE_open_attempts=len(blocked),parameter_fits=0,wallets=0,
        scope="Saved measuredRV/source proofs reconstructed, not repeat1mCSVparse, newstrategy or historicalnativecertification.")
    (directory/"PUBLIC_RESTORE.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--commit",required=True)
    p.add_argument("--directory",type=Path,required=True)
    a=p.parse_args()
    run(a.commit,a.directory)
