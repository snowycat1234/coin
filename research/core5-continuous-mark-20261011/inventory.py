"""Reuse source-directory inventory; inspect only newer source metadata paths."""
from datetime import datetime,timezone
import json
from pathlib import Path
from mark_source import HERE,ROOT,BASE_SOURCE,SYMBOLS,PHASES,inventories,git,digest,save


def run():
    inv,oldhash,invsha,hashsha=inventories()
    old=ROOT/'research/core5-october-warmup-20261011/FULL_GIT_INVENTORY.json.gz'
    import gzip
    full=json.loads(gzip.decompress(old.read_bytes()))
    prior_heads={line.split()[1]:line.split()[0] for line in full['remote_heads']}
    actual=git('ls-remote','--heads','origin').decode().splitlines()
    changes=[]
    for line in actual:
        sha,ref=line.split()
        if prior_heads.get(ref)==sha:continue
        # Tree/path metadata only; never read any2023/24outcome or locked source body.
        oldsha=prior_heads.get(ref)
        paths=git('diff','--name-only',oldsha,sha).decode().splitlines() if oldsha else git('ls-tree','-r','--name-only',sha).decode().splitlines()
        sourcepaths=[p for p in paths if p.startswith('research/') and
            (any(x in p for x in ('SOURCE_INDEX','SOURCE_COVERAGE','originals.zip','source-parts','raw/markPriceKlines')))]
        changes.append(dict(ref=ref,SHA=sha,prior_SHA=oldsha,changed_source_paths=sourcepaths))
    rows=[r for r in inv['reusable_price_archives'] if r['family']=='markPriceKlines']
    target=['2021-12']+[f'2022-{m:02d}' for m in range(1,10)]
    existing={(r['symbol'],r['month']) for r in rows if r['frequency']=='monthly'}
    missing=[dict(symbol=s,month=m) for m in target for s in SYMBOLS if (s,m) not in existing]
    assert len(missing)==50
    priors=[r for r in oldhash['price_source_receipts'] if r['family']=='markPriceKlines' and r['month'] in target]
    assert len(priors)==50
    # All newly published raw-source changes in this session are trade phases or
    # existing October source already incorporated. Record names for review.
    target_stems=['-1m-'+m for m in target]
    newer_mark_paths=[dict(ref=c['ref'],path=p) for c in changes for p in c['changed_source_paths']
        if 'markPriceKlines' in p and any(stem+'.zip' in p or stem+'-' in p for stem in target_stems)]
    assert not newer_mark_paths,'New mark source path must be deduplicated before acquisition'
    save(HERE/'INVENTORY.json',dict(status='PASS_SCOPED_MARK_SOURCE_DEDUP',base_source_commit=BASE_SOURCE,
        coverage_SHA256=invsha,hash_only_SHA256=hashsha,prior_full_directory_inventory_gzip_SHA256=digest(old.read_bytes()),
        prior_scope=full['methods'],prior_summary=full['summary'],remote_head_snapshot=actual,
        changed_heads_source_metadata=changes,newer_mark_source_paths=newer_mark_paths,
        reusable_monthly_mark_originals=65,reusable_daily_mark_companions=21,
        target_missing_monthly_bodies=missing,target_hash_only_receipts=priors,
        target_old_daily_companions=[r for r in rows if r['frequency']=='daily' and r['month'] in target],
        verified_UTC=datetime.now(timezone.utc).isoformat(),raw_archive_bodies_read=0,CSV_rows_read=0,
        outcome_arrays_read=0,fits=0,wallets=0,
        limits='Reuses previouslyexhaustive reachable source-directory inventory with documented2026 exclusions; newerremoteheads tree/sourcepaths inspected, no unreachable/externalbodyclaim. No newlyidentifiedmarktargetarchive; duplicate downloads forbidden.'))
    print('MARK_INVENTORY',dict(reuse_monthly=65,reuse_daily=21,missing_monthly=len(missing),changed_heads=len(changes)))


if __name__=='__main__':run()
