"""Reuse mature official downloader/validator for exactly missing2022October."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from datetime import datetime,timezone
import zipfile

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT")
DAY=86_400_000_000
OLD="49017d88b75498a53f90857fe0d01a622e812a2f"
OLD_PATH="research/cached-history-repair-20261010/"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path,record):
    with path.open("x") as f:
        f.write(json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+"\n")


def run(state,inventory,source):
    git=lambda *x:subprocess.check_output(["git",*x],cwd=ROOT)
    assert git("rev-parse","HEAD").decode().strip()==source and not git("status","--porcelain")
    review=json.loads(inventory.read_bytes())
    assert review["source_inventory_complete"] and review["unknown_source_archives"]==0
    assert not review["complete_october_month_sources"]
    state=state.resolve()
    assert state.is_relative_to(Path("/workspace")) and not state.exists()
    state.mkdir()
    save(state/"STARTED.json",dict(source_commit=source,inventory_SHA256=digest(inventory.read_bytes()),fits=0,wallets=0))
    os.environ.update(WORK_DIR=str(state/"work"),RAW_CACHE_DIR=str(state/"raw"),
        SYMBOLS=",".join(SYMBOLS),WARMUP_START="2022-10-01",START_DATE="2022-10-01",END_DATE="2022-10-31",
        FAMILIES="klines,markPriceKlines,fundingRate",HTTP_RETRIES="0",HTTP_CONNECT_TIMEOUT="10",HTTP_READ_TIMEOUT="20",
        MAX_ARCHIVE_MIB="8",MAX_UNCOMPRESSED_MIB="64",MAX_WORK_GIB="16",MIN_FREE_GIB="15",REFRESH_CHECKSUMS="0")
    from modules.collector_research.pipeline.download import Job,fetch,session,parse_checksum
    from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits
    from modules.collector_research.pipeline.common import bounds
    bounds()  # Existing immutable collector date guard, without reading lock body.
    raw=git("show",OLD+":"+OLD_PATH+"RECOVERY.zip")
    assert len(raw)==2484855 and digest(raw)=="42e59bf2200034f433816fc70b8a2da43eb36363810ba356d8ffdc3ddb7be929"
    oldzip=zipfile.ZipFile(io.BytesIO(raw))
    old_manifest_bytes=git("show",OLD+":"+OLD_PATH+"MANIFEST.json")
    assert digest(old_manifest_bytes)=="8191e0e26287ded3c02302b63f9c7f1f90b2396ff04e09385d9bbcf9b2b18ad6"
    old_manifest=json.loads(old_manifest_bytes)
    old_id={x["path"]:x["SHA256"] for x in old_manifest["members"]}
    rows=[]
    samples={}
    daily={}
    start=time.monotonic()
    downloaded=0
    left,right=month_limits(2022,10)
    grid=np.arange(left,right,60_000,dtype=np.int64)
    assert len(grid)==44640
    prepared=state/"prepared"
    prepared.mkdir()
    with session() as connection:
        for family in ("klines","markPriceKlines"):
            for symbol in SYMBOLS:
                job=Job(symbol,family,2022,10)
                try:
                    record=fetch(job,connection)
                except Exception as exc:
                    status=getattr(getattr(exc,"response",None),"status_code",None)
                    save(state/"BLOCKED.json",dict(status="SOURCE_ACQUISITION_STOP",family=family,symbol=symbol,
                        HTTP_status=status,error_class=type(exc).__name__,no_refusal_retry_or_bypass=True,
                        completed_archives=len(rows),fits=0,wallets=0))
                    raise
                if record["status"]=="ARCHIVE_UNAVAILABLE_UNCLASSIFIED":
                    save(state/"BLOCKED.json",dict(status="OFFICIAL_MONTH_404_UNAVAILABLE",family=family,symbol=symbol,
                        no_imputation=True,completed_archives=len(rows),fits=0,wallets=0))
                    raise RuntimeError("Official monthly archive unavailable")
                downloaded+=record["bytes"]
                assert downloaded<=30_000_000
                frame,duplicates=validate_price(numeric_csv(job.path),family,left,right)
                assert np.array_equal(frame.timestamp_ms.to_numpy(),grid)
                overlap=None
                if family=="markPriceKlines":
                    prefix="gap-repair/"+symbol+"_markPriceKlines_2022-10-02"
                    day_bytes=oldzip.read(prefix+".zip")
                    receipt_bytes=oldzip.read(prefix+".json")
                    assert digest(day_bytes)==old_id[prefix+".zip"] and digest(receipt_bytes)==old_id[prefix+".json"]
                    receipt=json.loads(receipt_bytes)
                    assert digest(day_bytes)==receipt["SHA256"]==parse_checksum(receipt["checksum_text"],symbol+"-1m-2022-10-02.zip")
                    temporary=prepared/(symbol+"-1m-2022-10-02.zip")
                    temporary.write_bytes(day_bytes)
                    try:
                        old_frame,old_duplicates=validate_price(numeric_csv(temporary),family,left+86_400_000,left+2*86_400_000)
                    finally:
                        temporary.unlink()
                    current=frame[(frame.timestamp_ms>=left+86_400_000)&(frame.timestamp_ms<left+2*86_400_000)].reset_index(drop=True)
                    assert len(old_frame)==len(current)==1440 and old_duplicates==0
                    assert np.array_equal(old_frame.to_numpy(),current.to_numpy())
                    overlap=dict(old_data_commit=OLD,member=prefix+".zip",SHA256=digest(day_bytes),
                        rows=1440,all_source_numeric_fields_exact=True)
                close=frame.close.to_numpy(dtype=float)[4::5]
                key=family+"_"+symbol
                r=np.r_[np.nan,np.diff(np.log(close))].reshape(31,288)
                rv=np.square(r).sum(1)
                assert np.isnan(rv[0]) and np.isfinite(rv[1:]).all() and (rv[1:]>0).all()
                samples[key]=close
                daily[key+"_RV"]=rv
                daily[key+"_close"]=close.reshape(31,288)[:,-1]
                # Boundary is source minute Oct1 23:59, available Oct2 00:00.
                assert frame.timestamp_ms.iloc[1439]==left+86_400_000-60_000
                rows.append(dict(family=family,symbol=symbol,raw_name=str(job.path.relative_to(state/"raw")),
                    official_URL=job.url,received_UTC=datetime.now(timezone.utc).isoformat(),bytes=record["bytes"],
                    SHA256=record["sha256"],CHECKSUM=digest(Path(str(job.path)+".CHECKSUM").read_bytes()),
                    observed_minutes=len(frame),duplicates=duplicates,zero_quote_minutes=int((frame.quote_volume==0).sum()),
                    exact_complete_grid=True,CRC=True,old_Oct2_mark_overlap=overlap,
                    first_required_RV_boundary_close=float(close[287]),last_Oct31_close=float(close[-1])))
                save(state/(family+"_"+symbol+"_SOURCE.json"),rows[-1])
                print("PREPARED",family,symbol,"44640 actual minutes; SHA/CRC/grid/boundary",flush=True)
                assert time.monotonic()-start<600 and shutil.disk_usage(state).free>=15*1024**3
                assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<=200_000_000
    oldzip.close()
    available=np.arange((left+86_400_000)*1000,(right+86_400_000)*1000,DAY,dtype=np.int64)
    five_available=np.arange((left+300_000)*1000,(right+300_000)*1000,300_000_000,dtype=np.int64)
    np.savez_compressed(prepared/"DAILY_RV.npz",available_us=available,symbol_order=np.asarray(SYMBOLS),**daily)
    np.savez_compressed(prepared/"FIVE_MIN_CLOSES.npz",available_us=five_available,symbol_order=np.asarray(SYMBOLS),**samples)
    save(state/"RECOVERY.json",dict(status="PASS_OCTOBER_CONTINUOUS_WARMUP_AND_TRUE_BOUNDARIES",source_commit=source,
        inventory_SHA256=digest(inventory.read_bytes()),protocol_SHA256=digest((HERE/"PROTOCOL.json").read_bytes()),
        sources=rows,downloaded_archives=len(rows),downloaded_bytes=downloaded,actual_minutes=446400,
        valid_RV_days_each_domain_asset=30,first_Oct1_RV_missing_preserved=True,old_overlap_rows_verified=7200,
        fits=0,wallets=0,HAR_refits=0,elapsed_seconds=time.monotonic()-start,
        derived={p.name:digest(p.read_bytes()) for p in prepared.iterdir()},
        scope="2022allowed seen historical source; minute-close clocks are conservative replay availability, not actual historicalarrivalpublication certification. No future completeness filter or sample deletion used."))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--state",type=Path,required=True)
    p.add_argument("--inventory",type=Path,required=True)
    p.add_argument("--source-commit",required=True)
    a=p.parse_args()
    run(a.state,a.inventory,a.source_commit)
