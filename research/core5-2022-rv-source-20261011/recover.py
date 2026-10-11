"""Source-only 2022 recovery; zero estimators, strategy recipes or wallets."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"har-rv-risk-20261011"))
from prepare import SYMBOLS,DAY,file_sha,sha,save
from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits

DATA="d69e9ac94478c5be54cb46c622afec7aaf3c61f7"
PREFIX="bear_recovery_data/data/raw/"


def run(archive,output,source):
    git=lambda *x:subprocess.check_output(["git",*x],cwd=ROOT).decode().strip()
    assert git("rev-parse","HEAD")==source and not git("status","--porcelain")
    protocol=json.loads((HERE/"PROTOCOL.json").read_bytes())
    assert archive.stat().st_size==protocol["wrapper_bytes"] and file_sha(archive)==protocol["wrapper_sha256"]
    output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    evidence=[]
    samples={}
    daily={}
    left,right=month_limits(2022,11)
    expected=np.arange(left,right,60_000,dtype=np.int64)
    assert len(expected)==43200
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==163
        # Do not open old account/model/result members or any2023price archive.
        for family in ("klines","markPriceKlines"):
            for symbol in SYMBOLS:
                name=PREFIX+family+"/"+symbol+"/"+symbol+"-1m-2022-11.zip"
                raw=z.read(name)
                check=z.read(name+".CHECKSUM")
                parts=check.decode().strip().split()
                assert len(parts)==2 and parts[0]==sha(raw) and parts[1].lstrip("*")==Path(name).name
                with zipfile.ZipFile(io.BytesIO(raw)) as inner:
                    assert inner.testzip() is None
                path=output/"temporary-source.zip"
                path.write_bytes(raw)
                try:
                    frame,duplicates=validate_price(numeric_csv(path),family,left,right)
                finally:
                    path.unlink()
                assert np.array_equal(frame.timestamp_ms.to_numpy(),expected)
                close=frame.close.to_numpy(dtype=float)[4::5]
                assert len(close)==30*288
                returns=np.r_[np.nan,np.diff(np.log(close))].reshape(30,288)
                rv=np.square(returns).sum(1)
                assert np.isnan(rv[0]) and np.isfinite(rv[1:]).all() and (rv[1:]>0).all()
                key=family+"_"+symbol
                samples[key]=close
                daily[key+"_RV"]=rv
                daily[key+"_close"]=close.reshape(30,288)[:,-1]
                evidence.append(dict(member=name,bytes=len(raw),SHA256=sha(raw),CHECKSUM_SHA256=sha(check),
                    observed_minutes=len(frame),exact_complete_grid=True,duplicates=duplicates,
                    zero_quote_minutes=int((frame.quote_volume==0).sum()),CRC=True,CHECKSUM=True))
                print("RECOVER",family,symbol,len(frame),"actual minutes",flush=True)
                assert time.monotonic()-start<120
    clocks=np.arange((left+86_400_000)*1000,(right+86_400_000)*1000,DAY,dtype=np.int64)
    five_available=np.arange((left+300_000)*1000,(right+300_000)*1000,300_000_000,dtype=np.int64)
    assert len(clocks)==30 and len(five_available)==8640
    np.savez_compressed(output/"DAILY_RV.npz",available_us=clocks,symbol_order=np.asarray(SYMBOLS),**daily)
    np.savez_compressed(output/"FIVE_MIN_CLOSES.npz",available_us=five_available,symbol_order=np.asarray(SYMBOLS),**samples)
    differences={}
    for symbol in SYMBOLS:
        trade=samples["klines_"+symbol]
        mark=samples["markPriceKlines_"+symbol]
        ratio=daily["markPriceKlines_"+symbol+"_RV"][1:]/daily["klines_"+symbol+"_RV"][1:]
        differences[symbol]=dict(median_daily_mark_over_trade_RV=float(np.median(ratio)),
            aggregate_mark_over_trade_RV=float(daily["markPriceKlines_"+symbol+"_RV"][1:].sum()/daily["klines_"+symbol+"_RV"][1:].sum()),
            maximum_abs_mark_trade_price_basis_bp=float((abs(mark/trade-1)*10000).max()))
    eligibility={}
    for family in ("klines","markPriceKlines"):
        panel=np.column_stack([daily[family+"_"+s+"_RV"] for s in SYMBOLS])
        ready=[int(clocks[i]) for i in range(29,len(clocks)-1)
               if np.isfinite(panel[i-29:i+2]).all() and (panel[i-29:i+2]>0).all()]
        eligibility[family]=ready
    assert not any(eligibility.values())
    save(output/"RECOVERY.json",dict(status="PASS_REAL_2022_TRADE_MARK_RECOVERY_WITH_WARMUP_GAP",
        source_commit=source,data_git=DATA,wrapper_SHA256=protocol["wrapper_sha256"],source_members=evidence,
        actual_minute_rows=432000,full_RV_days_each_domain_asset=29,first_RV_reason="NOV1_PRIOR5MIN_CLOSE_MISSING_NOT_IMPUTED",
        thirty_day_RV_mature_nextday_rows={k:len(v) for k,v in eligibility.items()},
        missing_warmup="ForNov1decision:Oct2-Oct31actualRV plusOct1final5minclose;Octoberfullmonth sufficient. No source identified by current34head inventory.",
        next_information_value="ContiguousOctober price warmup would turn existingNovember marks/trades into causal risk features. TradeRV versus markRV differ; neither alone certifies historical isolated liquidation/cash/funding.",
        price_domain_differences=differences,parameter_fits=0,wallets=0,provider_downloads=0,
        opened_members=[e["member"]+suffix for e in evidence for suffix in ("",".CHECKSUM")],
        scope="EntirefixedNovember seen2022training source, not forecast/alpha/OOS. No historicalreceive/publication or funding-unit certification.",
        elapsed_seconds=time.monotonic()-start,protocol_SHA256=file_sha(HERE/"PROTOCOL.json"),
        artifacts={p.name:file_sha(p) for p in output.iterdir()}))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--source-commit",required=True)
    a=p.parse_args()
    run(a.archive,a.output,a.source_commit)
