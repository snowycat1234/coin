"""Recover actual5min variance from existing official ZIPs; zero statistical fits."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

import numpy as np
from modules.collector_research.pipeline.normalize import numeric_csv, validate_price, month_limits

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = "94fe13c494c82bb6e6868e6614eb7298fb15b3c3"
PACKET = "research/core5-2021-economic-data/Y2021/"
SYMBOLS = ("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT")
DAY = 86_400_000_000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def save(path,data):
    with path.open("x") as f:
        f.write(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+"\n")


def run(archive,output,source_commit):
    git = lambda *x:subprocess.check_output(["git",*x],cwd=ROOT).decode().strip()
    assert git("rev-parse","HEAD")==source_commit and not git("status","--porcelain")
    index = json.loads(subprocess.check_output(["git","show",DATA+":"+PACKET+"INDEX.json"],cwd=ROOT))
    assert archive.stat().st_size==index["package_bytes"] and file_sha(archive)==index["package_SHA256"]
    members = {r["name"]:r for r in index["members"]}
    output.mkdir(parents=True)
    start = time.monotonic()
    evidence, values, samples = [], {}, {}
    with zipfile.ZipFile(archive) as z:
        for symbol in SYMBOLS:
            closes, opens = [], []
            for month in range(1,13):
                name = f"raw/klines/{symbol}/{symbol}-1m-2021-{month:02d}.zip"
                raw,check = z.read(name),z.read(name+".CHECKSUM")
                for n,b in ((name,raw),(name+".CHECKSUM",check)):
                    assert len(b)==members[n]["bytes"] and sha(b)==members[n]["SHA256"]
                parts = check.decode().strip().split()
                assert len(parts)==2 and parts[0]==sha(raw) and parts[1].lstrip("*")==Path(name).name
                with zipfile.ZipFile(io.BytesIO(raw)) as inner:
                    assert inner.testzip() is None
                path = output/"temporary-source.zip"
                with path.open("xb") as f:
                    f.write(raw)
                try:
                    left,right = month_limits(2021,month)
                    frame,duplicates = validate_price(numeric_csv(path),"klines",left,right)
                finally:
                    path.unlink()
                required = np.arange(left,right,60_000,dtype=np.int64)
                assert np.array_equal(frame.timestamp_ms.to_numpy(),required)
                # End-of5min closes, not high/low or executable future fields.
                closes.append(frame.close.to_numpy(dtype=float)[4::5])
                opens.append(frame.open.to_numpy(dtype=float)[::1440])
                evidence.append(dict(name=name,sha256=sha(raw),actual_minutes=len(frame),duplicates=duplicates,
                    CHECKSUM=True,CRC=True,zero_quote_minutes=int((frame.quote_volume==0).sum())))
                print("PREPARE",symbol,month,"/12",len(frame),"observed minutes",flush=True)
                assert time.monotonic()-start<600 and shutil.disk_usage(output).free>=15*1024**3
            close5 = np.concatenate(closes)
            opening = np.concatenate(opens)
            assert close5.shape==(365*288,) and opening.shape==(365,)
            returns = np.concatenate([[np.nan],np.diff(np.log(close5))]).reshape(365,288)
            rv = (returns*returns).sum(axis=1)
            assert np.isnan(rv[0]) and np.isfinite(rv[1:]).all() and (rv[1:]>0).all()
            values[symbol+"_RV"] = rv
            values[symbol+"_open"] = opening
            values[symbol+"_close"] = close5.reshape(365,288)[:,-1]
            values[symbol+"_max_logrise"] = (np.log(close5.reshape(365,288))-np.log(opening)[:,None]).max(axis=1)
            samples[symbol] = close5
    available = np.arange(1609545600000000,1641081600000000,DAY,dtype=np.int64)
    assert available.shape==(365,)
    np.savez_compressed(output/"DAILY_RV.npz",available_us=available,symbol_order=np.asarray(SYMBOLS),**values)
    np.savez_compressed(output/"FIVE_MIN_CLOSES.npz",symbol_order=np.asarray(SYMBOLS),**samples)
    save(output/"RECOVERY.json",dict(status="PASS_ACTUAL_FULL_INTRADAY_RV",source_commit=source_commit,
        data_git=DATA,archive_sha256=index["package_SHA256"],members=evidence,
        RV_valid_days_per_asset=364,excluded_first_RV_reason="JAN1_PRIOR5MIN_CLOSE_NOT_RECOVERED_NOT_IMPUTED",
        scientific_fits=0,new_provider_downloads=0,elapsed_seconds=time.monotonic()-start,
        artifacts={p.name:file_sha(p) for p in output.iterdir()}))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source-commit",required=True)
    args=parser.parse_args()
    run(args.archive,args.output,args.source_commit)
