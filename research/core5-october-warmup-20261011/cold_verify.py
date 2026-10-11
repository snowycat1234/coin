"""Fetch public original bytes and independently reproduce complete warmup."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import urllib.request
import zipfile
import numpy as np
import pandas as pd
from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits
from modules.collector_research.pipeline.download import parse_checksum

PREFIX="research/core5-october-warmup-20261011/"
digest=lambda b:hashlib.sha256(b).hexdigest()


def run(commit,directory):
    directory.mkdir(parents=True,exist_ok=False)
    denied=[]
    def audit(event,args):
        if event=="open" and isinstance(args[0],(str,bytes)):
            p=str(Path(args[0]).absolute())
            if any(p.startswith("/workspace/"+s+"/") for s in ("october2022-state","october2022-complete-state","october2022-union-state")):
                denied.append(p)
                raise RuntimeError("Original STATE access forbidden")
    sys.addaudithook(audit)
    started=time.monotonic()
    def fetch(sha,path):
        with urllib.request.urlopen("https://raw.githubusercontent.com/snowycat1234/coin/"+sha+"/"+path,timeout=20) as r:
            b=r.read(8000001)
        assert len(b)<8000001
        return b
    index_raw=fetch(commit,PREFIX+"SOURCE_INDEX.json")
    index=json.loads(index_raw)
    old=index["reused_old_daily_source_commit"]
    wrapper=fetch(old,index["reused_old_wrapper_path"])
    assert digest(wrapper)==index["reused_old_wrapper_SHA256"]
    manifest_raw=fetch(old,index["reused_old_manifest_path"])
    assert digest(manifest_raw)==index["reused_old_manifest_SHA256"]
    manifest={r["path"]:r["SHA256"] for r in json.loads(manifest_raw)["members"]}
    daily=zipfile.ZipFile(io.BytesIO(wrapper))
    saved={}
    for name,sha in index["prepared"].items():
        b=fetch(commit,PREFIX+"prepared/"+name)
        assert digest(b)==sha
        (directory/name).write_bytes(b)
        saved[name]=np.load(io.BytesIO(b),allow_pickle=False)
    l,r=month_limits(2022,10)
    grid=np.arange(l,r,60000,dtype=np.int64)
    seen=0
    added=0
    for row in index["monthly_sources"]:
        blocks=[]
        for part in row["parts"]:
            b=fetch(commit,PREFIX+part["path"])
            assert len(b)==part["bytes"] and digest(b)==part["SHA256"]
            blocks.append(b)
        b=b"".join(blocks)
        assert len(b)==row["bytes"] and digest(b)==row["SHA256"]
        check=fetch(commit,PREFIX+row["checksum_path"])
        assert digest(check)==row["CHECKSUM"] and parse_checksum(check.decode(),Path(row["raw_name"]).name)==digest(b)
        path=directory/Path(row["raw_name"]).name
        path.write_bytes(b)
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None and len(z.namelist())==1
        frame,duplicates=validate_price(numeric_csv(path),row["family"],l,r)
        assert len(frame)==row["original_month_source_minutes"] and duplicates==row["duplicates"]
        if row["family"]=="markPriceKlines":
            name=row["old_Oct2_mark_overlap"]["member"]
            b=daily.read(name)
            receipt_bytes=daily.read(name.removesuffix(".zip")+".json")
            assert digest(b)==manifest[name]==row["old_Oct2_mark_overlap"]["SHA256"]
            assert digest(receipt_bytes)==manifest[name.removesuffix(".zip")+".json"]
            receipt=json.loads(receipt_bytes)
            assert digest(b)==receipt["SHA256"]==parse_checksum(receipt["checksum_text"],row["symbol"]+"-1m-2022-10-02.zip")
            path.write_bytes(b)
            with zipfile.ZipFile(path) as z:
                assert z.testzip() is None
            past,dups=validate_price(numeric_csv(path),row["family"],l+86400000,l+2*86400000)
            assert len(past)==1440 and dups==0
            frame,dups=validate_price(pd.concat([frame,past],ignore_index=True),row["family"],l,r)
            assert dups==row["old_Oct2_mark_overlap"]["common_rows"]
            added+=1440-dups
        assert np.array_equal(frame.timestamp_ms.to_numpy(),grid)
        close=frame.close.to_numpy()[4::5]
        key=row["family"]+"_"+row["symbol"]
        np.testing.assert_array_equal(close,saved["FIVE_MIN_CLOSES.npz"][key])
        rv=np.square(np.r_[np.nan,np.diff(np.log(close))].reshape(31,288)).sum(1)
        np.testing.assert_array_equal(rv,saved["DAILY_RV.npz"][key+"_RV"])
        assert np.isnan(rv[0]) and (rv[1:]>0).all()
        assert float(close[287])==row["first_required_RV_boundary_close"]
        assert float(close[-1])==row["last_Oct31_close"]
        path.unlink()
        seen+=len(frame)
        print("COLD_VERIFIED",row["family"],row["symbol"],len(frame),flush=True)
    daily.close()
    assert seen==446400 and added==7200 and not denied
    five=saved["FIVE_MIN_CLOSES.npz"]["available_us"]
    np.testing.assert_array_equal(five[287::288],saved["DAILY_RV.npz"]["available_us"])
    result=dict(status="PASS_PUBLIC_ORIGINAL_MINUTE_COLD_RESTORE",artifact_commit=commit,source_index_SHA256=digest(index_raw),
        originals_bytes=index["original_bytes"],monthly_archives=10,Git_reused_daily_archives=5,actual_minutes=seen,
        existing_daily_gap_rows_added=added,exact_RV_and_5minclose=True,first_RV_missing_preserved=True,
        original_STATE_open_attempts=len(denied),fits=0,wallets=0,provider_downloads=0,elapsed_seconds=time.monotonic()-started)
    (directory/"PUBLIC_RESTORE.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--commit",required=True)
    p.add_argument("--directory",type=Path,required=True)
    a=p.parse_args()
    run(a.commit,a.directory)
